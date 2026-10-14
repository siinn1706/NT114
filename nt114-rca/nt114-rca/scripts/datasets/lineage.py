"""Incident registry, mirror completeness and lineage checks over data/raw (read-only).

Reads label files and archive listings only; never extracts or transforms telemetry.
Writes data/manifests/{incidents.jsonl, lineage-report.json,
mirror-completeness-rcaeval.json, mirror-completeness-cloud-opsbench.json}.
Stdlib only; run with ``python -I scripts/datasets/lineage.py``.
"""

import collections
import csv
import hashlib
import io
import json
import os
import re
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
MAN = os.path.join(ROOT, "data", "manifests")
UA = {"User-Agent": "nt114-rca-acquire/1"}
SYSTEMS = {"ob": "online-boutique", "ss": "sock-shop", "tt": "train-ticket"}
LABEL_NAME = re.compile(r"(label|ground|truth|fault|root_?cause|inject|answer|record)[^/]*\.(json|jsonl|csv|txt|xlsx)$", re.I)


def registry():
    with open(os.path.join(ROOT, "scripts", "datasets", "sources.json"), encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)["sources"]}


def state(sid):
    p = os.path.join(ROOT, "data", ".state", sid + ".json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def src_dir(sid):
    base = os.path.join(RAW, sid)
    if not os.path.isdir(base):
        return None
    vs = sorted(os.listdir(base))
    return os.path.join(base, vs[0]) if len(vs) == 1 else None


def acquired(sid):
    return state(sid).get("files_verified") and src_dir(sid)


def http_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def git_sha1(path):
    h = hashlib.sha1(b"blob %d\0" % os.path.getsize(path))
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def row(source, reg, **kw):
    r = {"incident_id": None, "source_id": source, "lineage_group": reg[source].get("lineage_group"),
         "system": None, "root_cause_entity": None, "fault": None, "fault_cell": None,
         "inject_or_start_time": None, "modalities_present": None, "label_file": None,
         "label_in_path": False, "copy_of": None, "note": None}
    r.update(kw)
    return r


def modalities(files):
    names = set(files)
    return sorted(m for m, pre in (("metrics", ("metrics", "simple_metrics", "data")), ("logs", ("logs",)),
                                   ("traces", ("traces",))) if any(n.startswith(pre) for n in names))


# ---------------------------------------------------------------- RCAEval

def rcaeval_zenodo_cases(d):
    """{key: {files: {name: (size, crc)}, inject_bytes, dataset, system, cell}} from zip central directories."""
    cases = collections.defaultdict(lambda: {"files": {}})
    for zname in sorted(os.listdir(d)):
        if not zname.endswith(".zip"):
            continue
        with zipfile.ZipFile(os.path.join(d, zname)) as z:
            for i in z.infolist():
                m = re.search(r"(RE[123])-(OB|SS|TT)/([^/]+)/(\d+)/([^/]+)$", i.filename)
                if not m:
                    continue
                ds, sysc, cell, inst, fn = m.groups()
                key = "%s%s_%s_%s" % (ds.lower(), sysc.lower(), cell, inst)
                c = cases[key]
                c.update(dataset=ds, system=sysc.lower(), cell=cell, rep=inst, archive=zname)
                c["files"][fn] = (i.file_size, "%08x" % i.CRC)
                if fn == "inject_time.txt":
                    c["inject_bytes"] = z.read(i)
    return {k: v for k, v in cases.items() if "inject_bytes" in v}


def rcaeval_hf_cases(d):
    cases = collections.defaultdict(lambda: {"files": {}})
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name)
        if not os.path.isdir(p):
            continue
        for fn in os.listdir(p):
            cases[name]["files"][fn] = os.path.getsize(os.path.join(p, fn))
        it = os.path.join(p, "inject_time.txt")
        if os.path.exists(it):
            with open(it, "rb") as f:
                cases[name]["inject_bytes"] = f.read()
    return {k: v for k, v in cases.items() if "inject_bytes" in v}


def split_cell(cell):
    svc, _, fault = cell.rpartition("_")
    return svc, fault


def rcaeval(reg, rows):
    zd, hd = acquired("rcaeval-zenodo"), acquired("rcaeval-hf")
    report = {"zenodo_present": bool(zd), "hf_present": bool(hd)}
    z = rcaeval_zenodo_cases(zd) if zd else {}
    for k, c in sorted(z.items()):
        svc, fault = split_cell(c["cell"])
        rows.append(row("rcaeval-zenodo", reg, incident_id="rcaeval:" + k, system=SYSTEMS[c["system"]],
                        root_cause_entity=svc, fault=fault, fault_cell="%s/%s/%s" % (c["dataset"], c["system"], c["cell"]),
                        inject_or_start_time=c["inject_bytes"].decode().strip(), modalities_present=modalities(c["files"]),
                        label_file="%s:%s-%s/%s/%s/inject_time.txt" % (c["archive"], c["dataset"], c["system"].upper(),
                                                                     c["cell"], c["rep"]),
                        label_in_path=True))
    if not hd:
        return report
    h = rcaeval_hf_cases(hd)
    by_inject = {(k[:5], c["inject_bytes"]): k for k, c in z.items()}
    mapping, unmatched = {}, []
    for k, c in sorted(h.items()):
        if k in z and z[k]["inject_bytes"] == c["inject_bytes"]:
            mapping[k] = k
        elif (k[:5], c["inject_bytes"]) in by_inject:
            mapping[k] = by_inject[(k[:5], c["inject_bytes"])]
        else:
            unmatched.append(k)
    renamed = sorted((h_k, z_k) for h_k, z_k in mapping.items() if h_k != z_k)
    same_key_diff_inject = sorted(k for k in h if k in z and z[k]["inject_bytes"] != h[k]["inject_bytes"])
    only_zenodo = sorted(set(z) - set(mapping.values()))
    mod_diff, aux_only_zenodo, only_hf_files = [], collections.Counter(), collections.Counter()
    header_only_traces = []
    for hk, zk in sorted(mapping.items()):
        zf, hf = z[zk]["files"], h[hk]["files"]
        zm, hm = modalities(zf), modalities(hf)
        if zm != hm:
            mod_diff.append({"hf": hk, "zenodo": zk, "zenodo_modalities": zm, "hf_modalities": hm})
        if zf.get("traces.csv", (None,))[0] == 116 and "traces" not in hm:
            header_only_traces.append(zk)
        hf_stems = {n.split(".")[0] for n in hf}
        for n in zf:
            if n.split(".")[0] not in hf_stems:
                aux_only_zenodo[n] += 1
        z_stems = {n.split(".")[0] for n in zf}
        for n in hf:
            if n.split(".")[0] not in z_stems:
                only_hf_files[n] += 1
    for hk, c in sorted(h.items()):
        zk = mapping.get(hk) or (hk if hk in z else None)
        svc, fault = split_cell(z[zk]["cell"]) if zk else (None, None)
        rows.append(row("rcaeval-hf", reg, incident_id="rcaeval:" + (zk or hk), system=SYSTEMS.get(hk[3:5]),
                        root_cause_entity=svc, fault=fault,
                        fault_cell=("%s/%s/%s" % (z[zk]["dataset"], z[zk]["system"], z[zk]["cell"])) if zk else None,
                        inject_or_start_time=c["inject_bytes"].decode().strip(), modalities_present=modalities(c["files"]),
                        label_file="%s/inject_time.txt" % hk, label_in_path=True, copy_of="rcaeval-zenodo",
                        note="inject_time differs from the Zenodo case with the same key" if hk in same_key_diff_inject
                        else None))
    report.update({
        "zenodo_cases": len(z), "hf_cases": len(h), "matched_by_identical_inject_time": len(mapping),
        "renamed_cases": renamed, "same_key_different_inject_time": same_key_diff_inject,
        "hf_unmatched": unmatched, "zenodo_without_hf_copy": only_zenodo,
        "modality_differences": mod_diff,
        "hf_missing_logs": sorted(d["hf"] for d in mod_diff if "logs" in d["zenodo_modalities"]
                                  and "logs" not in d["hf_modalities"]),
        "zenodo_header_only_traces_absent_on_hf": sorted(header_only_traces),
        "files_only_on_zenodo_by_name": dict(sorted(aux_only_zenodo.items())),
        "files_only_on_hf_by_name": dict(sorted(only_hf_files.items())),
        "hf_root_cause_txt": sorted(k for k, c in h.items() if "root_cause.txt" in c["files"]),
    })
    orphans = [k for k in unmatched if k not in z]
    report["verdict"] = ("HF is a derived copy: %d of %d HF cases map to Zenodo cases by identical inject_time bytes; "
                         "%d share a Zenodo key with a different inject_time; %d have no Zenodo counterpart"
                         % (len(mapping), len(h), len(unmatched) - len(orphans), len(orphans)))
    return report


# ---------------------------------------------------------------- Cloud-OpsBench

def cloud_opsbench(reg, rows):
    d = acquired("cloud-opsbench")
    if not d:
        return {"present": False}
    s = reg["cloud-opsbench"]
    with open(os.path.join(d, "index.jsonl"), encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            rows.append(row("cloud-opsbench", reg, incident_id="cloud-opsbench:" + c["case_key"], system=c["system"],
                            root_cause_entity=c.get("fault_object"), fault=c.get("root_cause"),
                            fault_cell="%s/%s" % (c["system"], c["category"]), label_file="index.jsonl"))
    tree = http_json("https://api.github.com/repos/LLM4Ops/Cloud-OpsBench/git/trees/%s?recursive=1" % s["source_commit"])
    gh = {x["path"]: x["sha"] for x in tree["tree"] if x["type"] == "blob"}
    with open(os.path.join(ROOT, "data", "manifests", "filelists", "cloud-opsbench.json"), encoding="utf-8") as f:
        hf = json.load(f)["files"]
    common, equal, lfs_checked, mism, only_hf = 0, 0, 0, [], []
    for x in hf:
        p = x["path"]
        if p not in gh:
            only_hf.append(p)
            continue
        common += 1
        if x["anchor"]["algo"] == "git-sha1":
            sha = x["anchor"]["value"]
        else:
            sha = git_sha1(os.path.join(d, *p.split("/")))
            lfs_checked += 1
        if sha == gh[p]:
            equal += 1
        else:
            mism.append(p)
    only_gh = sorted(set(gh) - {x["path"] for x in hf})
    return {"present": True, "github_source_commit": s["source_commit"], "github_truncated": tree.get("truncated"),
            "hf_files": len(hf), "github_blobs": len(gh), "common_paths": common, "equal_blob_ids": equal,
            "lfs_files_hashed_locally": lfs_checked, "mismatched": mism, "only_hf": only_hf, "only_github": only_gh,
            "verdict": "identical content for all common paths" if not mism
            else "identical except %d common path(s): %s" % (len(mism), ", ".join(mism[:10]))}


# ---------------------------------------------------------------- other label sources

def petshop(reg, rows):
    d = acquired("petshop")
    if not d:
        return 0
    n = 0
    for dp, _, fns in sorted(os.walk(os.path.join(d, "dataset"))):
        if "target.json" in fns:
            with open(os.path.join(dp, "target.json"), encoding="utf-8") as f:
                t = json.load(f)
            rel = os.path.relpath(dp, d).replace("\\", "/")
            rows.append(row("petshop", reg, incident_id="petshop:" + rel, system="aws-petshop",
                            root_cause_entity=t["root_cause"]["node"], fault=t["root_cause"].get("metric"),
                            fault_cell=rel.split("/")[1], inject_or_start_time=str(t["target"].get("timestamp")),
                            modalities_present=["metrics"], label_file=rel + "/target.json"))
            n += 1
    return n


def nezha(reg, rows):
    d = acquired("nezha")
    if not d:
        return {}
    counts = {}
    for date in sorted(os.listdir(os.path.join(d, "rca_data"))):
        p = os.path.join(d, "rca_data", date, "%s-fault_list.json" % date)
        if not os.path.exists(p):
            continue
        system = "online-boutique" if date.startswith("2022") else "train-ticket"
        with open(p, encoding="utf-8") as f:
            fl = json.load(f)
        for hour in sorted(fl):
            for i, e in enumerate(fl[hour]):
                pod = e["inject_pod"]
                svc = re.sub(r"(-[0-9a-f]{8,10})?-[0-9a-z]{5}$", "", pod)
                rows.append(row("nezha", reg, incident_id="nezha:%s:%s:%d" % (date, hour, i), system=system,
                                root_cause_entity=svc, fault=e["inject_type"], fault_cell="%s/%s" % (svc, e["inject_type"]),
                                inject_or_start_time=e.get("inject_timestamp"), modalities_present=["logs", "metrics", "traces"],
                                label_file="rca_data/%s/%s-fault_list.json" % (date, date)))
                counts[system] = counts.get(system, 0) + 1
    return counts


def agenticopseval(reg, rows):
    d = acquired("agenticopseval")
    if not d:
        return {}
    out = {}
    with open(os.path.join(d, "AIOps2025", "groundtruth.jsonl"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                g = json.loads(line)
                rows.append(row("agenticopseval", reg, incident_id="aiops2025:" + g["uuid"], system="online-boutique (AIOps 2025)",
                                root_cause_entity=g.get("instance"), fault=g.get("fault_type"),
                                fault_cell="%s/%s" % (g.get("instance_type"), g.get("fault_type")),
                                inject_or_start_time=g.get("start_time"), label_file="AIOps2025/groundtruth.jsonl"))
                out["AIOps2025"] = out.get("AIOps2025", 0) + 1
    ak = os.path.join(d, "RCA100", "answer_key")
    for fn in sorted(os.listdir(ak)):
        if fn.endswith(".gt.json"):
            with open(os.path.join(ak, fn), encoding="utf-8") as f:
                g = json.load(f)
            task = fn.split(".")[0]
            case = os.path.join(d, "RCA100", "cases", task)
            mods = sorted(n.split(".")[0] for n in os.listdir(case) if n.endswith(".parquet")) if os.path.isdir(case) else None
            rows.append(row("agenticopseval", reg, incident_id="rca100:" + g["case_id"], system="otel-demo (RCA100)",
                            root_cause_entity=",".join(g.get("root_cause_entities") or []),
                            fault=",".join(g.get("root_cause_types") or []),
                            fault_cell=g["case_id"].split(".")[0], inject_or_start_time=g.get("time_range_start"),
                            modalities_present=mods, label_file="RCA100/answer_key/" + fn))
            out["RCA100"] = out.get("RCA100", 0) + 1
    # Cross-check every AIOps2025 archive against the publisher checksums.md5 as well as the LFS anchor.
    md5 = {}
    with open(os.path.join(d, "AIOps2025", "checksums.md5"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                v, name = line.split()
                md5[name] = v
    bad = []
    for name, v in md5.items():
        h = hashlib.md5()
        with open(os.path.join(d, "AIOps2025", name), "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        if h.hexdigest() != v:
            bad.append(name)
    out["AIOps2025_checksums_md5"] = {"listed": len(md5), "mismatched": bad}
    t107 = http_json("https://www.aiops.cn/gitlab/api/v4/projects/107/repository/tree?per_page=100&recursive=true")
    ids107 = {x["name"]: x["id"] for x in t107 if x["name"] in ("groundtruth.jsonl", "input.json")}
    ids110 = {n: git_sha1(os.path.join(d, "AIOps2025", n)) for n in ("groundtruth.jsonl", "input.json")}
    out["project107_blob_ids"] = {"project107": ids107, "project110_local": ids110,
                                  "identical": all(ids107.get(k) == v for k, v in ids110.items())}
    return out


def aiops2021(reg, rows):
    d = acquired("aiops2021-upstream")
    if not d:
        return 0
    n = 0
    with open(os.path.join(d, "aiops21_groundtruth.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(row("aiops2021-upstream", reg, incident_id="aiops2021:" + r["id"], system="AIOps 2021 (CCB)",
                            root_cause_entity=r["service"], fault=r["anomaly_type"], fault_cell=r["anomaly_type"],
                            inject_or_start_time=r["st_time"], label_file="aiops21_groundtruth.csv"))
            n += 1
    return n


def openrca(reg, rows):
    d = acquired("openrca")
    if not d:
        return {"present": False}
    out = {}
    for zn in ("Bank.zip", "Market.zip", "Telecom.zip"):
        p = os.path.join(d, zn)
        if not os.path.exists(p):
            continue
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():
                if name.endswith("record.csv"):
                    text = z.read(name).decode("utf-8-sig")
                    recs = list(csv.DictReader(io.StringIO(text)))
                    for i, r in enumerate(recs):
                        rows.append(row("openrca", reg, incident_id="openrca:%s:%d" % (name, i), system=zn[:-4],
                                        root_cause_entity=r.get("component"), fault=r.get("reason"),
                                        inject_or_start_time=r.get("datetime") or r.get("timestamp"),
                                        label_file="%s:%s" % (zn, name)))
                    out[name] = len(recs)
    out["total_records"] = sum(v for k, v in out.items() if k.endswith("record.csv"))
    return out


def label_candidates(reg):
    """Archive members whose names look like labels, for sources without a parsed label format."""
    out = {}
    for sid in ("anomod", "dejavu", "msds", "rcabench-fse26"):
        d = acquired(sid)
        if not d:
            out[sid] = "not acquired"
            continue
        found = []
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".zip"):
                with zipfile.ZipFile(os.path.join(d, fn)) as z:
                    found += ["%s:%s" % (fn, n) for n in z.namelist() if LABEL_NAME.search(n)]
        out[sid] = {"count": len(found), "examples": found[:15],
                    "note": "incident rows not extracted; label format not parsed (tar.gz and split zips not listed)"}
    return out


def main():
    reg = registry()
    rows = []
    report = {"rcaeval": rcaeval(reg, rows), "cloud_opsbench": cloud_opsbench(reg, rows),
              "petshop_incidents": petshop(reg, rows), "nezha_incidents": nezha(reg, rows),
              "agenticopseval": agenticopseval(reg, rows), "aiops2021_groundtruth_rows": aiops2021(reg, rows),
              "openrca": openrca(reg, rows), "label_candidates": label_candidates(reg)}
    rows.sort(key=lambda r: (r["source_id"], r["incident_id"]))
    groups = collections.defaultdict(lambda: {"rows": 0, "independent_incidents": 0, "copies": 0, "sources": set()})
    for r in rows:
        g = groups[r["lineage_group"]]
        g["rows"] += 1
        g["sources"].add(r["source_id"])
        if r["copy_of"]:
            g["copies"] += 1
        else:
            g["independent_incidents"] += 1
    cells = collections.Counter((r["source_id"], r["fault_cell"]) for r in rows if not r["copy_of"])
    lineage = {"groups": {k: dict(v, sources=sorted(v["sources"])) for k, v in sorted(groups.items())},
               "independent_incidents_total": sum(g["independent_incidents"] for g in groups.values()),
               "rows_total": len(rows),
               "fault_cells": {sid: {"cells": sum(1 for (s, _) in cells if s == sid),
                                     "max_repetitions": max((n for (s, _), n in cells.items() if s == sid), default=0)}
                               for sid in sorted({s for s, _ in cells})},
               "note": "aiops2021-upstream rows are lineage metadata (OpenRCA parent); its telemetry was not acquired"}
    os.makedirs(MAN, exist_ok=True)
    with open(os.path.join(MAN, "incidents.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    for name, obj in (("mirror-completeness-rcaeval.json", report["rcaeval"]),
                      ("mirror-completeness-cloud-opsbench.json", report["cloud_opsbench"]),
                      ("lineage-report.json", dict(report, lineage=lineage, rcaeval=None, cloud_opsbench=None))):
        with open(os.path.join(MAN, name), "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
    print(json.dumps({"rows": len(rows), "independent": lineage["independent_incidents_total"],
                      "groups": {k: v["independent_incidents"] for k, v in lineage["groups"].items()}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
