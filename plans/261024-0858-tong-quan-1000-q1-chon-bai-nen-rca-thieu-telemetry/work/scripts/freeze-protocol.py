"""Phase 01: hash the frozen protocol and initialise work/state.json (refuses to re-freeze)."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PLAN, WORK, load_state, now_utc, save_state, sha_file  # noqa: E402

state = load_state()
if state.get("protocol_sha256"):
    raise SystemExit("already frozen; changes after freeze are amendments")
text = (PLAN / "protocol.md").read_text(encoding="utf-8")
if 'revision: "frozen-' not in text:
    raise SystemExit("protocol revision is not frozen-*")
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PLAN, capture_output=True, text=True).stdout.strip()
screen_dir = WORK / "screen"
freeze = {
    "protocol": "protocol.md", "protocol_sha256": sha_file(PLAN / "protocol.md"), "frozen_at_utc": now_utc(),
    "git_head": head, "to_publication_date": "2026-10-24",
    "pre_freeze_changes": "work/amendments.md (section 'Trước freeze')",
    "query_probe_final": {"file": "work/query-probe-04.csv", "sha256": sha_file(WORK / "query-probe-04.csv"),
                          "note": "17 queries, all HTTP 200, page-1 AND-clause hit rate >= 0.854"},
    "regex_calibration": {"file": "work/regex-calibration-02.json",
                          "sha256": sha_file(WORK / "regex-calibration-02.json")},
    "protocol_review": {"file": "research/protocol-review.md",
                        "sha256": sha_file(PLAN / "research" / "protocol-review.md")},
    "phase01_deviations": [
        "step 4 probed with per-page 5 then 200 (not 1); the final probe file is query-probe-04.csv",
        "step 5 (30+30 regex check) replaced by calibration on 736 labelled records (amendment)",
    ],
    "screening_files_before_freeze": sorted(p.name for p in screen_dir.glob("*")) if screen_dir.exists() else [],
}
(WORK / "protocol-freeze.json").write_text(json.dumps(freeze, indent=1), encoding="utf-8")
state["protocol_sha256"] = freeze["protocol_sha256"]
state["to_publication_date"] = freeze["to_publication_date"]
state.setdefault("phases", {})["01"] = {"status": "committed", "frozen_at_utc": freeze["frozen_at_utc"],
                                        "receipt": "work/receipts/01-freeze-01.json"}
save_state(state)
print(json.dumps(freeze, indent=1))
