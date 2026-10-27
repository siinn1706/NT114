"""Phase 05: agreement between first and second screener on the double sample (protocol §6).

usage: python -X utf8 -I kappa.py PREFIX S1 S2  -> work/screen/kappa-<PREFIX>.json
kappa_include: Cohen's kappa on include vs not-include over all double-screened rows.
kappa_inc_exc: Cohen's kappa over rows both screeners decided include or exclude.
kappa_include_abstract: kappa_include restricted to rows with an abstract; this is the gate, because title-only
rows are needs-review for both screeners by rule and would inflate agreement.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, read_csv  # noqa: E402


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    labels = sorted({x for p in pairs for x in p})
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


prefix, s1, s2 = sys.argv[1:4]
inp = WORK / "screen" / "input"
manifest = json.loads((inp / f"dbl-{prefix}-manifest.json").read_text(encoding="utf-8"))
# Forced rank-band ids may belong to another prefix, so first-screener rows come from every merged table.
first = {}
for merged in sorted((WORK / "screen").glob(f"*-{s1}-merged.csv")):
    if not merged.name.startswith(("all", "all2")):
        first.update({r["openalex_id"]: r for r in read_csv(merged)})
second = {}
for b in manifest["batches"]:
    second.update({r["openalex_id"]: r for r in read_csv(WORK / "screen" / f"{b['batch']}-{s2}.csv")})
assert set(second) == set(manifest["reasons"])
ids = sorted(second)
pairs = [(first[i]["decision"], second[i]["decision"]) for i in ids]
inc = [(a == "include", b == "include") for a, b in pairs]
ie = [(a, b) for a, b in pairs if {a, b} <= {"include", "exclude"}]
abs_ids = [i for i in ids if first[i]["read_level"] == "abstract"]
inc_abs = [(first[i]["decision"] == "include", second[i]["decision"] == "include") for i in abs_ids]
labels = ["include", "exclude", "needs-review", "context-survey"]
out = {"n": len(ids), "kappa_include": kappa(inc), "kappa_inc_exc": kappa(ie), "n_inc_exc": len(ie),
       "kappa_include_abstract": kappa(inc_abs), "n_abstract": len(abs_ids),
       "confusion_s1_rows_s2_cols": {a: {b: sum(p == (a, b) for p in pairs) for b in labels} for a in labels},
       "abs_agreement": {k: round(sum(first[i][k] == second[i][k] for i in ids) / len(ids), 4) for k in ("R1", "R2", "R3")},
       "threshold": 0.7,
       "disagreements": [{"openalex_id": i, "reason": manifest["reasons"][i], "s1": first[i]["decision"],
                          "s2": second[i]["decision"], "s1_R": first[i]["R_total"], "s2_R": second[i]["R_total"]}
                         for i in ids if first[i]["decision"] != second[i]["decision"]]}
out["pass"] = out["kappa_include_abstract"] is not None and out["kappa_include_abstract"] >= 0.7
(WORK / "screen" / f"kappa-{prefix}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps({k: out[k] for k in ("n", "kappa_include", "kappa_include_abstract", "n_abstract", "kappa_inc_exc", "n_inc_exc", "abs_agreement", "pass")}))
