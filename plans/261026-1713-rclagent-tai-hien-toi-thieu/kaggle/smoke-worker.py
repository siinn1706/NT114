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
# rounds plus 512 output tokens within a 16,384 context. Metric results are not budgeted: from the author's endpoint
# on RE2-OB they are at most 10 tokens, from metric-repair.py a few KPI rows; a larger one surfaces as the
# context-overflow stop, never as truncation.
LOG_RESULT_BUDGET = 2048
_spec = importlib.util.spec_from_file_location('tool_result_budget', Path(__file__).with_name('tool-result-budget.py'))
budget = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(budget)
_spec = importlib.util.spec_from_file_location('metric_repair', Path(__file__).with_name('metric-repair.py'))
metric_repair = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(metric_repair)
_spec = importlib.util.spec_from_file_location('telemetry_gap', Path(__file__).with_name('telemetry-gap.py'))
gap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gap)

DEFAULT_SEED = 20261026
# A response whose tool calls fail validation (leaked textual syntax, schema, identifiers) is asked again, never
# parsed from text. A per-request seed makes a same-seed retry repeat the same output, so each retry takes a seed
# derived from the run seed, the first request number and the attempt: reproducible, and recorded per request.
MALFORMED_CALL_RETRIES = 3


def retry_seed(seed, first_number, attempt):
    digest = hashlib.sha256(f'{seed}:{first_number}:{attempt}'.encode()).digest()
    return int.from_bytes(digest[:4], 'big') & 0x7fffffff
# A source set to 'absent' is answered by the harness, without the tool server, with the exact bytes the author's
# endpoint returns when it holds no row: the model is not told that the source is gone, and cannot tell this apart
# from a live source that found nothing. 'repaired' answers metric queries with metric-repair.py.
ABSENT_RESPONSE = {'search_logs': 'log_id,timestamp,cmdb_id,log_name,value\n',
                   'search_fluctuating_metrics': metric_repair.NO_ROWS}
SOURCE_OF = {'search_logs': 'logs', 'search_fluctuating_metrics': 'metric'}


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
    # Explicitly reject leaked unparsed tool syntax instead of extracting it. 'Action: ' is also ordinary prose, so,
    # as in the author's client, it only counts at the start of a line and when tools were offered.
    text = message.get('content') or ''
    action = bool(tools) and any(line.startswith('Action: ') for line in text.split('\n'))
    if not calls and (action or any(marker in text for marker in ('<tool_call>', '✿FUNCTION✿'))):
        raise ValueError('Server failed to emit structured tool_calls')
    return calls


def adapt_payload(payload, max_output, seed=DEFAULT_SEED):
    allowed = {'model', 'messages', 'tools', 'enable_thinking'}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError('Unsupported client fields: ' + ', '.join(sorted(unknown)))
    adapted = dict(payload)
    thinking = adapted.pop('enable_thinking', False)
    if thinking is not False:
        raise ValueError('This pinned Instruct model supports non-thinking mode only')
    adapted.update(max_tokens=max_output, temperature=0.7, top_p=0.8, top_k=20,
                   min_p=0.0, seed=seed, chat_template_kwargs={'enable_thinking': False})
    return adapted


class Guard:
    def __init__(self, output, selection, tokenizer, context, phase, deadline, max_requests=160,
                 seed=DEFAULT_SEED, sources=None, data_root=None, tool_rounds=4, deadline_seconds=1800,
                 components=None, window_kpi=None):
        import requests
        self.seed = seed
        # Telemetry-gap components (telemetry-gap.py); all off keeps every request byte-identical.
        self.components = dict.fromkeys(('gap_aware', 'trace_kpi', 'trace_expand'), False)
        self.components.update(components or {})
        self.window_kpi = window_kpi
        self.model_url = os.environ.get('LLM_API_URL', 'http://127.0.0.1:8000/v1/chat/completions')
        self.sources = sources or {'logs': 'author', 'metric': 'author'}
        self.data_root = Path(data_root) if data_root else None
        self.metric_data = None
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.selection = selection
        self.tokenizer = tokenizer
        self.context = context
        self.phase = phase
        self.deadline = deadline
        self.limit = max_requests
        self.tool_rounds = tool_rounds
        self.deadline_seconds = deadline_seconds
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

    def source_response(self, name, params):
        """The harness's answer for a query whose source is not 'author'; the tool server is not asked."""
        if self.sources[SOURCE_OF[name]] == 'absent':
            if name == 'search_fluctuating_metrics' and self.components['trace_kpi']:
                return gap.kpi_response(self.window_kpi, params['service_name'])
            if self.components['gap_aware']:
                return gap.unavailable(SOURCE_OF[name])
            return ABSENT_RESPONSE[name]
        if self.metric_data is None:  # 'repaired' exists for metric only; load the same files the server reads.
            import pandas as pd
            import pickle
            metric_df = pd.read_csv(self.data_root / 'metric/all/metrics.csv', low_memory=False)
            with (self.data_root / 'metric/service_node_map.pkl').open('rb') as f:
                self.metric_data = (metric_df, pickle.load(f))
        return metric_repair.search_fluctuating_metrics(*self.metric_data, params['service_name'], params['timestamp'])

    def stop(self, reason):
        self.fatal = self.fatal or reason
        self.event('fatal', reason=self.fatal)
        raise HarnessStop(self.fatal)

    def check(self):
        if self.fatal:
            raise HarnessStop(self.fatal)
        if time.monotonic() >= self.deadline:
            self.stop(f'{self.deadline_seconds / 60:g}-minute RCLAgent deadline exceeded' if self.phase == 'trace'
                      else 'Synthetic compatibility deadline exceeded')

    def post(self, url, **kwargs):
        import requests
        self.check()
        if url != self.model_url or not url.startswith('http://127.0.0.1:') or not url.endswith('/v1/chat/completions'):
            self.stop('Refusing any non-local or unexpected model endpoint')
        payload = kwargs['json']
        if self.phase == 'trace' and any(self.components.values()):
            try:
                payload = dict(payload, messages=gap.edit_messages(payload['messages'], kpi=self.window_kpi,
                                                                   **self.components))
            except Exception as exc:
                self.stop('Telemetry-gap prompt edit failed: ' + str(exc))
        maximum = 1024 if any(t['function']['name'] == 'print_results' for t in payload.get('tools', [])) else 512
        try:
            adapted = adapt_payload(payload, maximum, self.seed)
            prompt_ids = self.tokenizer.apply_chat_template(adapted['messages'],
                tools=adapted.get('tools'), tokenize=True, add_generation_prompt=True,
                enable_thinking=False)
            prompt_tokens = len(prompt_ids)
            if prompt_tokens + maximum > self.context:
                self.stop(f'Context overflow: input={prompt_tokens}, reserved_output={maximum}, context={self.context}; no truncation')
        except Exception as exc:
            self.stop('Request/template incompatibility: ' + str(exc))
        first_number = None
        for attempt in range(MALFORMED_CALL_RETRIES + 1):
            self.check()
            if self.count >= self.limit:
                self.stop('Model request budget exhausted (including retries)')
            self.count += 1  # Increment before sending; retries enter here again.
            request_number = self.count
            first_number = first_number or request_number
            if attempt:
                adapted = dict(adapted, seed=retry_seed(self.seed, first_number, attempt))
            self.event('request', number=request_number, phase=self.phase,
                       span_id=getattr(self.local, 'span_id', None),
                       operation=getattr(self.local, 'operation', None),
                       prompt_tokens_local=prompt_tokens, payload=adapted, attempt=attempt,
                       retry_of=first_number if attempt else None,
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
                try:
                    calls = validate_calls(message, payload.get('tools'), self.required_call)
                except Exception as exc:
                    if attempt == MALFORMED_CALL_RETRIES:
                        raise
                    self.event('malformed_tool_call_retry', number=request_number, next_attempt=attempt + 1,
                               next_seed=retry_seed(self.seed, first_number, attempt + 1), reason=str(exc))
                    continue
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
        if parsed.scheme != 'http' or parsed.netloc != '127.0.0.1:' + os.environ.get('TOOL_SERVER_PORT', '5000'):
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
        if rounds > guard.tool_rounds:
            guard.stop(f'Per-span tool round budget exceeded ({guard.tool_rounds})')
        try:
            content, calls = original_chat(messages, tools)
            # Upstream executes every call of this response, in this thread, before its next request.
            guard.local.log_calls = sum(c['function']['name'] == 'search_logs' for c in calls)
            if calls and not final and rounds >= guard.tool_rounds:
                guard.stop(f'Per-span tool round budget exceeded ({guard.tool_rounds}); no further tool executed')
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
        source = guard.sources[SOURCE_OF[name]] if guard.phase == 'trace' else 'author'
        response = original_get(name, params) if source == 'author' else guard.source_response(name, params)
        guard.event('tool_result', name=name, params=params, response=response, source=source,
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
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED)
    parser.add_argument('--logs', choices=('author', 'absent'), default='author')
    parser.add_argument('--metric', choices=('author', 'absent', 'repaired'), default='author')
    parser.add_argument('--tool-rounds', type=int, default=4, help='Tool rounds per span (trace phase)')
    parser.add_argument('--max-requests', type=int, default=160, help='Model requests incl. retries (trace phase)')
    parser.add_argument('--deadline-seconds', type=int, default=1800, help='RCLAgent deadline (trace phase)')
    parser.add_argument('--gap-aware', action='store_true', help='M1: missing-source notice')
    parser.add_argument('--trace-kpi', action='store_true', help='M2: trace-derived latency KPI for absent metrics')
    parser.add_argument('--trace-expand', action='store_true', help='M3: window evidence table in the final prompt')
    args = parser.parse_args()
    components = {'gap_aware': args.gap_aware, 'trace_kpi': args.trace_kpi, 'trace_expand': args.trace_expand}
    if args.trace_kpi and args.metric != 'absent':
        parser.error('--trace-kpi replaces absent metrics only')
    if any(components.values()) and args.phase != 'trace':
        parser.error('Telemetry-gap components apply to the trace phase only')
    from transformers import AutoTokenizer
    package, output = Path(args.package), Path(args.output)
    selection = json.loads((Path(args.trace_dir) / 'selection.json').read_text()) if args.phase == 'trace' else {}
    window_kpi = None
    if args.trace_kpi or args.trace_expand:
        window_kpi = json.loads((Path(args.trace_dir) / 'window-kpi.json').read_text(encoding='utf-8'))
        if window_kpi['trace_id'] != selection['trace_id']:
            parser.error('window-kpi.json belongs to another trace')
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True, trust_remote_code=False)
    guard = Guard(output, selection, tokenizer, args.context, args.phase,
                  time.monotonic() + (args.deadline_seconds if args.phase == 'trace' else 480),
                  max_requests=args.max_requests if args.phase == 'trace' else 8, seed=args.seed,
                  tool_rounds=args.tool_rounds, deadline_seconds=args.deadline_seconds,
                  sources={'logs': args.logs, 'metric': args.metric},
                  data_root=Path(args.trace_dir) / 'input' if args.trace_dir else None,
                  components=components, window_kpi=window_kpi)
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
            'status': status, 'phase': args.phase, 'seed': guard.seed, 'sources': guard.sources,
            'components': guard.components,
            'model_requests_including_retries': guard.count,
            'token_usage': guard.tokens if guard.tokens['responses_with_usage'] else None,
            'error': error, 'fatal': guard.fatal}, indent=2), encoding='utf-8')
    if status != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
