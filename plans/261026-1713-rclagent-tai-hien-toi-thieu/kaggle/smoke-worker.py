"""External operational guards around an unmodified RCLAgent checkout.

Invoked only in Kaggle by kaggle-runtime.py. Importing this module never loads a model.
"""
import argparse
import functools
import hashlib
import importlib.util
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from types import SimpleNamespace


class HarnessStop(BaseException):
    """A fatal operational stop must bypass upstream's catch-and-continue blocks."""


# Deviation from upstream, applied to search_logs results: the search_logs calls of one model response share
# this many tokens equally (floor(2,048 / n) each); a result above its share is condensed (exact-duplicate merge,
# then message-template merge, then marked truncation). Smaller results pass byte-for-byte. 2,048 keeps four tool
# rounds plus 512 output tokens within a 16,384 context. Metric results are not budgeted: on RE2-OB they are at
# most 10 tokens; a larger one surfaces as the context-overflow stop, never as truncation.
LOG_RESULT_BUDGET = 2048
_spec = importlib.util.spec_from_file_location('tool_result_budget', Path(__file__).with_name('tool-result-budget.py'))
budget = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(budget)


def budget_log_result(tokenizer, params, response, share=LOG_RESULT_BUDGET):
    """(text the model receives, audit record). Raises ValueError when the result cannot be fitted."""
    counted = {}

    def count(text):
        if text not in counted:
            counted[text] = len(tokenizer(text, add_special_tokens=False)['input_ids'])
        return counted[text]
    audit = {'budget_tokens': share, 'original_bytes': len(response.encode('utf-8')),
             'original_sha256': hashlib.sha256(response.encode('utf-8')).hexdigest()}
    if audit['original_bytes'] <= share:  # A token spans at least one byte.
        return response, dict(audit, applied=False)
    audit['original_tokens'] = count(response)
    if audit['original_tokens'] <= share:
        return response, dict(audit, applied=False)
    try:
        second = int(str(params.get('timestamp', '')).strip()[:10])  # Same parse as the upstream endpoint.
    except ValueError:
        raise ValueError('search_logs result over budget with an unparseable timestamp')
    condensed = budget.apply('ladder', response, second, share, count)
    if condensed is None:
        raise ValueError('search_logs result over budget and not condensable without guessing')
    return condensed, dict(audit, applied=True, notice=condensed.split('\n', 1)[0], condensed_tokens=count(condensed),
                           condensed_sha256=hashlib.sha256(condensed.encode('utf-8')).hexdigest())


def validate_calls(message, tools, required=False):
    import jsonschema
    calls = message.get('tool_calls') or []
    if not isinstance(calls, list):
        raise ValueError('tool_calls must be a list')
    if required and not calls:
        raise ValueError('Structured tool_calls required; textual fallback disabled')
    names = {item['function']['name']: item['function']['parameters'] for item in tools or []}
    ids = set()
    for call in calls:
        if call.get('type') != 'function' or not isinstance(call.get('id'), str) or not call['id'] or call['id'] in ids:
            raise ValueError('Invalid or duplicate tool call identifier')
        ids.add(call['id'])
        function = call.get('function', {})
        if function.get('name') not in names or not isinstance(function.get('arguments'), str):
            raise ValueError('Unknown function or non-string arguments')
        arguments = json.loads(function['arguments'])
        jsonschema.validate(arguments, names[function['name']])
    # Explicitly reject leaked unparsed tool syntax instead of extracting it.
    text = message.get('content') or ''
    if not calls and any(marker in text for marker in ('<tool_call>', 'Action:', '✿FUNCTION✿')):
        raise ValueError('Server failed to emit structured tool_calls')
    return calls


def adapt_payload(payload, max_output):
    allowed = {'model', 'messages', 'tools', 'enable_thinking'}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError('Unsupported client fields: ' + ', '.join(sorted(unknown)))
    adapted = dict(payload)
    thinking = adapted.pop('enable_thinking', False)
    if thinking is not False:
        raise ValueError('This pinned Instruct model supports non-thinking mode only')
    adapted.update(max_tokens=max_output, temperature=0.7, top_p=0.8, top_k=20,
                   min_p=0.0, seed=20261026, chat_template_kwargs={'enable_thinking': False})
    return adapted


class Guard:
    def __init__(self, output, selection, tokenizer, context, phase, deadline, max_requests=160):
        import requests
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.selection = selection
        self.tokenizer = tokenizer
        self.context = context
        self.phase = phase
        self.deadline = deadline
        self.limit = max_requests
        self.count = 0
        self.fatal = None
        self.tokens = {'prompt_tokens': 0, 'completion_tokens': 0, 'responses_with_usage': 0}
        self.local = threading.local()
        self.lock = threading.RLock()
        self.session = requests.Session()
        self.session.trust_env = False
        self.required_call = False
        self.pools = []

    def event(self, kind, **fields):
        with self.lock:
            with (self.output / 'events.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps({'time': time.time(), 'kind': kind, **fields}, ensure_ascii=False) + '\n')

    def stop(self, reason):
        self.fatal = self.fatal or reason
        self.event('fatal', reason=self.fatal)
        raise HarnessStop(self.fatal)

    def check(self):
        if self.fatal:
            raise HarnessStop(self.fatal)
        if time.monotonic() >= self.deadline:
            self.stop('30-minute RCLAgent deadline exceeded' if self.phase == 'trace' else 'Synthetic compatibility deadline exceeded')

    def post(self, url, **kwargs):
        import requests
        self.check()
        if url != 'http://127.0.0.1:8000/v1/chat/completions':
            self.stop('Refusing any non-local or unexpected model endpoint')
        if self.count >= self.limit:
            self.stop('Model request budget exhausted (including retries)')
        payload = kwargs['json']
        maximum = 1024 if any(t['function']['name'] == 'print_results' for t in payload.get('tools', [])) else 512
        try:
            adapted = adapt_payload(payload, maximum)
            prompt_ids = self.tokenizer.apply_chat_template(adapted['messages'],
                tools=adapted.get('tools'), tokenize=True, add_generation_prompt=True,
                enable_thinking=False)
            prompt_tokens = len(prompt_ids)
            if prompt_tokens + maximum > self.context:
                self.stop(f'Context overflow: input={prompt_tokens}, reserved_output={maximum}, context={self.context}; no truncation')
        except Exception as exc:
            self.stop('Request/template incompatibility: ' + str(exc))
        self.check()
        self.count += 1  # Increment before sending; retries enter here again.
        request_number = self.count
        self.event('request', number=request_number, phase=self.phase,
                   span_id=getattr(self.local, 'span_id', None),
                   operation=getattr(self.local, 'operation', None),
                   prompt_tokens_local=prompt_tokens, payload=adapted,
                   adaptation='top-level enable_thinking=False -> chat_template_kwargs; unknown fields rejected')
        started = time.monotonic()
        try:
            response = self.session.post(url, json=adapted, timeout=(5, max(0.1, min(180, self.deadline-time.monotonic()))))
        except requests.RequestException as exc:
            self.event('transport_error', number=request_number, error=repr(exc))
            raise  # Original tenacity client allows at most 3 attempts.
        self.event('response', number=request_number, status=response.status_code,
                   elapsed_seconds=time.monotonic()-started, body=response.text)
        self.check()
        if response.status_code in (502, 503, 504):
            response.raise_for_status()
        if response.status_code != 200:
            self.stop(f'Model server HTTP {response.status_code}; see response log (includes OOM/context errors)')
        try:
            body = response.json()
            usage = body.get('usage')
            if usage:
                for field in ('prompt_tokens', 'completion_tokens'):
                    self.tokens[field] += int(usage.get(field, 0))
                self.tokens['responses_with_usage'] += 1
            choice = body['choices'][0]
            if choice.get('finish_reason') not in ('stop', 'tool_calls'):
                raise ValueError('Output stopped without completion: ' + str(choice.get('finish_reason')))
            message = choice['message']
            calls = validate_calls(message, payload.get('tools'), self.required_call)
            if calls and self.phase == 'trace':
                for call in calls:
                    if call['function']['name'] != 'print_results':
                        self.validate_query(call['function']['name'], json.loads(call['function']['arguments']))
            return response
        except Exception as exc:
            self.stop('Invalid structured response: ' + str(exc))

    def validate_query(self, name, params):
        if name not in ('search_logs', 'search_fluctuating_metrics'):
            self.stop('Unexpected telemetry tool: ' + name)
        if set(params) != {'service_name', 'timestamp'}:
            self.stop('Unsupported telemetry tool parameters')
        # Upstream filters only by timestamp window and service substring. Every full-data row inside the
        # packaged window is present, so any service name yields the full-data answer; time decides coverage.
        try:
            second = int(str(params['timestamp']).strip()[:10])  # Same parse as the upstream endpoints.
        except ValueError:
            self.stop('Telemetry timestamp is not parseable by the upstream endpoint')
        window = self.selection['query_window']
        if window['start_second'] <= second <= window['end_second']:
            return
        # The endpoints read rows within +-60 s (logs) or +-1200 s (metrics) of the second. A window wholly
        # outside every full-data row is empty on the full data and on the package, so the answer is exact.
        half, source = (60, 'log') if name == 'search_logs' else (1200, 'metric')
        full = window.get('full_data_seconds', {}).get(source)
        if full and (second + half < full[0] or second - half > full[1]):
            return
        self.stop('Tool request timestamp outside the packaged time window; refusing incomplete evidence')


def install_guards(guard, upstream):
    sys.path.insert(0, str(upstream))
    import llm
    import coordinator as coordinator
    import requests
    from urllib.parse import parse_qsl, urlparse
    tool_session = requests.Session()
    tool_session.trust_env = False

    def local_get(url, **kwargs):
        guard.check()
        parsed = urlparse(url)
        if parsed.scheme != 'http' or parsed.netloc != '127.0.0.1:5000':
            guard.stop('Refusing non-local telemetry endpoint')
        if guard.phase == 'trace' and parsed.path in ('/search_logs', '/search_fluctuating_metrics'):
            # Upstream joins arguments without URL encoding; check what the server will actually read.
            sent = requests.Request('GET', url, params=kwargs.get('params')).prepare().url
            received = {}
            for key, value in parse_qsl(urlparse(sent).query, keep_blank_values=True):
                received.setdefault(key, value)  # Flask request.args.get returns the first value.
            guard.validate_query(parsed.path[1:], received)
        try:
            response = tool_session.get(url, **kwargs)
            if response.status_code != 200:
                guard.stop('Telemetry endpoint HTTP ' + str(response.status_code))
            return response
        except requests.RequestException as exc:
            guard.stop('Telemetry transport failure: ' + repr(exc))

    coordinator.requests = SimpleNamespace(get=local_get)
    # Preserve author's client, 3-attempt retry decorator and tuple protocol.
    llm.requests = SimpleNamespace(post=guard.post)

    def no_text_fallback(*args, **kwargs):
        return []

    llm.get_tool_from_content = no_text_fallback
    original_chat = llm.chat_api

    def chat(messages, tools):
        guard.check()
        final = any(t['function']['name'] == 'print_results' for t in tools or [])
        guard.required_call = final
        rounds = sum(1 for m in messages if m.get('role') == 'assistant' and m.get('tool_calls'))
        if rounds > 4:
            guard.stop('Per-span tool round budget exceeded (4)')
        try:
            content, calls = original_chat(messages, tools)
            # Upstream executes every call of this response, in this thread, before its next request.
            guard.local.log_calls = sum(c['function']['name'] == 'search_logs' for c in calls)
            if calls and not final and rounds >= 4:
                guard.stop('Per-span tool round budget exceeded (4); no further tool executed')
            if not calls and not content.strip():
                guard.stop('Empty model output')
            if final and len(calls) != 1:
                guard.stop('Exactly one structured print_results call is required')
            return content, calls
        except Exception as exc:
            guard.stop('Author client failed after bounded retries: ' + repr(exc))

    coordinator.chat_api = chat
    original_get = coordinator._get

    def get_tool(name, params):
        guard.check()
        if guard.phase == 'trace':
            guard.validate_query(name, params)
        response = original_get(name, params)
        guard.event('tool_result', name=name, params=params, response=response,
                    span_id=getattr(guard.local, 'span_id', None))
        if response.startswith('[tool error]'):
            guard.stop('Telemetry tool transport failure')
        if name != 'search_logs':
            return response
        try:
            share = LOG_RESULT_BUDGET // max(1, getattr(guard.local, 'log_calls', 1))
            delivered, audit = budget_log_result(guard.tokenizer, params, response, share)
        except ValueError as exc:
            guard.stop('Tool-result budget: ' + str(exc))
        guard.event('tool_result_budget', name=name, params=params, delivered=delivered if audit['applied'] else None,
                    span_id=getattr(guard.local, 'span_id', None), **audit)
        return delivered

    coordinator._get = get_tool
    original_pool = coordinator.AgentPool

    class TrackedPool(original_pool):
        def __init__(self, max_parallel=1):
            if max_parallel != 1:
                guard.stop('Concurrency must remain one')
            super().__init__(max_parallel)
            guard.pools.append(self)

    coordinator.AgentPool = TrackedPool
    for name in ('self_state_verification', 'consolidate'):
        method = getattr(coordinator.DedicatedAgent, name)

        def decorate(original, operation):
            @functools.wraps(original)
            def wrapped(agent, *args, **kwargs):
                guard.check()
                guard.local.span_id = agent.span_id
                guard.local.operation = operation
                result = original(agent, *args, **kwargs)
                try:
                    parsed = json.loads(result)
                    if not isinstance(parsed, dict) or parsed.get('span_id') != agent.span_id:
                        raise ValueError('Span identifier missing or mismatched')
                    if operation == 'self_state_verification':
                        if type(parsed.get('is_abnormal')) is not bool:
                            raise ValueError('Missing boolean is_abnormal')
                    # upstream passes a leaf's null ("no cause found here") upward unchanged
                    elif 'local_root_cause' not in parsed or not isinstance(parsed['local_root_cause'], (str, type(None))):
                        raise ValueError('Missing local_root_cause')
                except Exception as exc:
                    guard.stop('Invalid agent JSON output: ' + str(exc))
                guard.event('agent_complete', operation=operation, span_id=agent.span_id, output=result)
                return result
            return wrapped

        setattr(coordinator.DedicatedAgent, name, decorate(method, name))
    return coordinator, llm, chat


def graph_nodes(graph, selection):
    """Every node of the upstream trace graph; the count and identifiers must match the packaged selection."""
    def walk(node):
        return [node] + [descendant for child in node['children'] for descendant in walk(child)]
    nodes = walk(graph)
    assert len(nodes) == selection['span_count'] and len({n['span_id'] for n in nodes}) == len(nodes)
    return nodes


def protocol_check(guard, coordinator, chat):
    from tools_gpt import search_logs_function, print_result_function
    prompt = [{'role': 'system', 'content': 'This is a synthetic protocol test. Follow the requested tool protocol.'},
              {'role': 'user', 'content': 'Call search_logs with service_name="syntheticservice", timestamp="1700000000". After its result, return JSON {"received":"SYNTHETIC_OK"} only if the result contains SYNTHETIC_OK.'}]
    content, calls = chat(prompt, [search_logs_function])
    if len(calls) != 1 or calls[0]['function']['name'] != 'search_logs':
        guard.stop('Synthetic tool round did not produce the requested structured call')
    args = json.loads(calls[0]['function']['arguments'])
    if args != {'service_name': 'syntheticservice', 'timestamp': '1700000000'}:
        guard.stop('Synthetic tool arguments differ')
    result = coordinator._get('search_logs', args)
    if 'SYNTHETIC_OK' not in result:
        guard.stop('Synthetic endpoint result missing')
    prompt += [{'role': 'assistant', 'content': content, 'tool_calls': calls},
               {'role': 'tool', 'tool_call_id': calls[0]['id'], 'content': result}]
    received, _ = chat(prompt, None)
    if json.loads(received).get('received') != 'SYNTHETIC_OK':
        guard.stop('Model did not consume the tool-role result')
    candidates = ['synthetic-node-' + str(i) for i in range(10)]
    _, printed = chat([{'role': 'user', 'content': 'Call print_results exactly once with root_causes=' + json.dumps(candidates)}], [print_result_function])
    parsed = json.loads(printed[0]['function']['arguments'])
    if parsed['root_causes'] != candidates:
        guard.stop('print_results did not preserve synthetic candidates')
    assert coordinator._normalise_results(parsed)['root_causes'] == candidates
    before = guard.count
    try:
        adapt_payload({'model': os.environ['LLM_MODEL'], 'messages': [], 'unsupported_rcl_field': True}, 512)
    except ValueError:
        pass
    else:
        guard.stop('Unknown request field was not rejected')
    assert guard.count == before
    guard.event('protocol_pass', structured_calls=True, author_client=True,
                tool_result_round_trip=True, print_results=True,
                enable_thinking_translation=True, unknown_fields_rejected=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('protocol', 'trace'))
    parser.add_argument('--package', required=True)
    parser.add_argument('--trace-dir', help='Trace sub-package with selection.json (trace phase)')
    parser.add_argument('--output', required=True)
    parser.add_argument('--model-path', required=True)
    parser.add_argument('--context', type=int, required=True)
    args = parser.parse_args()
    from transformers import AutoTokenizer
    package, output = Path(args.package), Path(args.output)
    selection = json.loads((Path(args.trace_dir) / 'selection.json').read_text()) if args.phase == 'trace' else {}
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True, trust_remote_code=False)
    guard = Guard(output, selection, tokenizer, args.context, args.phase,
                  time.monotonic() + (1800 if args.phase == 'trace' else 480),
                  max_requests=160 if args.phase == 'trace' else 8)
    status = 'failed'
    error = None
    try:
        coordinator, llm, chat = install_guards(guard, package / 'upstream')
        if args.phase == 'protocol':
            protocol_check(guard, coordinator, chat)
        else:
            graph = coordinator.build_trace_graph(selection['root_span_id'])
            graph_nodes(graph, selection)
            (output / 'trace-graph.json').write_text(json.dumps(graph, indent=2), encoding='utf-8')
            result = coordinator.inspect_trace(graph, max_parallel=1)
            guard.check()
            if not isinstance(result, dict) or len(result.get('root_causes', [])) < 10:
                guard.stop('No valid final result with at least ten normalized candidates')
            (output / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        status = 'passed'
    except BaseException as exc:
        error = repr(exc)
        guard.event('worker_error', error=error, traceback=traceback.format_exc())
    finally:
        for pool in guard.pools:
            pool._executor.shutdown(wait=True, cancel_futures=True)
        (output / 'worker-status.json').write_text(json.dumps({
            'status': status, 'phase': args.phase, 'model_requests_including_retries': guard.count,
            'token_usage': guard.tokens if guard.tokens['responses_with_usage'] else None,
            'error': error, 'fatal': guard.fatal}, indent=2), encoding='utf-8')
    if status != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
