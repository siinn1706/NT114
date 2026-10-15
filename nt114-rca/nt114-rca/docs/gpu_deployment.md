# GPU deployment and feasibility test (RTX 4080 Laptop, 12 GB)

This guide takes the GPU machine from a fresh checkout to a measured model choice. It covers the
environment, the pinned model set, a small feasibility test on DEV data, and the order in which
M2 starts. Everything up to step 7 runs without TypeSafe Jev and without any test-set data.

Status on 2026-10-15: prepared, not run. M0 stays blocked until the Linux portability gate, the
GPU probe, TypeSafe access and the D3 data-sharing check have all passed. The capacity figures in
`configs/hardware/rtx4080-laptop-12gb.yaml` are estimates. The model set is final only after step 7.

## 1. Machine requirements

| Item | Requirement | Checked by |
|---|---|---|
| OS | Linux x86_64, or WSL2 Ubuntu 22.04/24.04 on Windows (vLLM ships Linux wheels only) | `uname -a` |
| GPU | NVIDIA, compute capability ≥ 8.9 for FP8 (RTX 4080 Laptop = 8.9) | `rca.feasibility check-env` |
| Driver | Reports CUDA ≥ 13.0, because vLLM 0.30.0 kernels are CUDA 13 builds. On WSL2, install the Windows driver; never install a Linux driver inside WSL | `scripts/gpu_probe.py` |
| Python | 3.12 | `python3.12 -V` |
| Disk | ~50 GB for the five pinned snapshots (9.3 + 8.1 + 7.7 + 19.3 + 6.1 GB), ~15 GB for the two venvs, plus the data bundle | `gpu_probe.py` (`disk_free_gib`) |
| Power | AC power and the vendor's performance mode; laptop GPUs throttle on battery | `smi.csv` clocks in the feasibility report |

## 2. Two environments

| Venv | Contents | Used for |
|---|---|---|
| `.venv` | `requirements-lock.txt` | prep, `run_grid`, `decide`, `analyze`, `rca.feasibility` |
| `.venv-serve` | `requirements-gpu.txt` (vLLM 0.30.0, transformers 5.17.0, bitsandbytes 0.50.2) | `vllm serve` only |

The two cannot share a venv. vLLM pins `torch==2.13.0` and `setuptools<81`, while the analysis
lock has torch 2.14.1 and setuptools 84. They talk over HTTP on `localhost:8000`.

## 3. Credentials

- **TypeSafe** (needed from step 9 only): type the key into the shell without echo, and never write it to a file:
  `read -rs TYPESAFE_API_KEY && export TYPESAFE_API_KEY`. `rca.jev` reads only this variable and
  never logs it. Do not put it in `.env`, a config, a notebook or the shell history.
- **Hugging Face:** the five models are public, so no token is needed. The private data bundle needs
  `hf auth login` with a team account. The token stays in the HF cache directory, outside the repo.

## 4. Sequence

Steps 1–8 need no Jev key. Step 9 is the first live Jev call and starts only once M0 has passed.

```bash
# 1. checkout (Linux / WSL2)
git clone https://github.com/siinn1706/NT114.git && cd NT114
git checkout feat/m1-offline-llm-jev-pipeline
cd nt114-rca/nt114-rca

# 2. Linux portability gate, from a worktree pinned to the bundle commit (plan phase 01, task 1)
git worktree add ../../../nt114-gate cd96e9e
(cd ../../../nt114-gate/nt114-rca/nt114-rca \
  && python3.12 -m venv .venv && . .venv/bin/activate && pip install -r requirements-lock.txt \
  && hf auth login && hf download siinn1706/nt114-rca-data --repo-type dataset --local-dir ~/nt114-rca-data \
  && bash scripts/verify_portability.sh ~/nt114-rca-data/nt114-data-v1-20261014-6fdd9835 | tee ~/portability.log)
# Record ~/portability.log in the data plan's reports/phase-12-portability.md, then remove the worktree.

# 3. analysis venv at the branch HEAD + data home
python3.12 -m venv .venv && . .venv/bin/activate && pip install -r requirements-lock.txt
export RCA_DATA_HOME=~/nt114-rca-data/nt114-data-v1-20261014-6fdd9835/parts
PYTHONPATH=src python -m rca.prep status && PYTHONPATH=src python -m rca.prep verify-splits
PYTHONPATH=src python -m pytest -q -m "not realdata" && PYTHONPATH=src python -m pytest -q -m realdata

# 4. GPU probe; paste its `hardware` block into configs/hardware/rtx4080-laptop-12gb.yaml
python scripts/gpu_probe.py --out results/gpu_probe.json
PYTHONPATH=src python -m rca.capacity configs/hardware/rtx4080-laptop-12gb.yaml

# 5. serving venv, frozen after the first install
python3.12 -m venv .venv-serve && .venv-serve/bin/pip install -r requirements-gpu.txt
.venv-serve/bin/pip freeze > requirements-gpu-lock.txt          # commit this file
export VLLM_VENV=$PWD/.venv-serve
PYTHONPATH=src python -m rca.feasibility check-env configs/hardware/rtx4080-laptop-12gb.yaml   # exit 0 = no problems

# 6. pinned model snapshots (into the HF cache; the commit sha is checked)
PYTHONPATH=src python -m rca.feasibility list  configs/hardware/rtx4080-laptop-12gb.yaml
PYTHONPATH=src python -m rca.feasibility fetch configs/hardware/rtx4080-laptop-12gb.yaml \
  qwen35-4b-fp8 qwen3-4b-2507-fp8 phi4-mini-fp8 qwen3-8b-awq qwen35-9b-nf4

# 7. feasibility test: one profile at a time, no Jev. The first run also builds the evidence and the
#    374-incident retrieval store on the CPU (13 min on the dev laptop); later profiles reuse them.
for p in qwen35-4b-fp8 qwen3-4b-2507-fp8 phi4-mini-fp8 qwen3-8b-awq qwen35-9b-nf4; do
  PYTHONPATH=src python -m rca.feasibility run configs/hardware/rtx4080-laptop-12gb.yaml "$p"
done
PYTHONPATH=src python -m rca.feasibility report       # results_feasibility/feasibility.csv

# 8. record the measured choice (section 6) in the plan's decisions.md and commit the config changes
```

Step 9 and later steps are the M2 sequence in section 7.

## 5. What the feasibility test does

`rca.feasibility run <hw> <profile>`:

1. It refuses to run when `results_feasibility/<profile>/` exists, or when a server already
   answers on the port. Only one model fits at a time.
2. It builds the evidence of the small DEV set on the CPU: `configs/exp/gpu-feasibility.yaml`,
   `within-rcaeval-grouped` validation role, 4 incidents per system, `full` and `no_trace`,
   retrieval `none` and `hybrid`, n = 10.
3. It starts `nvidia-smi` sampling every second (`smi.csv`), then starts `vllm serve` through
   `scripts/serve_model.sh` with `HF_HUB_OFFLINE=1`, so only the pinned snapshot can load. The
   server log goes to `server.log`.
4. It runs the grid with `run_grid` (live vLLM backend; the server fingerprint checks revision and
   quantisation), then stops the server and the sampler.
5. It writes `feasibility.json` with the following:
   - the profile;
   - the capacity estimate;
   - the server's measured weight memory, KV-cache memory and KV tokens;
   - peak and baseline VRAM, temperature, SM clock and throttle reasons;
   - the parse rate per cell, latency p50/p95, tokens/s and the served prompt-length p95;
   - a verdict.

A profile is **feasible** when all of these hold:

- the server starts without running out of memory;
- the parse rate is ≥ 0.99;
- the measured KV cache holds ≥ 2 requests of (p95 prompt + 10 × 400) tokens.

DEV AC@1 is reported for information only. With 12 incidents it does not rank models; the DEV
pilot does that.

## 6. Choosing the models from the report

| Role | Rule | Fallback |
|---|---|---|
| Primary | `qwen35-4b-fp8` if feasible | `qwen3-4b-2507-fp8` |
| Replication | `phi4-mini-fp8` if feasible | none; the replication arm is dropped and the drop is logged |
| Escalation candidates | the feasible profiles among `qwen3-8b-awq` and `qwen35-9b-nf4` | if neither is feasible, escalation needs external inference, which needs owner approval |

The final escalation model is picked in the DEV pilot: the feasible candidate with the larger DEV
AC@1 gain over the primary, measured over at least 30 minutes of sustained load (plan phase 03,
task 2). Record the revisions, flags, measured VRAM and verdicts in `decisions.md`.

If a measurement contradicts the estimate (for example, the server's KV tokens are far below the
estimate), keep the measurement. To change `gpu_memory_utilization` or `max_model_len`, edit the
profile, log the change, and rerun that profile in a fresh results directory.

## 7. Starting M2 (after M0 passes)

1. **Jev smoke call (M0 task 4).** Send one hand-written synthetic state outside the repo with
   `model: jev-1.13.0`. Record the exact response `model` string, the response fields and the org
   rate limit in `decisions.md`. Set `jev.expected_model` in `configs/exp/dev-pilot.yaml` to that string.
2. **Serve the chosen primary:**
   `bash scripts/serve_model.sh results_dev_pilot/server/qwen35-4b.args <repo> <sha> <flags from rca.feasibility list>`.
3. **DEV pilot, LLM part:**
   `PYTHONPATH=src python -m rca.run_grid prepare configs/exp/dev-pilot.yaml`, then `run`. These are
   143 RCAEval DEV incidents, so no NC data is involved.
4. **DEV pilot, Jev part:** `PYTHONPATH=src python -m rca.decide configs/exp/dev-pilot.yaml`. This is
   the first live Jev use. Before running it, confirm that D3 still withholds AIOps2025/RCA100
   evidence; DEV is RCAEval, CC BY 4.0.
5. Continue with plan phase 03 tasks 2–7: gates, prompt freeze, escalation serving, Jev bias and
   stability, tuning, and the preregistration freeze.

## 8. Troubleshooting

| Symptom | Action |
|---|---|
| `check-env`: `torch_cuda` is not 13.x, or no CUDA device | Update the driver (WSL2: the Windows driver) and reinstall `.venv-serve` |
| Server exits with "No available memory for the cache blocks", or not enough free memory at start | Close apps that use the display GPU. Lower `gpu_memory_utilization` in the hardware block to 0.85, log the change, rerun |
| `qwen35-9b-nf4`: bitsandbytes is unsupported for the model | Expected risk. The profile is infeasible and `qwen3-8b-awq` is the candidate |
| Parse rate < 0.99 | Read failing rows in `grid.jsonl`. Check that thinking is off (`chat_template_kwargs`); prompt changes belong to the M2 prompt freeze (≤ 3 DEV iterations) |
| SM clock falls during the run | Check AC power and performance mode. The 30-minute throughput measurement in M2 is the reference |
