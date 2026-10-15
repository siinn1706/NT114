#!/usr/bin/env bash
# Start a vLLM OpenAI-compatible server and record its exact launch arguments for the run's server
# fingerprint (run_grid reads them via the model's `launch_args` config key).
#
#   bash scripts/serve_model.sh <args-file> <hf-repo> <revision-sha> [extra vllm serve flags...]
#   bash scripts/serve_model.sh results/server/qwen35-9b.args Qwen/Qwen3.5-9B <sha> \
#        --quantization fp8 --max-model-len 16384 --gpu-memory-utilization 0.85 --port 8000
#
# The args file holds `--revision`, `--quantization` and every other flag on one line; run_grid refuses
# to run when they contradict the config. Prefix caching is always on; the vLLM version is recorded.
set -euo pipefail
if [ $# -lt 3 ]; then
  sed -n '2,10p' "$0"; exit 2
fi
args_file=$1; repo=$2; rev=$3; shift 3
mkdir -p "$(dirname "$args_file")"
vllm_version=$(python -c "import vllm; print(vllm.__version__)" 2>/dev/null || echo unknown)
echo "$repo --revision $rev --enable-prefix-caching $* --vllm-version $vllm_version" > "$args_file"
exec vllm serve "$repo" --revision "$rev" --enable-prefix-caching "$@"
