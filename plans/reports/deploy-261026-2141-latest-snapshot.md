# Latest NT114 snapshot: source and private artifacts

User scope: publish all current source/documentation changes, including the paused R-a/IM1 implementation, and improve the project README with paper lineage, data counts, flow and charts. This authorizes commit/push; it does not resume model runs or turn the Kaggle trace into an end-to-end success.

## Prepared source and documentation

- Current RCA changes are committed as `b32eda8` (`feat(rca): add deterministic RCL adaptation and IM1 controls`), 24 files. Full non-realdata suite: 418 passed, 56 deselected, one numerical warning in a synthetic SVD fixture, exit 0. No new LLM inference or realdata evaluation.
- Root README identifies RCLAgent/arXiv v1, author commit, current recursive smoke scope, canonical counts and paused adaptation work. Flow is Mermaid; two charts are actual Matplotlib output from manifests/summaries, with PNG/SVG and input hashes. Native E remains stopped on an out-of-package cartservice query.
- Credential-literal scan and Python AST checks passed. Source staging excludes runtime/venv, PDFs/fulltext, crash dumps, generated test outputs, SQLite caches and benchmark/inference ZIPs. Public scholarly response tables are preserved separately as an HF artifact; original local files are unchanged.

## Hugging Face completed

Repository: [siinn1706/nt114-rca-data](https://huggingface.co/datasets/siinn1706/nt114-rca-data), private before and after. Commit: [2e7d80c144d5f28d13e8ed1888c7bc83b8c7fdc1](https://huggingface.co/datasets/siinn1706/nt114-rca-data/commit/2e7d80c144d5f28d13e8ed1888c7bc83b8c7fdc1).

29 files were uploaded through an explicit allowlist and downloaded at that revision; every size/SHA256 matched. The payload contains the data card, four chart files, one-trace notebook/input package, CPU parity/manifest summaries, native result archives including failures, and an archive of 134 scholarly metadata CSVs. Canonical release content was not uploaded or modified; 3.265 canonical tree entries retain their blob IDs, sizes and LFS hashes.

Machine evidence: [artifact manifest](../261026-2141-publish-latest/artifact-manifest.json), [HF receipt](../261026-2141-publish-latest/hf-publish-receipt.json), [test verification](../261026-2141-publish-latest/test-verification.json), [chart provenance](../261026-2141-publish-latest/chart-provenance.json). Previous HF revision is `c5c4a6dc455cac5d0545b98d8d40266b2bbdaa05`; pinned historical download is the rollback route, not a destructive reset.

## GitHub delivery route

[siinn1706/NT114](https://github.com/siinn1706/NT114) was verified private. Local HEAD matched origin/main before commits, and branch API returned protected=false. The remaining reproduction/documentation snapshot is committed and pushed through the ordinary main-branch route; exact resulting commit and remote-head equality are verified by the push command output. No force-push, history rewrite, PR merge, provider visibility change, app server or model job is part of publication.

Resume checkpoint (2026-10-27): the approval-review usage limit prevented the second commit command from executing on the prior evening; it did not reject the action as unsafe. The reproduction commit was completed as `514c2fc`. HF remains at the verified revision above; no duplicate upload was made. The README/documentation commit carries the rest of the latest publishable snapshot, including prior research plans/reviews, diagrams and charts. Git push verification records the final resulting HEAD after these commits.

## Retained limitations

RCLAgent GPU compatibility and gate D are verified; native E did not finish, so no final RCA or scorer result exists. R-a/IM1 remain paused and have no model result. The fulltext/TDSC version comparison, method accuracy, H1 and IM1 effectiveness remain outside this publication. Upload/download integrity proves artifact publication, not scientific validity.
