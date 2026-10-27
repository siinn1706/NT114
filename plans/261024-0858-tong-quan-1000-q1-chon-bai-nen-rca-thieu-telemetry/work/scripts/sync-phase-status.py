"""Phase 10: reconcile stale phase-level status in work/state.json with the committed batches.

usage: python -X utf8 -I sync-phase-status.py SPEC_JSON OUT_CSV
SPEC_JSON maps phase -> {"status": ..., "receipt": ..., "reason": ...}. A phase is updated only when
every batch is committed and the cited receipt exists. The old status, reason and note move to
status_history; batches and their attempts are never touched. OUT_CSV lists, per phase, the batch
count, committed count, batches whose recorded outputs still match on disk, and the decision.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN, load_state, now_utc, save_state, sha_file  # noqa: E402

spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = sys.argv[2]
state = load_state()
rows = []
for phase, want in spec.items():
    ph = state["phases"].setdefault(phase, {"batches": {}})
    batches = ph.get("batches", {})
    committed = [b for b, e in batches.items() if e.get("status") == "committed"]
    intact = [b for b in committed if all((PLAN / o["path"]).is_file() and sha_file(PLAN / o["path"]) == o["sha256"]
                                          for o in batches[b].get("outputs", []))]
    receipt_ok = (PLAN / want["receipt"]).is_file()
    ok = receipt_ok and len(committed) == len(batches)
    if ok:
        old = {k: ph[k] for k in ("status", "reason", "blocked_reason", "note") if k in ph}
        ph.setdefault("status_history", []).append({**old, "replaced_at": now_utc()})
        for k in ("blocked_reason", "note"):
            ph.pop(k, None)
        ph.update(status=want["status"], receipt=want["receipt"], reason=want["reason"])
    rows.append({"phase": phase, "batches": len(batches), "committed": len(committed),
                 "outputs_intact": len(intact), "receipt": want["receipt"], "receipt_exists": receipt_ok,
                 "status": want["status"] if ok else ph.get("status"), "updated": ok})
save_state(state)
with open(out, "w", encoding="utf-8", newline="") as h:
    w = csv.DictWriter(h, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(json.dumps(rows, ensure_ascii=False))
