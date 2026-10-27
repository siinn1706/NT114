"""Phase 04: export T0 records as nckh-literature offline-import inputs (40 records per file, the tool's import ceiling).

usage: python -X utf8 -I build-dossier.py T0_CSV TAG  -> work/dossier/input/<TAG>-NN.json (refuses to overwrite)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, read_csv, sha_file  # noqa: E402
from queries import load_queries  # noqa: E402

PROTOCOL = {
    "revision": "frozen-261024",
    "question": "Which Q1 journal paper since 2020 is the best base to reproduce, study and improve for the MVP "
                "'microservice RCA with a single LLM under missing telemetry'?",
    "mode": "scoping",
    "queries": [q["query"] for q in load_queries()],
    "sources": ["OpenAlex", "reused corpus 11/10 (seed)", "Crossref abstract fill", "Semantic Scholar abstract fill"],
    "as_of": "2026-10-24",
    "inclusion": ["I1 software-system operation", "I2 RCA/fault localization/incident diagnosis",
                  "I3 method or empirical study with evaluation"],
    "exclusion": ["E1 RCA outside software", "E2 security only", "E3 hardware only", "E4 no empirical evaluation",
                  "E5 survey -> context-survey", "E6 no abstract", "E7 detection only"],
    "scope": {"population": "operated software systems (microservice, cloud-native, online services, distributed systems)",
              "concept": "failure diagnosis (RCA, fault localization, incident diagnosis), LLM and missing telemetry preferred",
              "context": "studies with empirical evaluation"},
    "screening_policy": "protocol.md section 6, frozen sha256 in work/protocol-freeze.json",
}

src, tag = Path(sys.argv[1]), sys.argv[2]
out = WORK / "dossier" / "input"
out.mkdir(parents=True, exist_ok=True)
rows = sorted(read_csv(src), key=lambda r: r["openalex_id"])
files = []
for n, i in enumerate(range(0, len(rows), 40)):
    cands = []
    for r in rows[i:i + 40]:
        ids = {"openalex": r["openalex_id"]}
        if r["doi"]:
            ids["doi"] = r["doi"]
        if r["arxiv"]:
            ids["arxiv"] = r["arxiv"]
        cands.append({"title": r["title"], "identifiers": ids, "abstract": r["abstract"],
                      "status": "retracted" if r["is_retracted"] in ("1", "True", "true") else "current"})
    path = out / f"{tag}-{n:02d}.json"
    with open(path, "x", encoding="utf-8", newline="\n") as handle:
        json.dump({"protocol": PROTOCOL, "candidates": cands, "task_id": "261024-literature-1000-q1",
                   "attempt_id": f"{tag}-{n:02d}"}, handle, ensure_ascii=False, indent=1)
    files.append({"path": path.name, "n": len(cands), "sha256": sha_file(path)})
(out / f"{tag}-manifest.json").write_text(json.dumps({"source": str(src).replace("\\", "/"), "source_sha256": sha_file(src),
                                                       "files": files}, indent=1), encoding="utf-8")
print(json.dumps({"records": len(rows), "files": len(files)}))
