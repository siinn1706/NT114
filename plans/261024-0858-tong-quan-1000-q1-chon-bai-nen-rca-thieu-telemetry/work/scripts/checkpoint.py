"""Commit one deterministic batch to work/state.json after its receipt exists (protocol §11).

usage: python -X utf8 -I checkpoint.py PHASE BATCH RECEIPT_ID --in F [--in F ...] --out F [--out F ...] [--note TEXT]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN, WORK, commit_batch, load_state, next_attempt  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("phase"); ap.add_argument("batch"); ap.add_argument("receipt")
ap.add_argument("--in", dest="inputs", action="append", default=[])
ap.add_argument("--out", dest="outputs", action="append", required=True)
ap.add_argument("--note", default="")
a = ap.parse_args()
receipt = WORK / "receipts" / f"{a.receipt}.json"
if str(json.loads(receipt.read_text(encoding="utf-8"))["exit_status"]) != "0":
    raise SystemExit("receipt exit is not 0")
state = load_state()
attempt = f"{a.batch}-a{next_attempt(state, a.phase, a.batch):02d}"
commit_batch(state, a.phase, a.batch, [PLAN / p for p in a.outputs], inputs=[PLAN / p for p in a.inputs],
             attempt=attempt, receipt=f"work/receipts/{a.receipt}.json", **({"note": a.note} if a.note else {}))
print(attempt)
