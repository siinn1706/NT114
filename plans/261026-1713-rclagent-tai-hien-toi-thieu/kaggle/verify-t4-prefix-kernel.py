"""Kaggle-only synthetic GPU regression and dense attention reference check.

No model or benchmark data is loaded. Before/after run in separate processes.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

sys.dont_write_bytecode = True


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def gpu_test(mode, output):
    import torch
    import vllm
    from vllm.attention.ops.prefix_prefill import context_attention_fwd
    assert vllm.__version__ == '0.10.2'
    assert torch.cuda.is_available()
    torch.cuda.set_device(0)
    torch.manual_seed(20261026)
    capability = torch.cuda.get_device_capability(0)
    result = {'mode': mode, 'gpu': torch.cuda.get_device_name(0),
              'capability': capability, 'head_size': 128, 'query_heads': 32,
              'kv_heads': 8, 'dtype': 'float16', 'cases': [], 'status': 'failed'}

    @torch.inference_mode()
    def case(length, context):
        heads, kv_heads, dim, block = 32, 8, 128, 16
        total = length + context
        q = torch.randn(length, heads, dim, device='cuda', dtype=torch.float16) * 0.2
        keys = torch.randn(total, kv_heads, dim, device='cuda', dtype=torch.float16) * 0.2
        values = torch.randn_like(keys) * 0.2
        blocks = (total + block - 1) // block
        # Match the author's dependency's documented paged KV layout directly.
        kc = torch.zeros(blocks, block, kv_heads, dim, device='cuda', dtype=torch.float16)
        vc = torch.zeros_like(kc)
        kc.view(-1, kv_heads, dim)[:context].copy_(keys[:context])
        vc.view(-1, kv_heads, dim)[:context].copy_(values[:context])
        kc = kc.view(blocks, block, kv_heads, dim // 8, 8).permute(0, 2, 3, 1, 4).contiguous()
        vc = vc.permute(0, 2, 3, 1).contiguous()
        k, v = keys[context:].contiguous(), values[context:].contiguous()
        out = torch.full_like(q, float('nan'))
        table = torch.arange(blocks, device='cuda', dtype=torch.int32).unsqueeze(0)
        starts = torch.tensor([0, length], device='cuda', dtype=torch.int32)
        lengths = torch.tensor([total], device='cuda', dtype=torch.int32)
        scale = torch.tensor(1.0, device='cuda', dtype=torch.float32)
        context_attention_fwd(q, k, v, out, 'auto', kc, vc, table, starts,
                              lengths, total, length, scale, scale)
        torch.cuda.synchronize()
        if mode == 'before':
            return {'query_length': length, 'cached_context': context, 'kernel_completed': True}
        # FP32 dense causal reference, query chunks bound temporary GPU memory.
        kh = keys.repeat_interleave(heads // kv_heads, dim=1).transpose(0, 1).float()
        vh = values.repeat_interleave(heads // kv_heads, dim=1).transpose(0, 1).float()
        maximum = 0.0
        for start in range(0, length, 128):
            end = min(start + 128, length)
            scores = torch.matmul(q[start:end].transpose(0, 1).float(), kh.transpose(1, 2)) / dim**0.5
            allowed = torch.arange(total, device='cuda')[None, :] <= context + torch.arange(start, end, device='cuda')[:, None]
            scores.masked_fill_(~allowed[None], float('-inf'))
            reference = torch.matmul(torch.softmax(scores, dim=-1), vh).transpose(0, 1)
            actual = out[start:end].float()
            torch.testing.assert_close(actual, reference, atol=1e-3, rtol=1e-3)
            maximum = max(maximum, float((actual-reference).abs().max().item()))
        return {'query_length': length, 'cached_context': context,
                'max_absolute_error': maximum, 'atol': 1e-3, 'rtol': 1e-3,
                'all_rows_finite': bool(torch.isfinite(out).all().item())}

    try:
        if mode == 'before':
            try:
                result['cases'].append(case(129, 17))
            except Exception as exc:
                result['error'] = repr(exc)
                result['traceback'] = traceback.format_exc()
                if capability == (7, 5) and 'out of resource: shared memory' in str(exc) and '98304' in str(exc) and '65536' in str(exc):
                    result['status'] = 'expected-shared-memory-failure'
                else:
                    raise
            else:
                if capability == (7, 5):
                    raise RuntimeError('Original T4 failure did not reproduce; stop to re-diagnose')
                result['status'] = 'original-supported-on-other-gpu'
        else:
            for length, context in [(n, c) for n in (1, 63, 64, 65, 127, 128, 129) for c in (0, 17)] + [(2048, 2048)]:
                result['cases'].append(case(length, context))
            assert all(row['all_rows_finite'] for row in result['cases'])
            result['status'] = 'passed'
    finally:
        result['peak_cuda_allocated_bytes'] = torch.cuda.max_memory_allocated()
        result['peak_cuda_reserved_bytes'] = torch.cuda.max_memory_reserved()
        save(output, result)
    if result['status'] == 'failed':
        raise RuntimeError('GPU kernel check failed')


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--evidence', type=Path, required=True)
    args.add_argument('--child', choices=['before', 'after'])
    options = args.parse_args()
    if sys.platform != 'linux' or not Path('/kaggle/input').is_dir():
        raise RuntimeError('GPU checks may run only on Kaggle')
    evidence = options.evidence
    evidence.mkdir(parents=True, exist_ok=True)
    if options.child:
        gpu_test(options.child, evidence / (options.child + '.json'))
        return
    import importlib.metadata
    assert importlib.metadata.version('vllm') == '0.10.2'
    distribution = importlib.metadata.distribution('vllm')
    source = Path(distribution.locate_file('vllm/attention/ops/prefix_prefill.py'))
    patch_path = Path(__file__).with_name('vllm-t4-compat.py')
    spec = importlib.util.spec_from_file_location('vllm_t4_compat', patch_path)
    compat = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compat)
    # Validate the released source before running either version.
    compat.patched_bytes(source.read_bytes())
    for mode in ('before', 'after'):
        if mode == 'after':
            compat.apply(source, evidence)
        with (evidence / (mode + '.log')).open('wb') as log:
            subprocess.run([sys.executable, str(Path(__file__).resolve()), '--child', mode,
                            '--evidence', str(evidence)], stdout=log, stderr=subprocess.STDOUT,
                           env=os.environ.copy(), check=True, timeout=240)
        print('GPU prefix check:', mode, json.loads((evidence / (mode + '.json')).read_text())['status'], flush=True)
    save(evidence / 'status.json', {'status': 'passed', 'original_reproduced_or_supported': True,
                                  'patched_dense_reference_cases': 15, 'model_requests': 0})


if __name__ == '__main__':
    main()
