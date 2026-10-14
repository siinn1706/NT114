import json, re, collections, sys
zen = json.load(open(sys.argv[1], encoding="utf-8"))
hf = json.load(open(sys.argv[2], encoding="utf-8"))["siblings"]
z = collections.defaultdict(set); unsafe = []
for arc in zen:
    for name, usz, csz, crc in arc["entries"]:
        if name.startswith(("/", "\\")) or ".." in name.split("/") or re.match(r"^[A-Za-z]:", name):
            unsafe.append(name)
        m = re.search(r"(RE[123])-(OB|SS|TT)/([^/]+)/(\d+)/([^/]+)$", name)
        if m:
            ds, sysc, sf, inst, fn = m.groups()
            z[f"{ds.lower()}{sysc.lower()}_{sf}_{inst}"].add(fn)
h = collections.defaultdict(set)
for s in hf:
    p = s["rfilename"].split("/")
    if len(p) == 2: h[p[0]].add(p[1])
zc = {k for k, v in z.items() if "inject_time.txt" in v}; hc = set(h)
print("zenodo cases", len(zc), "hf cases", len(hc), "common", len(zc & hc))
print("only zenodo", sorted(zc - hc)[:20]); print("only hf", sorted(hc - zc)[:20])
def mods(files):
    return (any(f.startswith(("metrics","simple_metrics","data")) for f in files), any(f.startswith("logs") for f in files), any(f.startswith("traces") for f in files))
diff = [(k, sorted(z[k]), sorted(h[k])) for k in sorted(zc & hc) if mods(z[k]) != mods(h[k])]
print("modality mismatches", len(diff)); [print(" ", d) for d in diff[:10]]
print("hf cases without logs among re2/re3:", sorted(k for k in hc if k[:3] in ("re2","re3") and not mods(h[k])[1]))
print("zenodo cases without logs among re2/re3:", sorted(k for k in zc if k[:3] in ("re2","re3") and not mods(z[k])[1]))
print("hf root_cause.txt:", sorted(k for k in hc if "root_cause.txt" in h[k]))
print("zenodo extra file types:", collections.Counter(f for v in z.values() for f in v).most_common(15))
print("unsafe members", len(unsafe), unsafe[:5])
