"""GPU feasibility test of the serving profiles: load, KV headroom, parse rate and latency on DEV.

  python -m rca.feasibility list      <hw.yaml>
  python -m rca.feasibility check-env <hw.yaml>              # needs $VLLM_VENV (the serving venv)
  python -m rca.feasibility fetch     <hw.yaml> <profile>... # pinned snapshots into the HF cache
  python -m rca.feasibility run       <hw.yaml> <profile> [--exp configs/exp/gpu-feasibility.yaml]
  python -m rca.feasibility report    [--root results_feasibility]
  python -m rca.feasibility compare-sampling results_dev_sampling/grid.jsonl   # presence penalty 0 vs 1.5

`run` starts `vllm serve` through scripts/serve_model.sh (offline, pinned revision), samples
nvidia-smi every second, runs the small DEV grid of the experiment config with run_grid, stops the
server and writes `<root>/<profile>/feasibility.json`. The estimate from
rca.capacity is stored next to the measurement; the measurement decides.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import yaml

from . import capacity

ROOT = Path(__file__).resolve().parents[2]
SMI_FIELDS = "timestamp,memory.used,memory.total,temperature.gpu,clocks.sm,power.draw,clocks_throttle_reasons.active"
MIN_PARSE_RATE = 0.99
MIN_CONCURRENT = 2
# lines vLLM prints while loading; values are GiB, tokens and "x" concurrency
LOG_PATTERNS = {
    "model_load_gib": r"Model loading took ([\d.]+) ?GiB",
    "kv_cache_gib": r"Available KV cache memory: ([\d.]+) ?GiB",
    "kv_cache_tokens": r"GPU KV cache size: ([\d,]+) tokens",
    "max_concurrency": r"Maximum concurrency for [\d,]+ tokens per request: ([\d.]+)x",
}
OOM_PATTERNS = ("CUDA out of memory", "OutOfMemoryError", "No available memory for the cache blocks",
                "is larger than the available KV cache memory")


def load(hw_path) -> tuple[capacity.Plan, dict[str, dict]]:
    """The capacity plan and the profiles of a hardware file, each profile resolved to repo + revision."""
    plan = capacity.load_plan(hw_path)
    specs = {m.name: m for m in plan.models}
    raw = yaml.safe_load(Path(hw_path).read_text(encoding="utf-8")).get("profiles", [])
    profiles = {}
    for p in raw:
        if p["model"] not in specs:
            raise ValueError(f"profile {p['name']}: unknown model {p['model']!r}")
        m = specs[p["model"]]
        p = {"extra_args": [], "chat_template_kwargs": None, "fallback": None, **p}
        p.setdefault("repo", m.repo)
        p.setdefault("revision", m.revision)
        if not re.fullmatch(r"[0-9a-f]{40}", p["revision"] or ""):
            raise ValueError(f"profile {p['name']}: revision must be a full commit sha")
        profiles[p["name"]] = p
    for p in profiles.values():
        if p["fallback"] is not None and p["fallback"] not in profiles:
            raise ValueError(f"profile {p['name']}: unknown fallback {p['fallback']!r}")
    return plan, profiles


def serve_args(p: dict, hw: capacity.Hardware, port: int) -> list[str]:
    """vllm serve flags after <repo> <revision>; the same list is recorded in the launch-args file."""
    args = ["--max-model-len", str(p["max_model_len"]), "--gpu-memory-utilization", str(hw.gpu_memory_utilization)]
    if p.get("quantization"):
        args += ["--quantization", p["quantization"]]
    return args + list(p["extra_args"]) + ["--port", str(port)]


def grid_cfg(exp: dict, p: dict, run_dir: Path) -> dict:
    """The run_grid config of one profile: the experiment config with this profile as its only model."""
    cfg = copy.deepcopy(exp)
    cfg.update(out=str(run_dir / "grid.jsonl"), cache=str(run_dir / "llm_cache.sqlite"))
    cfg["models"] = [{"name": p["repo"], "role": p["role"], "backend": "vllm",
                      "base_url": f"http://localhost:{exp.get('port', 8000)}/v1", "revision": p["revision"],
                      "quantization": p.get("quantization"), "launch_args": str(run_dir / "server.args"),
                      "max_tokens": 400, "chat_template_kwargs": p["chat_template_kwargs"]}]
    body = {k: v for k, v in cfg.items() if k != "_hash"}
    cfg["_hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:10]
    return cfg


def parse_server_log(text: str) -> dict:
    out = {}
    for k, pat in LOG_PATTERNS.items():
        hits = re.findall(pat, text)
        if hits:
            v = hits[-1].replace(",", "")
            out[k] = int(v) if k == "kv_cache_tokens" else float(v)
    out["oom"] = any(s in text for s in OOM_PATTERNS)
    return out


def _num(x: str) -> float | None:
    try:
        return float(x)
    except ValueError:
        return None


def smi_stats(path: Path, baseline_rows: int = 1) -> dict:
    """Peak / baseline VRAM (MiB), temperature and SM clock from the nvidia-smi CSV log. Throttling shows
    as a falling SM clock or a non-zero throttle-reason mask under load."""
    if not path.is_file():
        return {}
    rows = [r for r in csv.reader(path.read_text(encoding="utf-8").splitlines()) if len(r) >= 7]
    if not rows:
        return {}
    mem = [_num(r[1]) for r in rows]
    temp = [t for t in (_num(r[3]) for r in rows) if t is not None]
    clk = [c for c in (_num(r[4]) for r in rows) if c is not None]
    reasons = sorted({r[6].strip() for r in rows} - {"0x0000000000000000", ""})
    base = [m for m in mem[:baseline_rows] if m is not None]
    return {"samples": len(rows), "baseline_mib": base[0] if base else None,
            "peak_mib": max(m for m in mem if m is not None), "total_mib": _num(rows[0][2]),
            "temp_max_c": max(temp) if temp else None, "sm_clock_p50_mhz": float(np.median(clk)) if clk else None,
            "sm_clock_min_mhz": min(clk) if clk else None, "throttle_reasons": reasons}


def grid_stats(path: Path) -> dict:
    """Parse rate, latency, throughput and served prompt lengths over the rows answered by the server."""
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.is_file() else []
    live = [r for r in rows if not r.get("cached")]
    if not live:
        return {"rows": len(rows), "live_rows": 0}
    lat = np.array([r["latency_s"] for r in live], dtype=float)
    pt = np.array([r["prompt_tokens"] or 0 for r in live], dtype=float)
    ct = np.array([r["completion_tokens"] or 0 for r in live], dtype=float)
    q = lambda a, p: round(float(np.percentile(a, p)), 1)
    by_cond: dict[str, list] = {}
    for r in live:
        by_cond.setdefault(f"{r['condition']}/{r['retrieval']}", []).append(not r["parse_failed"])
    return {"rows": len(rows), "live_rows": len(live), "incidents": len({r["case_id"] for r in live}),
            "parse_rate": round(float(np.mean([not r["parse_failed"] for r in live])), 4),
            "parse_rate_by_cell": {k: round(float(np.mean(v)), 4) for k, v in sorted(by_cond.items())},
            "latency_s": {"p50": q(lat, 50), "p95": q(lat, 95), "max": round(float(lat.max()), 1)},
            "prompt_tokens": {"p50": q(pt, 50), "p95": q(pt, 95), "max": int(pt.max())},
            "completion_tokens_per_s": round(float(ct.sum() / lat.sum()), 1) if lat.sum() else None,
            "wall_s_per_request": round(float(lat.mean()), 2),
            "dev_ac1": round(float(np.mean([bool(r["correct"]) for r in live])), 3)}


def verdict(server: dict, grid: dict, req_tokens: int | None) -> dict:
    """Feasible = the server came up without OOM, answers parse, and the KV cache holds at least
    MIN_CONCURRENT requests of the measured p95 size."""
    conc = (server["kv_cache_tokens"] / req_tokens) if server.get("kv_cache_tokens") and req_tokens else None
    reasons = []
    if not server.get("ready"):
        reasons.append("server did not become ready" + (" (out of memory)" if server.get("oom") else ""))
    if grid.get("live_rows", 0) == 0:
        reasons.append("no live rows")
    elif grid["parse_rate"] < MIN_PARSE_RATE:
        reasons.append(f"parse rate {grid['parse_rate']} < {MIN_PARSE_RATE}")
    if conc is None:
        reasons.append("KV cache size not found in the server log")
    elif conc < MIN_CONCURRENT:
        reasons.append(f"KV cache holds {conc:.1f} requests of {req_tokens} tokens < {MIN_CONCURRENT}")
    return {"feasible": not reasons, "concurrent_requests_measured": round(conc, 2) if conc else None,
            "request_tokens": req_tokens, "reasons": reasons}


def _get(url: str, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def _port_busy(port: int) -> bool:
    try:
        _get(f"http://localhost:{port}/v1/models", 2)
        return True
    except Exception:
        return False


def _stop(proc: subprocess.Popen | None, grace=30):
    """Stop a process started here together with its children (the server runs under bash)."""
    if proc is None or proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        proc.wait(grace)
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (AttributeError, ProcessLookupError):
        proc.terminate()
    try:
        proc.wait(grace)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (AttributeError, ProcessLookupError):
            proc.kill()
        proc.wait()


def _venv_env(offline: bool) -> dict:
    venv = os.environ.get("VLLM_VENV")
    if not venv:
        raise RuntimeError("set VLLM_VENV to the serving venv (see docs/gpu_deployment.md)")
    env = dict(os.environ, PATH=f"{Path(venv) / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}")
    env.pop("PYTHONPATH", None)
    if offline:
        env["HF_HUB_OFFLINE"] = "1"   # serve only what `fetch` pinned; never resolve a moving branch
    return env


def run(hw_path, name: str, exp_path, root: Path) -> dict:
    from . import run_grid
    plan, profiles = load(hw_path)
    p = profiles[name]
    exp = run_grid.load_cfg(exp_path)
    port = exp.get("port", 8000)
    run_dir = root / name
    if run_dir.exists():
        raise RuntimeError(f"{run_dir} exists; move it away to rerun (latency from a resumed run is not comparable)")
    if _port_busy(port):
        raise RuntimeError(f"a server already answers on :{port}; stop it first (one model fits at a time)")
    run_dir.mkdir(parents=True)
    cfg = grid_cfg(exp, p, run_dir)
    run_grid.prepare(cfg)                       # CPU; reuses current evidence files

    env = _venv_env(offline=True)
    smi = srv = None
    server = {"ready": False}
    started = time.time()
    try:
        if shutil.which("nvidia-smi"):
            smi = subprocess.Popen(["nvidia-smi", f"--query-gpu={SMI_FIELDS}", "--format=csv,noheader,nounits", "-lms", "1000"],
                                   stdout=open(run_dir / "smi.csv", "w", encoding="utf-8"), stderr=subprocess.DEVNULL)
            time.sleep(2)                       # baseline sample before the model loads
        cmd = [shutil.which("bash") or "bash", str(ROOT / "scripts" / "serve_model.sh"), str(run_dir / "server.args"), p["repo"], p["revision"],
               *serve_args(p, plan.hardware, port)]
        srv = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=open(run_dir / "server.log", "w", encoding="utf-8"),
                               stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.time() + exp.get("server_timeout_s", 1200)
        while time.time() < deadline and srv.poll() is None and not _port_busy(port):
            time.sleep(5)
        server["ready"] = srv.poll() is None and _port_busy(port)
        server["load_s"] = round(time.time() - started, 1)
        if server["ready"]:
            run_grid.run(cfg)
    finally:
        _stop(srv)
        _stop(smi, 5)
    server.update(parse_server_log((run_dir / "server.log").read_text(encoding="utf-8", errors="replace")))
    grid = grid_stats(run_dir / "grid.jsonl")
    p95 = int(grid["prompt_tokens"]["p95"]) if grid.get("live_rows") else None
    req = capacity.request_tokens(p95, 400, exp["n_samples"]) if p95 else None
    spec = next(m for m in plan.models if m.name == p["model"])
    est = capacity.serve(spec, plan.hardware, p["precision"], p95 or plan.prompt_tokens, 400, exp["n_samples"])
    rep = {"profile": p, "hardware": plan.hardware.name, "config_hash": cfg["_hash"],
           "server_args": (run_dir / "server.args").read_text(encoding="utf-8").strip()
           if (run_dir / "server.args").is_file() else None,
           "estimate": est, "server": server, "gpu": smi_stats(run_dir / "smi.csv"), "grid": grid,
           "verdict": verdict(server, grid, req), "wall_s": round(time.time() - started, 1)}
    (run_dir / "feasibility.json").write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("estimate", "server", "gpu", "grid", "verdict")}, indent=1))
    return rep


def report(root: Path) -> list[dict]:
    """One row per profile run: estimate next to measurement, and the verdict."""
    rows = []
    for f in sorted(root.glob("*/feasibility.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        g, s, gpu, v = r["grid"], r["server"], r["gpu"], r["verdict"]
        rows.append({"profile": r["profile"]["name"], "role": r["profile"]["role"],
                     "fallback": r["profile"]["fallback"], "feasible": v["feasible"],
                     "weights_gb_est": r["estimate"]["weights_gb"], "model_load_gib": s.get("model_load_gib"),
                     "kv_cache_gib": s.get("kv_cache_gib"), "conc_est": r["estimate"]["concurrent_requests"],
                     "conc_measured": v["concurrent_requests_measured"],
                     "peak_vram_mib": gpu.get("peak_mib"), "baseline_vram_mib": gpu.get("baseline_mib"),
                     "parse_rate": g.get("parse_rate"), "latency_p50_s": (g.get("latency_s") or {}).get("p50"),
                     "latency_p95_s": (g.get("latency_s") or {}).get("p95"),
                     "tok_per_s": g.get("completion_tokens_per_s"),
                     "prompt_p95": (g.get("prompt_tokens") or {}).get("p95"), "temp_max_c": gpu.get("temp_max_c"),
                     "reasons": "; ".join(v["reasons"])})
    if rows:
        with open(root / "feasibility.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(json.dumps(rows, indent=1))
    return rows


PAIR_KEY = ("case_id", "condition", "retrieval", "store_mode")
MAX_TOKEN_INCREASE = 0.25


def compare_sampling(grid_path, base: float = 0.0, alt: float = 1.5, n_boot: int = 10000) -> dict:
    """Paired DEV comparison of two presence-penalty arms of the same model on the same cells.

    Decision rule (fixed before the run): keep `base` unless `alt` has parse rate >= MIN_PARSE_RATE,
    a paired AC@1 gain whose 95 % incident-cluster bootstrap CI lies above 0, and mean completion
    tokens at most MAX_TOKEN_INCREASE above `base`. Confidence stability (consensus, spread of the
    verbal confidence across samples) is reported, not gated. DEV rows only."""
    from .metrics import cluster_bootstrap, mcnemar
    rows = [json.loads(l) for l in Path(grid_path).read_text(encoding="utf-8").splitlines() if l.strip()]
    if any(r.get("split_role") not in (None, "val") for r in rows):
        raise ValueError("sampling is compared on DEV (split_role val) rows only")
    arms: dict[float, dict] = {base: {}, alt: {}}
    for r in rows:
        pp = (r.get("sampling") or {}).get("presence_penalty")
        pp = 0.0 if pp is None else float(pp)
        if pp in arms:
            arms[pp][tuple(r[k] for k in PAIR_KEY)] = r
    keys = sorted(set(arms[base]) & set(arms[alt]))
    if not keys:
        raise ValueError(f"no cells answered under both presence_penalty={base} and {alt}")

    def summary(rs):
        return {"n": len(rs), "ac1": round(float(np.mean([bool(r["correct"]) for r in rs])), 4),
                "ac3": round(float(np.mean([bool(r["correct_at_3"]) for r in rs])), 4),
                "parse_rate": round(float(np.mean([r["parse_rate"] for r in rs])), 4),
                "conf_consensus": round(float(np.mean([r["conf_consensus"] for r in rs])), 4),
                "conf_verbal_sd": round(float(np.mean([r.get("conf_verbal_sd", np.nan) for r in rs])), 3),
                "completion_tokens": round(float(np.mean([r["completion_tokens"] or 0 for r in rs])), 1),
                "latency_s": round(float(np.mean([r["latency_s"] for r in rs])), 2)}

    a = [arms[base][k] for k in keys]
    b = [arms[alt][k] for k in keys]
    sa, sb = summary(a), summary(b)
    diff = cluster_bootstrap(np.column_stack([[bool(r["correct"]) for r in b], [bool(r["correct"]) for r in a]]),
                             [r["case_id"] for r in a], n=n_boot)
    tok_up = sb["completion_tokens"] / sa["completion_tokens"] - 1 if sa["completion_tokens"] else 0.0
    switch = sb["parse_rate"] >= MIN_PARSE_RATE and diff["lo"] > 0 and tok_up <= MAX_TOKEN_INCREASE
    rep = {"pairs": len(keys), "incidents": diff["n_clusters"], "base": {"presence_penalty": base, **sa},
           "alt": {"presence_penalty": alt, **sb},
           "ac1_gain": {k: round(v, 4) for k, v in diff.items() if k != "n_clusters"},
           "mcnemar": mcnemar([bool(r["correct"]) for r in a], [bool(r["correct"]) for r in b]),
           "completion_token_increase": round(tok_up, 3), "choice": alt if switch else base}
    print(json.dumps(rep, indent=1))
    return rep


ENV_CHECK = r"""
import json, sys, torch, vllm, transformers
from importlib.util import find_spec
from importlib.metadata import version, PackageNotFoundError
def ver(n):
    try:
        return version(n)
    except PackageNotFoundError:
        return None
cap = torch.cuda.get_device_capability(0) if torch.cuda.is_available() else None
free, total = torch.cuda.mem_get_info() if cap else (0, 0)
print(json.dumps({"vllm": vllm.__version__, "torch": torch.__version__, "torch_cuda": torch.version.cuda,
  "transformers": transformers.__version__, "cuda_available": torch.cuda.is_available(),
  "device": torch.cuda.get_device_name(0) if cap else None, "compute_capability": cap,
  "free_gib": round(free / 2**30, 2), "total_gib": round(total / 2**30, 2),
  "qwen3_5": find_spec("vllm.model_executor.models.qwen3_5") is not None,
  "bitsandbytes": ver("bitsandbytes")}))
"""


def pinned(req_file: Path) -> dict:
    return dict(re.findall(r"^([A-Za-z0-9_.-]+)==(\S+)", req_file.read_text(encoding="utf-8"), re.M))


def check_env() -> dict:
    """Versions and GPU as seen by the serving venv, checked against requirements-gpu.txt."""
    env = _venv_env(offline=False)
    out = subprocess.run(["python", "-c", ENV_CHECK], env=env, capture_output=True, text=True, check=True).stdout
    got = json.loads(out.strip().splitlines()[-1])
    want = pinned(ROOT / "requirements-gpu.txt")
    problems = [f"{k} {got.get(k)} != pinned {v}" for k, v in want.items() if k in got and got[k] != v]
    if not got["cuda_available"]:
        problems.append("torch sees no CUDA device")
    elif tuple(got["compute_capability"]) < (8, 9):
        problems.append(f"compute capability {got['compute_capability']} < 8.9: no FP8 kernels")
    problems += [f"{k} missing" for k in ("qwen3_5", "bitsandbytes") if not got[k]]
    got["problems"] = problems
    print(json.dumps(got, indent=1))
    return got


def fetch(hw_path, names: list[str]) -> dict:
    """Download the pinned snapshot of each profile into the HF cache and confirm the commit."""
    from huggingface_hub import snapshot_download
    _, profiles = load(hw_path)
    out = {}
    for n in names:
        p = profiles[n]
        path = Path(snapshot_download(p["repo"], revision=p["revision"]))
        if path.name != p["revision"]:
            raise RuntimeError(f"{p['repo']}: snapshot {path.name} != pinned {p['revision']}")
        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        out[n] = {"repo": p["repo"], "revision": p["revision"], "path": str(path), "gb": round(size / 1e9, 2)}
    print(json.dumps(out, indent=1))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("list", "check-env", "fetch", "run"):
        s = sub.add_parser(c)
        s.add_argument("hw")
        if c == "fetch":
            s.add_argument("profiles", nargs="+")
        if c == "run":
            s.add_argument("profile")
            s.add_argument("--exp", default=str(ROOT / "configs" / "exp" / "gpu-feasibility.yaml"))
            s.add_argument("--root", default="results_feasibility")
    s = sub.add_parser("report")
    s.add_argument("--root", default="results_feasibility")
    s = sub.add_parser("compare-sampling")
    s.add_argument("grid")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        plan, profiles = load(a.hw)
        for p in profiles.values():
            spec = next(m for m in plan.models if m.name == p["model"])
            est = capacity.serve(spec, plan.hardware, p["precision"], plan.prompt_tokens, plan.max_tokens, plan.n_samples)
            print(json.dumps({"name": p["name"], "role": p["role"], "repo": p["repo"], "revision": p["revision"],
                              "fallback": p["fallback"], "estimate": est,
                              "serve": f"bash scripts/serve_model.sh <args-file> {p['repo']} {p['revision']} "
                                       + " ".join(serve_args(p, plan.hardware, 8000))}))
    elif a.cmd == "check-env":
        sys.exit(1 if check_env()["problems"] else 0)
    elif a.cmd == "fetch":
        fetch(a.hw, a.profiles)
    elif a.cmd == "run":
        run(a.hw, a.profile, a.exp, Path(a.root))
    elif a.cmd == "compare-sampling":
        compare_sampling(a.grid)
    else:
        report(Path(a.root))


if __name__ == "__main__":
    main()
