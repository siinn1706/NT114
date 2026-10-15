# Decision log

Append-only: date, decision, evidence, owner. Every later deviation from the plan or the
preregistration is added here.

| Date | Decision | Evidence | Owner |
|---|---|---|---|
| 2026-10-15 | Implementation started with `/ak:cook --auto` on this plan; phase 02 (M1) implemented on the Windows prep machine, CPU only, mock LLM and mock Jev | Fast suite 232 passed (191 before); realdata suite 39 passed; synthetic and real-bundle smoke chains ran with mock backends | R1 |
| 2026-10-15 | `.gitignore` (nt114-rca) gains `.env`, `.env.*`, `results*/`, `paper/artifact/` and `data_synth_home/` (the synthetic home that `configs/canonical_synthetic.yaml` and `configs/exp/smoke-offline.yaml` generate was not ignored) | `git check-ignore -v` on each path | R1 |
| 2026-10-15 | **Scoring rule:** a miss has rank `n_candidates + 1`, not `len(ranking) + 1`. With the old rule a one-item wrong ranking had rank 2 and counted as correct@3. An empty ranking (all samples unparsable) is a miss with `parse_failed = true`. Mean rank changes accordingly | `tests/test_score.py::test_empty_ranking_is_wrong` | R1 |
| 2026-10-15 | **`blind_nonroot_ev` target:** the non-root service listed in the Traces block of the `full` evidence whose evidence-line count (all blocks) is closest to the root's; ties by `sha256(uid + service)`. If none exists the condition is skipped for that incident and recorded in the evidence file's `skipped` list. The target is written only to `ablation_log.jsonl` | `run_grid.nonroot_ev_target`; `tests/test_run_grid_canonical.py::test_blind_nonroot_ev` | R1 |
| 2026-10-15 | **Embedder pinning:** `embedder: tfidf` is now an explicit choice. A configured dense embedder that falls back to TF-IDF stops the run, and the embedder kind is part of `store_fp`. The synthetic configs use `tfidf` | `tests/test_run_grid_canonical.py::test_embedder_kind_pinned` | R1 |
| 2026-10-15 | **Decision grids exclude the oracle store:** `rca.decide` refuses a grid containing `oracle_store` rows, so `no_precedent` (O3) runs go to a separate grid file | `tests/test_decide.py::test_rejects_oracle_rows` | R1 |
| 2026-10-15 | **Jev `supported` noul** is sent with a `criteria` map {true, false}, as in research/jev-api-verification §2. Confirm in the M0 smoke call that this field is accepted; drop it if TypeSafe rejects criteria on `noul` | `jev.build_questions` | R1 |
| 2026-10-15 | **Permutation-invariance test** covers `full`, `no_metric`, `no_log` and `no_trace`. `blind_root` is label-dependent by design (it masks the true root), so it is excluded there; the canary test covers it | `tests/test_leakage.py` | R1 |
| 2026-10-15 | **M1 approved by the owner.** Phase 02 stays done; later work continues the cook workflow without reopening it | Owner message 2026-10-15 | Owner |
| 2026-10-15 | **D1:** Jev via TypeSafe direct, pinned `jev-1.13.0`; Jev remains the mandatory post-LLM decision layer | Owner | Owner |
| 2026-10-15 | **D2:** planned GPU is an NVIDIA RTX 4080 Laptop with 12 GB VRAM (owner-reported). Primary 3–4B; 7–9B only at 4 bit and only if measured feasible; QLoRA/LoRA, no full fine-tuning; 14B–27B not assumed; escalation chosen by measurement; external inference only with separate approval. Model set and VRAM estimates: research/model-selection §3. GPU, driver, CUDA, PyTorch and free VRAM still to be probed (`scripts/gpu_probe.py`) | Owner; `python -m rca.capacity configs/hardware/rtx4080-laptop-12gb.yaml` | Owner / R1 |
| 2026-10-15 | **D3:** AIOps2025 and RCA100 evidence is not sent to TypeSafe until their licence and data-processing terms are verified. `rca.decide` withholds evidence for these datasets in every variant (J-noevidence form), records `evidence_withheld`, and includes the withheld set in the Jev fingerprint. `jev.evidence_cleared: [...]` lifts it per dataset once the terms are recorded here | `tests/test_decide.py::test_withheld_evidence_never_sent` | Owner |
| 2026-10-15 | **D4:** Kubernetes live demo out of scope | Owner | Owner |
| 2026-10-15 | **D5:** submission target 2027-01-08 (provisional); venue TBD | Owner | Owner |
| 2026-10-15 | **D6:** service-alias sign-off requires verified raw-data / topology evidence and collision tests before final sign-off (before M3) | Owner | Owner / R1 |
| 2026-10-15 | **D7:** RCA100 primary evaluation on tier A (86 tasks / 70 injections); all 103 tasks / 86 injections reported as secondary analysis | Owner | Owner |
| 2026-10-15 | **D8:** RCAEval primary split is the cell-held-out `within-rcaeval-grouped-0-e9b2c81c`; `within-rcaeval-retrieval` is the secondary recurring-fault evaluation (E2b) | Owner | Owner |
| 2026-10-15 | **M0 stays blocked** until the Linux portability gate, the GPU probe on the training machine and TypeSafe access pass. No GPU experiment and no live Jev call before then | Owner | R1 |
| 2026-10-15 | **Mock Jev is refused on real grids:** `rca.decide` stops when the Jev backend is mock and any grid row comes from a real LLM, unless `jev.smoke: true` (never reported; the analysis headline guard also refuses mock Jev rows) | `tests/test_decide.py::test_mock_jev_refused_on_real_grid` | R1 |
| 2026-10-15 | **Live LLM backends need a pinned `revision`**; `LLM(...)` raises otherwise | `tests/test_pipeline.py::test_live_backend_needs_revision` | R1 |
| 2026-10-15 | **Model probe (HF API, read-only):** repo, revision sha, licence and architecture of Qwen3.5-4B (`851bf6e`, Apache-2.0, 4.66B incl. vision, 8 of 32 layers full attention), Qwen3-4B-Instruct-2507 (`cdbee75`, Apache-2.0), Phi-4-mini-instruct (`cfbefac`, MIT), Gemma 4 E4B-it (`ee0ef60`, Apache-2.0, 8.0B stored), Qwen3.5-9B (`c202236`, Apache-2.0), Qwen3-8B (`b968826`) and Qwen3-8B-AWQ (`4da05a8`), recorded in `configs/hardware/rtx4080-laptop-12gb.yaml`. No official FP8 or 4-bit Qwen3.5 small checkpoint was found | `huggingface.co/api/models/<repo>` and `config.json` at those revisions | R1 |
| 2026-10-15 | **Non-LLM baselines B0, B1, B3 implemented on CPU** (`src/rca/baselines.py`, ahead of phase 04). B3 alert-entity reads the entity from `context.visible_text` (the task's alert entity, `<service>[::<op>]`). RCA100 tier A (D7 primary, 86 tasks / 70 injections): majority 41/70 = 0.586 and alert-entity 0.374 injection-weighted (0.651 / 0.372 per task), equal to the data protocol. All 103 tasks / 86 injections (D7 secondary): 0.477 / 0.304 (0.544 / 0.311 per task). The majority class is computed from the scored set's labels and is a label-prior reference only. B2 BARO remains (separate venv) | `tests/test_baselines.py::test_rca100_tier_a_protocol_numbers` (realdata) | R1 |
| 2026-10-15 | **Injection weights are renormalised per evaluated cell** (`analyze.reweight`): weight = 1 / records of that injection in the cell, so an injection always counts once even when a cell holds only part of it. The tier-A RCA100 numbers do not change (no tier-A injection has a tier-B sibling) | `tests/test_baselines.py::test_reweight_equal_per_injection_within_cell` | R1 |
| 2026-10-15 | **`configs/exp/dev-pilot.yaml`** prepared for the 12 GB primary (Qwen3.5-4B FP8, `within-rcaeval-grouped` val = 143 DEV incidents, live Jev). Not run: it needs the GPU machine and TypeSafe access | config resolves on the real build | R1 |

## Pending owner inputs (phase 01)

| Item | Status |
|---|---|
| Linux GPU gate from the `cd96e9e` worktree | **blocking** (needs the GPU machine) |
| GPU probe: model, VRAM, driver, CUDA, PyTorch, free VRAM, disk | **blocking** (`scripts/gpu_probe.py` on the machine; D2 hardware reported) |
| Model-card probe: chat template, thinking toggle, minimum vLLM version | open (repos, revisions, licences recorded) |
| TypeSafe key in `TYPESAFE_API_KEY`, exact response `model` string, org rate limit | **blocking** (hard exit of M0; deadline 2026-10-30) |
| D3 licence and data-processing terms for AIOps2025 / RCA100 | open (evidence withheld until then) |
| D6 alias evidence and collision tests | open (before M3) |
| Venue (D5) | open |
| Researcher availability per week, weeks 1–12 | open |
