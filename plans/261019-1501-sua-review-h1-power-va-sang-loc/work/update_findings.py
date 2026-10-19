"""Apply the review-repair evidence updates to the literature review's findings.csv (idempotent).

- H2 sources: record the open-access copies OpenAlex lists and why the agent could not read them.
- SADE (F-037): full text now read (arXiv 2605.04530).
- New findings F-054..F-056 from the Perplexity-assisted challenge round, each checked in the original paper.

usage: python -I update_findings.py
"""
import csv
from pathlib import Path

F = Path(__file__).resolve().parents[2] / "261019-1045-chon-dong-gop-khoa-hoc-qua-tong-quan-elicit" / "work" / "findings.csv"
RG = ("Open-access copy listed by OpenAlex (ResearchGate DOI {d}); the agent was stopped by a Cloudflare bot check "
      "on 2026-10-19 and does not solve CAPTCHAs, so the full text stays unread. ")
UPDATES = {
    "F-033": {"verified_full_text": "unavailable",
              "uncertainty": "high: " + RG.format(d="10.13140/rg.2.2.15499.04644") + "Abstract only; shared authors with VerifyRCA (F-049)"},
    "F-034": {"verified_full_text": "unavailable",
              "uncertainty": "high: " + RG.format(d="10.13140/rg.2.2.28829.88803") + "Abstract only; off-topic references (F-049)"},
    "F-035": {"verified_full_text": "unavailable",
              "uncertainty": "high: " + RG.format(d="10.13140/rg.2.2.29081.17765") + "Abstract only"},
    "F-037": {"claim": "SADE separates evidence acquisition from hypothesis commitment with a phase-gated workflow under a fixed "
                       "20-turn budget and improves root-cause F1 by 36.9 pp over the NIKA-native ReAct + GPT-5 baseline (21.5 pp over a same-backbone Claude-Code baseline) on 523 held-out "
                       "network-troubleshooting incidents; the budget is a fixed cap, not a learned acquisition policy",
              "evidence_location": "private/fulltext/261019/2605.04530.txt L13-25 (abstract), L460-513 (Table II, 20-turn budget, F1), L779-782",
              "verified_full_text": "yes",
              "uncertainty": "medium: network troubleshooting (NIKA), not microservice RCA; fixed turn cap rather than budget-optimal acquisition",
              "source_url": "https://doi.org/10.1109/LCN67947.2026.11660797",
              "pub_status": "peer-reviewed: IEEE LCN 2026; arXiv 2605.04530"},
}
NEW = [
    {"finding_id": "F-054", "work_id": "", "source_url": "https://arxiv.org/abs/2306.13063",
     "pub_status": "peer-reviewed: ICLR 2024; arXiv 2306.13063",
     "claim": "Vanilla verbalized confidence is a weak failure predictor (GPT-4 mean AUROC 62.7%, close to chance), "
              "while sample consistency with 5 responses outperforms it, e.g. GSM8K AUROC 54.8% -> 92.7%",
     "evidence_location": "private/fulltext/261019/2306.13063.txt L429-440 (Sec. 5.1, Table 2), L524-536 (Table 3, Fig. 7)",
     "verified_full_text": "yes",
     "uncertainty": "medium: QA/reasoning tasks, GPT-3.5/GPT-4; gains are task-dependent (largest on arithmetic)",
     "decision_relevance": "H1 power prior: the literature AUROC 0.51-0.65 concerns verbal confidence; the H1 primary score is "
                           "consensus (sample agreement, n = 10), which can separate errors much better or not at all; "
                           "only a DEV pilot can tell",
     "hypothesis": "H1", "direction": "context", "transfer": "out-of-domain"},
    {"finding_id": "F-055", "work_id": "W00645", "source_url": "https://doi.org/10.1145/3793655.3793732",
     "pub_status": "peer-reviewed: FORGE@ICSE 2026; arXiv 2601.22208",
     "claim": "Withholding one modality during alert unification changes LLM RCA unevenly: removing metrics costs most "
              "localisation (e.g. Qwen 3 4B Delta LA = -0.155), removing logs mainly hurts fault-type accuracy "
              "(Delta TA = -0.128), and removing traces can improve propagation-path and hypothesis accuracy (up to +0.28 / +0.06)",
     "evidence_location": "private/fulltext/261019/2601.22208.txt L878-893 (RQ2 holdout experiments)",
     "verified_full_text": "yes",
     "uncertainty": "medium: GAIA and OpenRCA, six open models; no confidence or abstention measured",
     "decision_relevance": "H1 design: controlled modality removal on LLM RCA is established (not novel by itself) and its effect "
                           "is heterogeneous, so a pooled single-modality endpoint must be reported per condition too",
     "hypothesis": "H1", "direction": "overlaps", "transfer": "in-domain"},
    {"finding_id": "F-056", "work_id": "",
     "source_url": "repo:plans/261019-1501-sua-review-h1-power-va-sang-loc/research/h1-endpoint-va-power.md",
     "pub_status": "internal (design simulation, 2026-10-19)",
     "claim": "With the actual E1 estimator, injection clustering, 11-level consensus ties and percentile cluster bootstrap, "
              "the fixed-coverage (0.7) gain MDE at 80% power is about 0.05-0.06 on RCAEval full and the pooled single-modality "
              "set, 0.05 on AIOps2025 and 0.08-0.10 on Nezha / RCA100 (alpha 0.05), under a binomial-logit generator",
     "evidence_location": "plans/261019-1501-sua-review-h1-power-va-sang-loc/work/out/h1-mde.csv; h1-power-grid.csv",
     "verified_full_text": "yes",
     "uncertainty": "high: depends on the assumed consensus distribution and ICC 0.5; synthetic, replaced by DEV-informed parameters later",
     "decision_relevance": "Replaces the AUROC >= 0.75 gate and the MDE/sqrt(c) approximation; H1 is not underpowered by construction",
     "hypothesis": "H1", "direction": "context", "transfer": "in-domain"},
    {"finding_id": "F-057", "work_id": "W01612", "source_url": "https://arxiv.org/abs/2608.08968",
     "pub_status": "peer-reviewed: ASE 2026 (DOI 10.1145/3832783.3834335); arXiv 2608.08968",
     "claim": "GALA+ has an LLM investigator emit a root-cause confidence in [0, 1] per microservice candidate and uses a "
              "threshold (best near 0.6) only to stop or extend graph exploration; no abstention, calibration or "
              "risk-coverage evaluation is reported",
     "evidence_location": "private/fulltext/261019/2608.08968.txt L413-430 (consolidated confidence), L480-496 (stop rule), L1139-1142 (theta sweep)",
     "verified_full_text": "yes",
     "uncertainty": "low for what is reported; confidence is a search-control signal of an agent pipeline, not a deferral rule",
     "decision_relevance": "H1 novelty: closest in-domain use of LLM confidence thresholds in microservice RCA; does not pre-empt "
                           "matched-coverage abstention; surfaced by the Perplexity challenge round",
     "hypothesis": "H1", "direction": "overlaps", "transfer": "in-domain"},
]

rows = list(csv.DictReader(open(F, encoding="utf-8")))
fields = list(rows[0])
for r in rows:
    r.update(UPDATES.get(r["finding_id"], {}))
have = {r["finding_id"] for r in rows}
rows += [{k: n.get(k, "") for k in fields} for n in NEW if n["finding_id"] not in have]
with open(F, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} findings; updated {sorted(UPDATES)}; new {[n['finding_id'] for n in NEW if n['finding_id'] not in have]}")

