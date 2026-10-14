"""List a remote zip's members via HTTP Range (central directory only; no data download).
Usage: python -I remote-zip-list.py OUT.json URL [URL...]"""
import json, struct, sys, urllib.request

def rng(url, start, end):
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}", "User-Agent": "nt114-metadata-check"})
    with urllib.request.urlopen(req, timeout=120) as r:
        total = int(r.headers["Content-Range"].split("/")[-1])
        return r.read(), total

def members(url):
    tail, total = rng(url, 0, 0)
    tail, _ = rng(url, max(0, total - 70000), total - 1)
    i = tail.rfind(b"PK\x05\x06")
    n, cd_size, cd_off = struct.unpack("<HII", tail[i + 10:i + 20])
    z = tail.rfind(b"PK\x06\x07")
    if z != -1 and (cd_off == 0xFFFFFFFF or n == 0xFFFF):
        (z64_off,) = struct.unpack("<Q", tail[z + 8:z + 16])
        rec, _ = rng(url, z64_off, z64_off + 55)
        n, cd_size, cd_off = struct.unpack("<QQQ", rec[32:56])
    cd, _ = rng(url, cd_off, cd_off + cd_size - 1)
    out, p = [], 0
    while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        crc, csz, usz, fl, el, cl = struct.unpack("<IIIHHH", cd[p + 16:p + 34])
        name = cd[p + 46:p + 46 + fl].decode("utf-8", "replace")
        out.append([name, usz, csz, f"{crc:08x}"])
        p += 46 + fl + el + cl
    return {"url": url, "total_bytes": total, "entries_declared": n, "entries": out}

res = []
for u in sys.argv[2:]:
    try:
        res.append(members(u))
        print(u, "entries", len(res[-1]["entries"]))
    except Exception as e:
        res.append({"url": u, "error": repr(e)})
        print(u, "ERROR", repr(e))
json.dump(res, open(sys.argv[1], "w", encoding="utf-8"))
