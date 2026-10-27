# Runtime architecture review: scope of the current RCA loop

## Code Review Summary

### Scope

- Reviewed the requested runtime files: `src/rca/run_grid.py`, `evidence.py`, `ablate.py`, `selective.py`, `analyze.py`, `configs/exp/dev-pilot.yaml`, `docs/data_contract.md`, `tests/conftest.py`, and `research/05_evidence_instrument_audit.md`.
- Read supporting contracts and implementation: `README.md`, `src/rca/llm.py`, `src/rca/retrieve.py`, and `research/01_experimental_readiness.md`.
- Review focus: executable entry points, anchor/window dependence, label-informed ablations, offline retrieval/policy evaluation, and whether a real monitor -> detect -> retrieve -> RCA -> propose -> repair -> verify/rollback loop exists.
- No files under `src/`, `configs/`, or `tests/` were changed.

### Overall Assessment

The repository implements a reproducible, batch, evaluation-first RCA experiment. Its stated pipeline is `telemetry -> modality ablation -> evidence summary -> optional old cases -> one LLM -> offline selective evaluation -> metrics` (`README.md:3-20`). It does not implement a 24/24 operational AIOps loop. Retrieval and single-shot root-cause ranking are executable offline; `next_check` is only a text field. Monitoring, anomaly detection, typed remediation, post-change verification, rollback, and safe continuous orchestration are absent.

The `dev-pilot` configuration cannot support a 24/24 claim: it is explicitly `NOT RUN YET`, uses only `rcaeval`, `split_role: val`, one primary vLLM model, eight evidence conditions, and `none/hybrid` retrieval (`configs/exp/dev-pilot.yaml:1-18,28-37`). The audit record also says no model or GPU was used and that the mock chain is plumbing only (`research/05_evidence_instrument_audit.md:1-6,250-260`).

## Stage coverage against the requested loop

| Stage | Current status | Evidence and boundary |
|---|---|---|
| Monitor | **Absent** | `prepare` reads stored canonical telemetry once; `run` iterates finite cached records and writes JSONL (`run_grid.py:290-329,564-678`). No stream, watcher, alert consumer, or monitor entry point exists in the production module set. |
| Detect / onset | **Absent as a detector** | Evidence windows are centred on `case.inject_time` (`evidence.py:25,32-35,218-225`). The anchor comes from evaluation labels or the first firing alert (`data_contract.md:124-127`), so the code does not discover onset, measure detection recall/false positives, or report time-to-detect. |
| Retrieve | **Implemented offline** | Only train-role precedents from the configured split are loaded (`run_grid.py:349-387`); retrieval runs before the LLM call (`run_grid.py:576-640`). This is a static case store, not a live retrieval service. |
| RCA | **Implemented as single-shot ranking** | The prompt asks for a root service and returns `ranking`, `confidence`, `insufficient_evidence`, and `next_check` (`llm.py:26-59`). The grid records the answer and correctness against post-mortem truth (`run_grid.py:641-678`). |
| Propose | **Partial, unstructured** | `next_check` is a bounded string for an engineer to inspect (`llm.py:30-32,47-59`). There is no typed hypothesis, change plan, approval gate, or action contract. |
| Repair | **Absent** | No repair/action tool, deployment client, or mutation path is called by `run_grid` or the LLM layer. Scoped `git grep` found no production `repair`/`remediat` entry point. |
| Verify | **Offline artifact verification only** | `reproduce` reruns analysis tables and compares hashes (`data_contract.md:262-265`); this verifies research artifacts, not service health after a change. |
| Rollback | **Absent** | No rollback state, checkpoint, canary, health threshold, or reverse action is represented in the inspected runtime. |
| Regression checks | **Partial and research-only** | Evidence fingerprints, golden evidence, headline guards, and table reproduction protect data/analysis consistency (`run_grid.py:181-199`, `analyze.py:62-84`, `data_contract.md:139-144,262-265`). They do not test a repair against live regression signals. |
| Safe continuous orchestration | **Absent** | The implementation is resumable batch execution keyed by cached grid cells (`run_grid.py:593-678`), not an event loop with deduplication, approval, timeout, health gates, or rollback. |

## Findings

### High — The experiment has no detection boundary, so it cannot support monitor/detect or time-to-detect claims

`evidence.build` always receives `case.inject_time` and compares `[t-600,t)` with `[t,t+300]` (`evidence.py:25,32-35,218-225`). The data contract explicitly states that this anchor is read from label files, with RCA100 using its first firing alert (`data_contract.md:124-127`). The readiness review already records the consequence: a label-derived window is cleaner than a real detection-time window (`research/01_experimental_readiness.md:112-117`).

This is valid for a benchmarked RCA question, but it is not an implemented detector. The current code cannot measure alert generation, detection delay, false positives, missed incidents, or the evidence available before an alert. A future closed-loop claim must add a detector input and timestamp contract; do not infer it from current RCA accuracy.

### Medium — `blind_root` is a label-informed, evaluation-only ablation

`run_grid.prepare` reads `Truth` before constructing conditions (`run_grid.py:243-261`). `ablate.apply` receives the true root service for `blind_root`, and applicability requires that the true root has spans and that the trace set contains the relevant services (`ablate.py:71-82`). The condition matrix and anchor rules are also documented as label/evaluation driven (`data_contract.md:117-127`). The canonical test asserts that the masked service equals the stored label (`tests/test_run_grid_canonical.py:61-69`).

The label boundary is protected from the model prompt, and the masking is a deliberate counterfactual design rather than a leakage finding. It is still a construct/deployability limit: a live system cannot know which service is the true root in order to create the condition. The readiness review classifies this as a residual construct risk (`research/01_experimental_readiness.md:116-119`). Report it as an evaluation-only diagnostic ablation, never as an online missing-telemetry policy.

### Medium — Train-label precedents are intentional case-based reasoning with a bounded generalization claim

Train precedents are stored with `root` and `fault` (`run_grid.py:374-380`), and `format_hits` prints those resolved-case labels in the prompt (`retrieve.py:124-132`). This is the intended case-based reasoning design; the query's own label is not read by `CaseStore.search`, and the `no_precedent` path is explicitly marked oracle (`data_contract.md:203-215`). The construct boundary is generalization: the grouped split holds out root/fault cells but does not hold out root services, and the audit therefore reports same-root precedents reachable above chance, especially under `blind_root` (`research/05_evidence_instrument_audit.md:221-239`). This is not itself a leakage finding.

Aggregate retrieval gains therefore need to stay within the configured case-based protocol and should not be generalized to root-held-out RCA. The existing mitigation—reporting retrieval cells by whether a top-k precedent carries the query root and stratifying similarity—is appropriate (`research/05_evidence_instrument_audit.md:233-248`; `analyze.py:162-174`). A root-held-out protocol would be needed for a stronger cross-root generalization claim.

### Medium — Evidence ordering gives the LLM a non-LLM ranking hint

Metric services are sorted by descending z-score and only high-z services are emitted (`evidence.py:230-249`). The audit confirms that the evidence-order baseline reaches 148/218 RCAEval test roots at top-1 (`research/05_evidence_instrument_audit.md:107-114`). Candidate order is shuffled, but the evidence text still presents a heuristic ranking. LLM RCA results must stay paired with B1/B1m and should not be described as independent reasoning from raw telemetry.

### Medium — Selective policy results are counterfactual, label-scored offline choices, not an executing policy

`selective.py` defines only `answer`, `retrieve`, and `abstain`; it joins cached cells and explicitly says no policy reaches a prompt (`selective.py:1-13,66-101`). `oracle_policy` reads correctness labels by design (`selective.py:206-212`). `analyze.selective_table` fits DEV thresholds and applies them to test rows, again using cached correctness (`analyze.py:249-303`). The data contract labels this whole section evaluation-only (`data_contract.md:235-243`).

This is useful for estimating a deferral/retrieval policy under full feedback. It does not execute a policy, propose a repair, or establish a safe decision gate for production incidents.

### Medium — Regression/reproducibility checks stop at artifacts and mock plumbing

The available checks protect schema, fingerprints, leakage boundaries, evidence goldens, and reproducible analysis tables (`tests/test_run_grid_canonical.py:38-103`; `data_contract.md:139-144,257-265`). The research audit explicitly calls the mock end-to-end chain a plumbing check and says mock outputs are not results (`research/05_evidence_instrument_audit.md:250-260`). There is no post-remediation regression fixture or live canary that verifies recovery and triggers rollback.

## Verification performed

- Static AST parse of the six core Python modules plus `llm.py`: `AST_OK 6`.
- The initial focused probe used the system interpreter, which has no `pytest` (`No module named pytest`); that does not describe the project environment. The project `.venv\Scripts\python.exe` run subsequently verified 47 passed in 20.93s across `test_confidence`, `test_score`, `test_selective`, and `test_baro`; the earlier temporary-directory setup errors were sandbox failures and the escalated rerun passed.
- A scoped tracked-file search found no production monitor, remediation, rollback, or continuous-orchestration entry point; matches for “detect/repair” were test/data-integrity or documentation terms.

## Recommended actions

1. Keep the current repository labelled as an offline RCA/evaluation pipeline. Do not report 24/24 loop completion.
2. If the user goal is the operational loop, add separate contracts and entry points for alert ingestion/detection, retrieval at alert time, structured RCA/proposal output, explicitly authorized remediation, post-change health verification, and rollback; each needs a dry-run/safety boundary before mutation.
3. Preserve the current label-aware ablations and oracle policy as evaluation-only, and retain root-held-out or equivalent retrieval sensitivity before making generalization claims.
4. Add a runtime regression harness only after the action contract exists; current evidence/table reproduction tests cannot validate repair safety.

### Unresolved questions

- What external system is authorized to receive remediation actions, and what health signal defines verify/rollback? No such contract is present in the repository.

Status: DONE_WITH_CONCERNS
Summary: The executable scope is a batch, label-anchored, single-LLM RCA experiment with offline retrieval and policy analysis. The monitor/detect/remediate/verify/rollback continuous loop is not implemented; the main construct risks are the label-derived anchor, label-informed ablations, and root-bearing retrieval precedents.
Concerns/Blockers: The system interpreter lacks `pytest`, but the project venv focused suite passed; no live model/GPU or operational action target was available or invoked.
