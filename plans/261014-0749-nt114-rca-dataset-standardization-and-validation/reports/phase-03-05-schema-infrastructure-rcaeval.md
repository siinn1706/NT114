# Phases 03–05: schema, processing infrastructure and the RCAEval reference build

Date: 2026-10-14. Status: completed and verified on the real data.

## Outcome

The canonical RCAEval build `rcaeval-9bfc8d21733f` holds all 736 case directories with 0 adapter
exceptions and 0 service-identity collisions. 735 incidents are accepted (703 ACCEPT, 32
ACCEPT_WITH_WARNINGS). The one REJECT is `RE2-OB/checkoutservice_cpu/multi-source-data`, a
documented duplicate of `checkoutservice_cpu/1`. `validate` exits 0 with 0 invariant errors, a
rebuild is a no-op with the same `dataset_digest`
(`014ce4af3f276ccb75cbc8b32ca1a536cdce3087918fb4c54331790e39379a36`), and `sha256sum -c` over the
29,410 raw files of the profiled sources exits 0.

## Verification beyond exit codes (re-checked 2026-10-14 from the store files)

| Check | Result |
|---|---|
| Record files agree | `incidents.jsonl`, `labels.jsonl`, `quality.jsonl`: 736 identical uid sets |
| Label validity | 736/736 `valid`, tier A; 0 accepted incidents whose root is not a candidate |
| Telemetry | metrics present in 735/735 accepted (coverage min 0.85, median 1.0); logs present 360, natural_absent 375 (RE1); traces present 240, natural_absent 482, empty 13 (header-only RE3-SS files) |
| No-telemetry incidents | 0 accepted incidents with no present modality |
| Evidence generation | `evidence.build` succeeded for 735/735 accepted incidents (audit `--evidence-stats`). The metric z-score alone ranks the root first in 532/735 (72%); the root is unflagged in 2 |
| Cross-dataset audit | `audit-rcaeval-9bfc8d21733f.json`: 0 unexplained duplicates, 0 lineage gaps (735 matched one-to-one with the registry; the duplicate explained), 0 leakage hits, 0 split errors |
| Real-data parity | `tests/test_realdata_samples.py` 5/5 (HF parity on a seeded sample; known HF differences classified) |

Warnings by cause: non-finite metric values above 5% (21), dropped empty-time metric rows (8),
orphan spans above 20% (2), coverage below 0.5 (1).

## Limitations

- The leakage scan's free-text artefact list for RCAEval has 7 lines (the RE3-SS `root_cause.txt`
  files); RCAEval has no other free-text label source.
- The 72% metric-rank-1 rate means RCAEval is easy for a z-score baseline; LLM results must be
  reported against it.

## Unresolved

- The alias entries in `configs/service_aliases.yaml` are marked "agent 2026-10-14, owner to
  confirm".
