---
title: "Release nt114-data-v1: GitHub code commit, private HF bundle"
date: 2026-10-14
summary: "Bundle 6fdd9835 tied to commit cd96e9e, verified on Windows and on HF; Linux gate pending"
---

# Release nt114-data-v1: GitHub code commit, private HF bundle

## What happened
Release nt114-data-v1 prepared. Code commit cd96e9e (clean) on branch release/nt114-data-v1. Bundle nt114-data-v1-20261014-6fdd9835 (MANIFEST.sha256 1a51a7c5..., 10.67 GB) verified on Windows in place, on a robocopy copy (deep verify, status, 16 splits, sha256sum -c) and after upload to the private HF dataset siinn1706/nt114-rca-data (commit c5c4a6dc; 3,265/3,265 files match, 3,098 by LFS sha256).

## Decision
Owner chose: full bundle including eval_only labels on a private HF repo; label-free split/manifests kept in git too; push branch; Docker preflight skipped. The 4 RCAEval exclusions are lifted after tests/test_realdata_identity.py passed. releases/nt114-data-v1.json ties code commit, bundle checksums and HF commit.

## Next steps
Run scripts/verify_portability.sh on the Linux GPU machine (mandatory gate), then close phase 12 and M1/M2. Owner final review of the six service aliases. Phase 08/M3 deferred.

> Historical work record — not durable authority. Prefer docs/specs/ADRs for current decisions.
