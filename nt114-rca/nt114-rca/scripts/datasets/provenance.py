"""Write data/provenance/<id>.json for every registry source from registry, pinned file list and state.

Values that were not read in a recorded step stay "UNKNOWN". Stdlib only;
run with ``python -I scripts/datasets/provenance.py``.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
U = "UNKNOWN"


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    reg = load(os.path.join(ROOT, "scripts", "datasets", "sources.json"))
    lineage = load(os.path.join(ROOT, "data", "manifests", "lineage-report.json"), {})
    groups = (lineage.get("lineage") or {}).get("groups", {})
    out_dir = os.path.join(ROOT, "data", "provenance")
    os.makedirs(out_dir, exist_ok=True)
    for s in reg["sources"]:
        sid = s["id"]
        st = load(os.path.join(ROOT, "data", ".state", sid + ".json"), {})
        fl = load(os.path.join(ROOT, "data", "manifests", "filelists", sid + ".json"), {})
        pv = s.get("provenance", {})
        files = fl.get("files", [])
        state = st.get("state") or "PENDING:not-started"
        if s.get("decision_state") and state == "PENDING:not-started":
            state = s["decision_state"]
        counts = st.get("counts") or {}
        last_ok = [h for h in st.get("history", []) if h["state"] in ("VERIFIED", "VERIFIED-LOCAL-ONLY",
                                                                       "PENDING:metadata-only")]
        rec = {
            "id": sid,
            "canonical_source_url": pv.get("canonical_url", U),
            "publication": pv.get("publication", U),
            "doi": s.get("doi") or U,
            "publisher_or_maintainer": pv.get("publisher", U),
            "license": s.get("license") if s.get("license") is not None else U,
            "license_evidence": pv.get("licence_evidence", U),
            "kind": s["kind"],
            "revision_or_version": s.get("revision") or s.get("record") or s.get("retrieved_tag") or U,
            "artefact_list": "data/manifests/filelists/%s.json" % sid if fl else U,
            "artefact_url_example": (files[0].get("url") or files[0].get("drive_id")) if files else U,
            "host_metadata": fl.get("host_meta", U),
            "metadata_pinned_at": fl.get("pinned_at", U),
            "retrieved_at": last_ok[-1]["at"] if last_ok else None,
            "file_count": {"expected": len(files) if files else U, "verified": counts.get("present_files") if
                           st.get("files_verified") else 0},
            "total_bytes": {"expected": sum(f["size"] or 0 for f in files) if files else U,
                            "verified": counts.get("bytes") if st.get("files_verified") else 0},
            "hash_list": "data/manifests/checksums.sha256 and checksums-levels.tsv" if st.get("files_verified") else None,
            "integrity_levels": st.get("integrity_levels") or sorted({f["integrity_level"] for f in files}) or U,
            "archive_audit": {k: v for k, v in (st.get("archive_audit") or {}).items() if k != "detail"} or None,
            "labels": pv.get("labels", U),
            "modalities": pv.get("modalities", U),
            "known_limitations": pv.get("limitations", []) + s.get("known_defects", []) + s.get("limitations", []),
            "lineage_group": s.get("lineage_group"),
            "lineage_edges": {k: s[k] for k in ("copy_of", "supersedes", "source_commit", "repo_pointer") if s.get(k)},
            "lineage_group_counts": groups.get(s.get("lineage_group")),
            "category": s.get("category"),
            "state": state,
            "reason": st.get("reason") or s.get("reason"),
            "next_action": st.get("next_action") or s.get("next_action"),
            "decisions": s.get("state_target"),
            "state_file": "data/.state/%s.json (git-ignored)" % sid,
        }
        tmp = os.path.join(out_dir, sid + ".json.tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
        os.replace(tmp, os.path.join(out_dir, sid + ".json"))
        print("%-26s %s" % (sid, state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
