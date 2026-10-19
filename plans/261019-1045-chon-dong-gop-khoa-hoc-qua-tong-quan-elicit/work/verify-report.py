"""CPU-only checks for the literature-review report (no model calls, no network).

usage: python -I verify-report.py <report.md> <findings.csv> [--write-appendix]
With --write-appendix, replaces the <!-- FINDINGS-APPENDIX --> marker (or the previously generated
block) with one entry per finding, then runs the checks:
  1. every [F-xxx] cited in the report exists in findings.csv and in the appendix;
  2. every finding has the 11 required fields non-empty;
  3. every source_url starts with http, or with repo: pointing to an existing path;
  4. every relative Markdown link in the report resolves to an existing file;
  5. every FT evidence_location names a file that exists under private/fulltext/261019/.
Exit code 1 on any failure.
"""
import csv, re, sys
from pathlib import Path

REQ = ["finding_id", "source_url", "pub_status", "claim", "evidence_location", "verified_full_text", "uncertainty",
       "decision_relevance", "hypothesis", "direction", "transfer"]
START, END = "<!-- FINDINGS-APPENDIX -->", "<!-- /FINDINGS-APPENDIX -->"
report, fpath = Path(sys.argv[1]), Path(sys.argv[2])
root = report.resolve().parents[2]
F = list(csv.DictReader(open(fpath, encoding="utf-8")))
text = report.read_text(encoding="utf-8")

if "--write-appendix" in sys.argv:
    lines = [START, ""]
    for f in F:
        lines.append(f"- **[{f['finding_id']}]** {f['claim']}")
        lines.append(f"  - `source_url`: {f['source_url']} · `work_id`: {f['work_id'] or '—'} · `pub_status`: {f['pub_status']}")
        lines.append(f"  - `evidence_location`: {f['evidence_location']} · `verified_full_text`: {f['verified_full_text']}")
        lines.append(f"  - `uncertainty`: {f['uncertainty']}")
        lines.append(f"  - `decision_relevance`: {f['decision_relevance']}")
        lines.append(f"  - `hypothesis`: {f['hypothesis']} · `direction`: {f['direction']} · `transfer`: {f['transfer']}")
    lines += ["", END]
    block = "\n".join(lines)
    if END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, text, flags=re.S)
    else:
        text = text.replace(START, block)
    report.write_text(text, encoding="utf-8")

errors = []
ids = {f["finding_id"] for f in F}
appendix = text.split(START, 1)[1] if START in text else ""
body = text.split(START, 1)[0]
cited = set()
for grp in re.findall(r"\[(F-\d{3}(?:[,–\-\s]+F-\d{3})*)\]", body):
    parts = re.findall(r"F-\d{3}", grp)
    if "–" in grp and len(parts) == 2:  # range F-010–F-013
        a, b = (int(p[2:]) for p in parts)
        parts = [f"F-{i:03d}" for i in range(a, b + 1)]
    cited |= set(parts)
for c in sorted(cited - ids):
    errors.append(f"cited but not in findings.csv: {c}")
for c in sorted(cited):
    if f"[{c}]" not in appendix:
        errors.append(f"cited but not in appendix: {c}")
for f in F:
    for k in REQ:
        if not (f.get(k) or "").strip():
            errors.append(f"{f['finding_id']}: empty field {k}")
    u = f["source_url"]
    if u.startswith("repo:"):
        if not (root / u[5:].split("#")[0]).exists():
            errors.append(f"{f['finding_id']}: repo path missing {u}")
    elif not u.startswith("http"):
        errors.append(f"{f['finding_id']}: source_url not http/repo: {u}")
    m = re.match(r"private/fulltext/261019/(\S+?\.(?:txt|md))", f["evidence_location"])
    if m and not (root / "private" / "fulltext" / "261019" / m.group(1)).exists():
        errors.append(f"{f['finding_id']}: full-text file missing {m.group(1)}")
for link in re.findall(r"\]\((\.\.?/[^)#\s]+)(?:#[^)]*)?\)", text):
    if not (report.parent / link).resolve().exists():
        errors.append(f"broken link: {link}")
uncited = sorted(ids - cited)
print(f"findings={len(F)} cited={len(cited)} uncited_in_body={len(uncited)} {uncited}")
print("\n".join(errors) if errors else "ALL CHECKS PASSED")
sys.exit(1 if errors else 0)
