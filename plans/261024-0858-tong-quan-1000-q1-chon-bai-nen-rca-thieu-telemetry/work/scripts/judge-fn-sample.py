"""Phase 04: record the screener's should_keep judgement (I1 and I2 per protocol §6) on the FN sample.

usage: python -X utf8 -I judge-fn-sample.py TAG  -> work/records/<TAG>-fn-judged.csv and work/<TAG>-fn-check.json
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, read_csv, write_csv  # noqa: E402

JUDGED = {"t0seed2": ({
    "W3197917898": "database self-diagnosis detects root causes of anomalies: I1 (DB operation) and I2",
    "W4410431126": "survey of failure analysis and fault diagnosis in AI systems: I1 and I2, would be E5 context-survey",
}, {
    "W7119533583": "IT operations reasoning benchmark; main task is Q&A on operational data, not diagnosis: I2 fails",
    "W4415185724": "data center operational data query assistant; no diagnosis task: I2 fails",
    "W7129050780": "source-code bug localization from bug reports, not system operation: I1 fails",
    "W7165520791": "communication-network alert interpretation: E1 telecom",
    "W4378648031": "configuration root cause in robots: outside software-system operation (E1)",
}), "t0seed4": ({}, {
    "W3198059351": "multivariate time-series anomaly detection and diagnosis on cyber-physical systems: I1 fails (E1)",
    "W3216877984": "organizational learning from information-system incidents; no diagnosis task: I2 fails",
    "W7119533583": "IT operations reasoning benchmark; main task is Q&A on operational data, not diagnosis: I2 fails",
    "W4378648031": "configuration root cause in robots: outside software-system operation (E1)",
    "W7124847402": "Open RAN cellular network automation: E1 telecom",
}), "t0full2": ({}, {
    "W3191614725": "practitioner survey on microservice design/monitoring/testing; no diagnosis task: I2 fails",
    "W4407900333": "small LM agent executing ICT operation procedures; no diagnosis task: I2 fails",
    "W7124784658": "LLMs resolving environment-related software crash bugs: debugging, not system operation (I1 fails)",
    "W7124847402": "Open RAN cellular network automation: E1 telecom",
    "W4416265819": "prognostics and health management of industrial equipment: E1",
}), "t0snow2": ({}, {
    "W4319915104": "SDN data-plane link/switch failure recovery review; recovery, not diagnosis: I2 fails (and E5)",
    "W7204634174": "LLM agent for security incident response (SOAR): E2 security only",
    "W4416922257": "LLM one-shot fault diagnosis on chiller sensor data: E1 outside software",
    "W4412434710": "time-series anomaly detection survey without localization: E7 and E5",
    "W4387382605": "ChatGPT for telecom intent-based network management; no diagnosis task: I2 fails (E1)",
}), "t0r2b": ({}, {
    "W4399657688": "LLM-assisted fault diagnosis for heterogeneous (mobile) network devices: E1 telecom access networks",
    "W4411550834": "causal GNN fault diagnosis on the Tennessee Eastman process: E1 outside software",
    "W4285131467": "Alibaba microservice call-graph characterization; no diagnosis task: I2 fails",
    "W3035061803": "performance-bug taxonomy and dataset: software engineering, not system operation (I1 fails)",
    "W3201728132": "temporal isolation of NFV containers in OpenStack; no diagnosis task: I2 fails",
})}


def upper(k, n):
    """Clopper-Pearson 95% upper bound: p with P(X <= k | n, p) = 0.025, by bisection."""
    if k == n:
        return 1.0
    cdf = lambda p: sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))
    lo, hi = k / n, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if cdf(mid) > 0.025 else (lo, mid)
    return hi


tag = sys.argv[1]
KEEP, NEAR = JUDGED[tag]
rows = read_csv(WORK / "records" / f"{tag}-fn-sample.csv")
for r in rows:
    r["should_keep"] = int(r["openalex_id"] in KEEP)
    r["note"] = KEEP.get(r["openalex_id"]) or NEAR.get(r["openalex_id"], "")
write_csv(WORK / "records" / f"{tag}-fn-judged.csv", rows, list(rows[0]))
out = {"source": f"records/{tag}-fn-sample.csv", "rule": "protocol §4: >1 FN borderline or >0 FN neither -> regex amendment"}
for s in ("borderline", "neither"):
    k = sum(r["should_keep"] for r in rows if r["stratum"] == s)
    n = sum(r["stratum"] == s for r in rows)
    out[s] = {"n": n, "fn": k, "cp95_upper": round(upper(k, n), 4)}
out["amendment_required"] = out["borderline"]["fn"] > 1 or out["neither"]["fn"] > 0
(WORK / f"{tag}-fn-check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out))
