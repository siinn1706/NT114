"""Mechanical consistency checks of the phase-01 drafts and the path-selection spec.

usage: python -X utf8 check-phase01-consistency.py PLAN_WORK_DIR OUT_JSON

Checks structure and cross-references only; it does not judge the content.
Exit 1 when any check fails.
"""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ARMS = {"l0", "ra", "ra_im1", "ra_im1_shuf"}
DECISIONS = {"D2", "D3", "D6", "D7", "D8", "D10", "D11", "D12", "D13"}
FILES = ["data-contract-addendum-im1-draft.md", "arm-ids.csv", "decision-check-map.csv",
         "path-selection-spec.md", "h1-membership-recheck.csv"]
APPROVAL_CLAIMS = [r"đã được (chủ dự án )?duyệt", r"chủ dự án đã duyệt", r"approved by the owner", r"owner approved"]


def main():
    work, out = Path(sys.argv[1]), Path(sys.argv[2])
    res = []

    def check(name, ok, detail=""):
        res.append({"check": name, "ok": bool(ok), "detail": detail})

    arms = list(csv.DictReader((work / "arm-ids.csv").open(encoding="utf-8")))
    ids = [a["arm_id"] for a in arms]
    check("arm ids are exactly l0, ra, ra_im1, ra_im1_shuf", set(ids) == ARMS and len(ids) == len(ARMS), ids)
    check("every arm makes one call per answer", all(a["llm_calls_per_answer"].startswith("1 call") for a in arms))
    check("retrieval is none for every arm", all(a["retrieval"] == "none" for a in arms))
    ts = {a["arm_id"]: a["train_structure"] for a in arms}
    check("train_structure: l0 and ra none; ra_im1 im1_frame; ra_im1_shuf im1_frame_shuffled",
          ts == {"l0": "none", "ra": "none", "ra_im1": "im1_frame", "ra_im1_shuf": "im1_frame_shuffled"}, ts)
    check("l0 is the existing unchanged arm with evidence.py v3 and prompt v1",
          [a for a in arms if a["arm_id"] == "l0"][0]["status"].startswith("existing")
          and "BUILDER_VERSION 3" in [a for a in arms if a["arm_id"] == "l0"][0]["evidence_builder"])

    dmap = list(csv.DictReader((work / "decision-check-map.csv").open(encoding="utf-8")))
    covered = {r["decision"] for r in dmap}
    check("decision map covers D2 D3 D6 D7 D8 D10 D11 D12 D13", DECISIONS <= covered, sorted(DECISIONS - covered))
    cids = [r["check_id"] for r in dmap]
    check("check ids unique", len(cids) == len(set(cids)))
    check("every row names a phase and an artifact", all(r["phase"].strip() and r["artifact"].strip() for r in dmap))

    add = (work / "data-contract-addendum-im1-draft.md").read_text(encoding="utf-8")
    sec_b = add.split("## B.")[1].split("## C.")[0]
    rows = [int(m) for m in re.findall(r"^\| (\d) \|", sec_b, flags=re.M)]
    check("addendum section B maps D11 conditions 1-7", rows == list(range(1, 8)), rows)
    check("addendum keeps retrieval = none meaning", "`retrieval = none` keeps its meaning" in add)
    check("addendum marked not approved", "chưa được duyệt" in add)
    spec = (work / "path-selection-spec.md").read_text(encoding="utf-8")
    claims = [p for p in APPROVAL_CLAIMS for t in (add, spec) if re.search(p, t)]
    check("no approval claim in addendum or spec", not claims, claims)
    named = set(re.findall(r"`(l0|ra|ra_im1|ra_im1_shuf)`", add + spec))
    check("arm ids named in addendum and spec exist", named <= ARMS, sorted(named))

    mem = list(csv.DictReader((work / "h1-membership-recheck.csv").open(encoding="utf-8")))
    totals = {r["role"]: int(r["records"]) for r in mem if r["kind"] == "total" and r["subset"] == "all"}
    table = re.findall(r"^\| (test|val) \| [^|]+\| (\d+) \| (\d+) \| (\d+) \| (\d+) \|", spec, flags=re.M)
    sums_ok = all(int(a) + int(b) + int(c) == int(t) == totals[role] for role, a, b, c, t in table)
    check("spec path counts sum to the recounted pool records (test 285, val 210)",
          len(table) == 5 and sums_ok, {"rows": len(table), "totals": totals})
    check("membership recount has no design mismatch",
          all(r["match"] == "True" for r in mem if r["kind"] == "check"))

    hashes = {f: hashlib.sha256((work / f).read_bytes()).hexdigest() for f in FILES}
    record = {"checks": res, "sha256": hashes, "failed": sum(not r["ok"] for r in res)}
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in res:
        print("PASS" if r["ok"] else "FAIL", r["check"], "" if r["ok"] else r["detail"])
    for f, h in hashes.items():
        print(h, f)
    sys.exit(1 if record["failed"] else 0)


if __name__ == "__main__":
    main()
