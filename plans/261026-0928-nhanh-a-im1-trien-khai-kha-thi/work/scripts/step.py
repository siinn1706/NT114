"""Run one literal-argv command and write a receipt v2 for it.

usage: python -X utf8 step.py --id ID --cwd DIR [--input F ...] [--output F ...]
       [--check TEXT ...] [--limitation TEXT ...] [--expected-nonzero] -- EXE ARG ...

Paths in --input/--output are relative to the plan directory (the receipt
workspace). stdout/stderr are kept in work/logs/<id>.{out,err}. The receipt goes
to work/receipts/<id>.json; an existing receipt is never overwritten.
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PLAN = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def eol(data):
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    cr = data.count(b"\r") - crlf
    kinds = [k for k, n in (("crlf", crlf), ("lf", lf), ("cr", cr)) if n]
    return "none" if not kinds else kinds[0] if len(kinds) == 1 else "mixed"


def main():
    if "--" not in sys.argv:
        sys.exit("missing -- before the command")
    split = sys.argv.index("--")
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--output", action="append", default=[])
    parser.add_argument("--check", action="append", default=[])
    parser.add_argument("--limitation", action="append", default=[])
    parser.add_argument("--expected-nonzero", action="store_true")
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args(sys.argv[1:split])
    argv = sys.argv[split + 1:]
    receipt = PLAN / "work" / "receipts" / f"{args.id}.json"
    if receipt.exists():
        sys.exit(f"receipt exists: {receipt}")
    before = {}
    for rel in args.input:
        data = (PLAN / rel).read_bytes()
        before[rel] = (sha(data), eol(data))
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    proc = subprocess.run(argv, cwd=args.cwd, capture_output=True, timeout=args.timeout, shell=False)
    logs = PLAN / "work" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{args.id}.out").write_bytes(proc.stdout)
    (logs / f"{args.id}.err").write_bytes(proc.stderr)
    inputs = []
    for rel, (h, e) in before.items():
        data = (PLAN / rel).read_bytes()
        inputs.append({"path": rel, "sha256_before": h, "sha256_after": sha(data),
                       "eol_before": e, "eol_after": eol(data), "mutation": "none"})
    outputs = [{"path": rel, "sha256": sha((PLAN / rel).read_bytes()), "created_this_attempt": True}
               for rel in args.output if (PLAN / rel).is_file()]
    missing = [rel for rel in args.output if not (PLAN / rel).is_file()]
    out_hashes = sorted(o["sha256"] for o in outputs)
    record = {
        "schema_version": 2, "id": args.id, "evidence_class": "deterministic",
        "host": "claude-code", "surface": "cli", "version": "unknown",
        "logical_entrypoint": "nckh-cook", "mode": "auto", "actual_invocation": " ".join(argv),
        "requested_model": "unknown", "resolved_model": "unknown", "effective_model": "unknown",
        "requested_effort": "unknown", "resolved_effort": "unknown", "effective_effort": "unknown",
        "permission_mode": "auto", "sandbox": "host-default",
        "tool_trace_reference": f"work/logs/{args.id}.out",
        "egress_trace_reference": f"work/logs/{args.id}.err",
        "exit_status": str(proc.returncode),
        "output_status": "missing:" + ",".join(missing) if missing else "present",
        "cost_coverage": "unknown", "cost": "unknown", "as_of": started,
        "skill_ids": ["nckh-cook"], "agent_ids": [], "plugin_ids": [],
        "input_hashes": [i["sha256_before"] for i in inputs], "output_hashes": out_hashes,
        "checks": args.check or ["exit status recorded"], "limitations": args.limitation or ["none recorded"],
        "closure_hash": sha("\n".join(out_hashes).encode()),
        "command_results": [{"command": " ".join(argv), "shell": "none (subprocess argv)", "cwd": args.cwd,
                             "exit_status": proc.returncode, "stdout_sha256": sha(proc.stdout),
                             "stderr_sha256": sha(proc.stderr), "expected_nonzero": args.expected_nonzero}],
        "input_files": inputs, "output_files": outputs,
    }
    receipt.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stdout.write(proc.stdout.decode("utf-8", "replace")[-3000:])
    sys.stderr.write(proc.stderr.decode("utf-8", "replace")[-3000:])
    print(f"\n[step] {args.id} exit={proc.returncode} outputs={len(outputs)} missing={missing}")
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
