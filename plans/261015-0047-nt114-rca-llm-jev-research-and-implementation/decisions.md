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

## Pending owner inputs (phase 01)

| Item | Status |
|---|---|
| Linux GPU gate from the `cd96e9e` worktree | open (needs the GPU machine) |
| GPU model, VRAM, CUDA, disk → tier S/M/L | open (D2) |
| Model-card probe (licence, template, quantised checkpoint, revision sha) | open |
| TypeSafe key, exact response `model` string, org rate limit | open (hard exit of M0; deadline 2026-10-30) |
| D1–D8 | open (plan.md "Open decisions") |
| Researcher availability per week, weeks 1–12 | open |
