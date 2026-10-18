# 03 — Elicit search pack

## Executive summary

These five questions are what the H1–H3 decision depends on ([02](02_research_directions.md)).
They put empirical papers first: papers with datasets, baselines, ablations and quantitative
results. Unlike the earlier survey, they **must include conference proceedings and arXiv**. That
survey kept only Q1 journals
(`/plans/261011-1345-aiops-q1-literature-gap/work/q1-protocol.md:25`), so it could not confirm
or refute gaps in a field that publishes mainly at ICSE, FSE, ASE, ISSRE, EuroSys, WWW, KDD,
ICLR, NeurIPS and similar venues.

Treat every gap as UNVERIFIED until a search with these settings comes back.

## Blockers for the literature step

1. The corpus must cover conferences and preprints. Otherwise a "0 papers" result is
   uninformative.
2. Terminology varies: RCA, fault localisation, incident diagnosis, failure diagnosis, root-cause
   service, culprit. Run the synonym sets below, not single phrases.
3. Some 2025–2026 work may exist only as preprints. Record its peer-review status in the
   extraction table and never count a preprint as an established result.
4. Benchmarks overlap with the ones this repository uses (RCAEval, Nezha, AIOps challenge data,
   OpenRCA). Record dataset and protocol exactly, so that numbers are never compared across
   protocols. This repository's protocol does not match AgenticOpsEval's
   (`/plans/261015-0047-nt114-rca-llm-jev-research-and-implementation/design/research-design.md:242`).
5. Do not paste any search hit's claims into the reports until the full text is checked.

## Common settings

- Years: 2020–2026. Include older papers only when they are a standard baseline the new papers
  compare against.
- Venue types: journal, conference, workshop, arXiv/preprint. Record which.
- Language: English.

**Inclusion (all questions)**

- Reports a quantitative evaluation on at least one named dataset or system.
- Describes the method well enough to tell which signals, inputs and outputs are used.

**Exclusion (all questions)**

- Position papers, vision papers and surveys. Keep surveys only to snowball references.
- Purely qualitative case studies with no metric.
- Papers on hardware or network fault diagnosis with no service or component-level RCA (unless
  RQ2 or RQ3 needs them for method transfer; tag them `transfer`).
- Duplicates (keep the most complete version and note the others).

## Research questions

### RQ1 (H1, H3): How accurate and how well-calibrated are LLM-based RCA methods when telemetry modalities are missing or incomplete?

- **Keywords**
  - ("large language model" OR LLM OR "language model" OR agent) AND ("root cause analysis" OR
    "root cause localization" OR "fault localization" OR "incident diagnosis" OR "failure
    diagnosis")
  - AND (microservice OR "cloud system" OR AIOps OR observability)
  - AND ("missing modality" OR "missing telemetry" OR "incomplete observability" OR "missing
    traces" OR "partial observability" OR "modality ablation" OR "metrics only")
- **Include** papers that ablate or naturally lack metrics, logs or traces, **or** that report any
  confidence, calibration or abstention result for LLM-RCA.
- **Exclude** non-LLM RCA papers, except multimodal non-LLM papers that report modality ablations
  (tag them `non-LLM-baseline`).
- **Extract** the modality ablations performed, the accuracy change per modality, and whether
  confidence was measured under each condition.

### RQ2 (H1): Which confidence-estimation and selective-prediction methods have been compared empirically for LLM outputs over a closed answer set, and which have been used in AIOps or incident management?

- **Keywords**
  - (LLM OR "large language model") AND ("confidence estimation" OR "uncertainty
    quantification" OR calibration OR "verbalized confidence" OR "self-consistency" OR
    "semantic entropy" OR "token probability")
  - AND ("selective prediction" OR abstention OR "risk-coverage" OR "conformal prediction" OR
    deferral OR "learning to defer")
  - Second pass: add AND (AIOps OR incident OR "root cause" OR "log analysis" OR "IT operations")
- **Include** papers with a head-to-head comparison of at least two confidence estimators, using
  AUROC, ECE, Brier, AURC or selective risk.
- **Exclude** papers that only propose an estimator without a comparison, and papers on
  open-ended generation that offer no mapping to a closed answer set.
- **Extract** the estimators compared, the answer-space type, and the metrics. Record any finding
  on vote share vs token probability vs verbal confidence.

### RQ3 (H2): Has budget- or cost-aware adaptive acquisition of evidence (telemetry queries, tool calls, features) been studied for RCA or incident diagnosis, and how were cost and budget-matched baselines defined?

- **Keywords**
  - ("root cause analysis" OR "incident diagnosis" OR "fault localization" OR troubleshooting)
    AND ("active feature acquisition" OR "cost-sensitive" OR "budget" OR "adaptive data
    collection" OR "sequential decision" OR "tool calls" OR "query cost" OR "observability cost"
    OR "sampling of traces")
  - Second pass, without the RCA term: "active feature acquisition" AND (benchmark OR
    "budget-accuracy")
- **Include** papers that define an acquisition or query cost and report accuracy against cost,
  or a budget-matched comparison.
- **Exclude** papers on trace or log sampling for storage reduction that do not evaluate the
  downstream diagnosis.
- **Extract** the cost definition (tokens, queries, latency, money, data volume), whether
  evaluation was live or offline replay, the baselines, and the budget-curve metrics.

### RQ4 (H3): Do LLM-based or hybrid RCA pipelines separate candidate generation (recall) from candidate ranking (precision), and what share of errors comes from each stage?

- **Keywords**
  - (LLM OR "large language model" OR agent) AND ("root cause" OR "fault localization")
  - AND ("candidate generation" OR "candidate set" OR shortlist OR "two-stage" OR "retrieve then
    rank" OR "re-ranking" OR "recall@k" OR "error analysis" OR "failure analysis of the agent")
  - Also: "answer not in options" OR "none of the above" OR "unanswerable" AND (LLM OR "multiple
    choice")
- **Include** papers that report stage-wise metrics (candidate recall@K and final top-1), an
  error taxonomy with counts, or LLM behaviour when the true answer is outside the provided
  options.
- **Exclude** papers that report only end-to-end accuracy.
- **Extract** the stage definitions, recall@K of the generator, conditional accuracy of the
  ranker, the error-taxonomy counts, and the abstention behaviour when the answer is out of set.
- **Seed paper (added 2026-10-18).** "Where Root Cause Analysis Fails: A Retrieval-Reranking Decomposition" (NeurIPS 2026 poster,
  https://neurips.cc/virtual/2026/poster/139698).
  - The owner verified the full text. It covers RCAEval RE1 (OB, SS, TT; 125 incidents each),
    WADI, SWaT and HVAC, and not Nezha, RCA100 or AIOps2025.
  - Use it for backward and forward citation search.
  - Score it `relevance_H3 = 2`.
  - Record its BARO and LLM numbers as external reference values only; see
    [02, H3](02_research_directions.md).

### RQ5 (all): Which benchmarks and evaluation protocols exist for LLM-RCA, and how do they handle repeated injections, label-derived anchor times, train/test overlap and pre-training contamination?

- **Keywords**
  - ("root cause analysis" OR "fault localization") AND (benchmark OR dataset OR "evaluation
    protocol")
  - AND (microservice OR "Online Boutique" OR "Train Ticket" OR "Sock Shop" OR RCAEval OR OpenRCA
    OR Nezha OR "AIOps challenge")
  - AND (LLM OR leakage OR contamination OR "data split" OR reproducibility)
- **Include** benchmark papers, and method papers that state their split or protocol explicitly.
- **Exclude** dataset announcements with no evaluation protocol.
- **Extract** the dataset, number of injections, modalities, split method, whether the anchor or
  alert time is given to the method, any reported leakage or contamination control, and the
  published baselines with their numbers.

## Evidence-extraction table schema

One row per paper × dataset × method arm. Keep `quote` fields verbatim with a page or section
reference, so every number can be traced.

| Column | Type | Definition |
|---|---|---|
| `paper_id` | string | DOI, or arXiv id with version |
| `title`, `year`, `venue`, `venue_type` | string / int / string / enum{journal, conference, workshop, preprint} | Bibliographic record |
| `peer_reviewed` | bool | False for preprints |
| `rq` | list{RQ1..RQ5} | Which questions the row informs |
| `system_under_test` | string | e.g. Online Boutique, Train Ticket, production cloud |
| `dataset` | string | Name and version; `private` if not released |
| `n_incidents`, `n_injections` | int | As reported; record `UNKNOWN` when not given |
| `modalities_available` | set{metrics, logs, traces, events, alerts, topology} | Inputs the method can use |
| `missingness_manipulation` | enum{none, drop-modality, partial-service, natural} + text | How missing telemetry is created |
| `method_family` | enum{statistical, graph/causal, ML, LLM single-shot, LLM agent, hybrid} | |
| `llm_model`, `llm_size`, `open_weights` | string / string / bool | |
| `candidate_generation` | text | How candidates are produced (all services, statistical filter, retrieval, agent search) |
| `ranking_method` | text | |
| `confidence_estimator` | set{none, verbal, self-consistency, token-prob, entropy, learned verifier, other} | |
| `abstention_or_deferral` | text | Rule and target (for example, threshold on X) |
| `acquisition_policy`, `cost_definition` | text / text | For RQ3: what is acquired and how cost is measured |
| `evaluation_mode` | enum{offline replay, live environment, both} | |
| `split_protocol` | text | Random, grouped, held-out system, held-out fault, temporal |
| `leakage_controls` | text | Anchor time given? Repeated-injection handling? Contamination check? |
| `baselines` | list | Names of comparators reported |
| `metric_name`, `metric_value`, `ci_or_sd` | string / float / string | One row per headline number; `AC@1`, `AC@3`, `Avg@5`, `AUROC`, `ECE`, `Brier`, `AURC`, `selective_risk@cov`, `cost` |
| `ablation_results` | text | Per-modality or per-stage deltas |
| `stage_wise_errors` | text | Generator recall@K, conditional ranker accuracy, error-taxonomy counts |
| `code_available`, `data_available` | bool + URL | |
| `relevance_H1`, `relevance_H2`, `relevance_H3` | enum{0, 1, 2} | 0 = none, 1 = related, 2 = directly overlaps the hypothesis |
| `overlap_note` | text | What exactly the paper already covers of H1, H2 or H3 |
| `quote` | text | Verbatim support for the key claims, with page or section |
| `extractor`, `extracted_on`, `verified_full_text` | string / date / bool | |

## Screening and decision rule for tomorrow

1. Screen titles and abstracts per RQ with the inclusion and exclusion rules above. Record the
   counts (identified, screened, included).
2. Read the full text of every paper scored `relevance_Hx = 2`, and fill `overlap_note` and
   `quote`.
3. For each hypothesis, an "overlap exists" verdict needs at least one peer-reviewed paper with
   `relevance = 2` and a quantitative result on a comparable setting. Otherwise the gap stays
   UNVERIFIED (absence in one search is not proof of novelty).
4. Copy the baselines and metrics found for each hypothesis into
   [02](02_research_directions.md) before any implementation choice.

## Unresolved questions

- Should Elicit results be restricted to papers with released code or data? This trades recall
  for reproducibility.
- Is a venue target (D5, still open) needed to set the bar for which prior work counts as
  overlap?
