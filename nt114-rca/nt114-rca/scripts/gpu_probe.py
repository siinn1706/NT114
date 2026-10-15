"""Record the GPU, driver, CUDA, PyTorch and free disk of this machine as JSON.

  python scripts/gpu_probe.py [--data-home data] [--out results/gpu_probe.json]

Read-only. On a machine without an NVIDIA GPU it reports `gpus: []` and exits 0. The `hardware`
block can be pasted into configs/hardware/*.yaml for `python -m rca.capacity`.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

QUERY = "name,memory.total,memory.used,memory.free,driver_version,compute_cap"


def _run(cmd: list[str]) -> str | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def parse_smi(csv: str) -> list[dict]:
    """Rows of `nvidia-smi --query-gpu=QUERY --format=csv,noheader,nounits`."""
    gpus = []
    for line in filter(str.strip, csv.splitlines()):
        name, total, used, free, driver, cap = [x.strip() for x in line.split(",")]
        gpus.append({"name": name, "memory_total_mib": int(total), "memory_used_mib": int(used),
                     "memory_free_mib": int(free), "driver_version": driver, "compute_capability": cap})
    return gpus


def cuda_driver_version(smi_header: str | None) -> str | None:
    m = re.search(r"CUDA Version:\s*([\d.]+)", smi_header or "")
    return m.group(1) if m else None


def torch_info() -> dict:
    try:
        import torch
    except ImportError:
        return {"installed": False}
    info = {"installed": True, "version": torch.__version__, "cuda_build": torch.version.cuda,
            "cuda_available": torch.cuda.is_available()}
    if info["cuda_available"]:
        free, total = torch.cuda.mem_get_info()
        info.update(device=torch.cuda.get_device_name(0), bf16=torch.cuda.is_bf16_supported(),
                    free_gib=round(free / 2**30, 2), total_gib=round(total / 2**30, 2))
    return info


def probe(data_home: str = "data") -> dict:
    smi = shutil.which("nvidia-smi")
    gpus = parse_smi(_run([smi, f"--query-gpu={QUERY}", "--format=csv,noheader,nounits"]) or "") if smi else []
    disk = shutil.disk_usage(Path(data_home) if Path(data_home).exists() else Path.cwd())
    rep = {"probed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "platform": platform.platform(),
           "python": sys.version.split()[0], "gpus": gpus,
           "cuda_driver": cuda_driver_version(_run([smi]) if smi else None),
           "nvcc": (re.findall(r"release ([\d.]+)", _run(["nvcc", "--version"]) or "") or [None])[0],
           "torch": torch_info(), "disk_free_gib": round(disk.free / 2**30, 1)}
    if gpus:
        g = gpus[0]
        rep["hardware"] = {"name": re.sub(r"[^a-z0-9]+", "-", g["name"].lower()).strip("-"),
                           "vram_gb": round(g["memory_total_mib"] * 2**20 / 1e9, 2),
                           "reserved_gb": round(g["memory_used_mib"] * 2**20 / 1e9, 2)}
    return rep


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-home", default="data")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rep = probe(a.data_home)
    text = json.dumps(rep, indent=1)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return rep


if __name__ == "__main__":
    main()
