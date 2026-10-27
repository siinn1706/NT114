# Publish current research snapshot

Outcome: commit and push all current publishable changes to the existing private GitHub repository, publish the new minimal RCLAgent package/results to the existing private Hugging Face dataset, and add a clear README with cited paper lineage, manifest-derived data counts, flow and charts.

Scope: latest source, tests, research plans/reviews, notebook, compatibility repair and documentation. Preserve paused R-a/IM1 work with its actual status. Runtime environments, copyrighted full-text papers, credentials, transcripts, canonical data and telemetry archives stay outside Git. New benchmark input/output archives go only to the authorized private artifact destination. No model run, deployment server, training, benchmark expansion or privacy change.

Acceptance: tests appropriate to all current source changes pass; documentation links and counts match owning artifacts; no secrets or generated runtime payload is staged; GitHub remote commit matches local commit; Hugging Face uploads are downloaded at the returned revision and SHA256-verified; both repositories remain private; publish report records revisions, boundaries and rollback.

Sequence: inspect source/decisions and provider state; prepare README/charts and publication manifest; test and review; publish private artifacts; commit/push reviewed source and documentation; verify remote revisions and record outcome.

Prepared and verified: full non-realdata suite 418 passed / 56 deselected; Python syntax and literal-credential scan passed; README links and chart source hashes matched. Current RCA code/test snapshot committed as b32eda8. GitHub destination siinn1706/NT114 is private and main is unprotected; ordinary push is the permitted route.

Hugging Face publication completed at 2e7d80c144d5f28d13e8ed1888c7bc83b8c7fdc1: 29 files uploaded and downloaded with SHA256 equality, 3.265 existing canonical tree entries unchanged, private visibility rechecked. See hf-publish-receipt.json. Remaining delivery action: commit documentation/reproduction snapshot and ordinary push; exact remote-head evidence is recorded by the push step. Kaggle remains stopped at E; publication does not upgrade it to success.

Resume checkpoint, 2026-10-27 Asia/Saigon: the prior second-commit command was not executed because the automatic approval reviewer hit its usage limit. It has now succeeded as 514c2fc. HF HEAD/privacy and the data-card hash were rechecked without uploading again; README links/chart provenance and the remaining credential/syntax scan passed. The documentation commit closes source preparation, followed by the skill-required Git-manager push and independent remote-head check. Generated Matplotlib SVG bytes remain equal to the published files; a path-specific Git attribute allows their intentional path-data line-end spaces. Raw generated review logs remain local.
