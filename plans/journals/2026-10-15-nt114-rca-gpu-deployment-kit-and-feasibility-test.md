---
title: NT114-RCA GPU deployment kit and feasibility test
date: 2026-10-15
summary: "Pushed the M1 branch; pinned vLLM 0.30.0 in a separate serving venv; added serving profiles and rca.feasibility; nothing run on GPU, no Jev"
---

# NT114-RCA GPU deployment kit and feasibility test

## What happened
- Pushed `feat/m1-offline-llm-jev-pipeline` (5 commits ahead of main) after a secrets, large-file and path scan. No force push, no merge.
- Model cards read at the pinned revisions: Qwen3.5 needs `enable_thinking: false` and `--language-model-only`. Only Qwen3-8B has an official 4-bit (AWQ) checkpoint.
- vLLM 0.30.0 pins torch 2.13.0 and setuptools<81, which conflict with the analysis lock (torch 2.14.1, setuptools 84). Serving moved to its own `.venv-serve`, talking over HTTP.
- Added five serving profiles to the hardware YAML, `rca.feasibility` (check-env, fetch, run, report), `configs/exp/gpu-feasibility.yaml` (12 DEV incidents) and `docs/gpu_deployment.md`.

## Problems hit
- Popen("bash") on Windows resolved to the WSL relay bash; it now resolves through `shutil.which`.
- On Windows, MSYS `exec` detaches the server child from the process tree, so taskkill /T misses it. Linux uses killpg. The test's fake server exits on its own after 30 s idle.

## Evidence
- 260 fast tests pass, including an end-to-end feasibility run against a fake vLLM server.
- Real-data `prepare` of the feasibility config gave 12 DEV incidents and a 374-incident store in 765 s. Retrieval prompt p95 is 4,512 tokens.

## Next steps
- Owner, on the GPU machine: Linux gate, GPU probe, check-env, fetch, then feasibility for all five profiles.
- Then the Jev smoke call, after which the DEV pilot can start.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
