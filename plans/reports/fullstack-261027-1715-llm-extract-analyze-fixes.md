# LLM parsing, safe extraction and headline guard fixes

Date: 2026-10-27 (Asia/Saigon). Package: `nt114-rca/nt114-rca`. Nothing was committed.

## Changes

### `src/rca/llm.py` (CRLF kept)
- `parse()`: when a service appears more than once in the ranking, only its first position is kept (`dict.fromkeys`).
- `parse()`: confidence must be a real number in 0-100. A bool, string such as `"85%"`, list, null/missing value, or out-of-range value marks the sample `ok=False` with `confidence=0.0`. That is the way the module already records parse failures, so `aggregate()` drops the sample and `parse_rate` falls. It no longer raises.
- `aggregate()`: Borda dedupes each sample's ranking too, because samples cached before this change still hold the raw ranking.
- **Schema not changed (no `uniqueItems`).** The module states that `PROMPT_VERSION` must be bumped on any change to `schema()`. `schema()` is sent as the vLLM `response_format`, so any change also changes the guided-decoding constraint. A bump would change every cache key and result key, and keeping `v1` with a different schema would leave the cache stale. The brief's fallback rule covers this case, so only the parsing dedupe was applied.

### `src/rca/safe_extract.py` (CRLF kept)
- The receipt now records `archive_sha256`. A receipt is reused only when its `archive_sha256` equals the current archive's sha256. When the field is missing (an old receipt) or differs (different archive bytes), a fresh receipt is started and every member is extracted again.
- `done()` now checks that the receipt has a `sha256`, that the file size matches, and that the file's sha256 on disk equals the receipt's. On a mismatch the member is extracted again, the same repair as before.
- A member whose path, case-folded, is `.extract.json` or `.extract.json.part` (the atomic-write temporary) raises `UnsafeArchive`.
- Two file members whose paths are equal case-insensitively raise `UnsafeArchive` ("name collision"). Exact duplicate names are included.
- At the start of a run, `complete` is cleared from the loaded receipt and set again only at the end.
- Module docstring updated.

### `src/rca/analyze.py` (LF kept)
- `guard_headline()` now refuses rows with `split_role == "train"`, as it already did for `val`. Module docstring and function docstring updated. Exploratory runs (no `preregistration_sha`) are unchanged.

### Tests added
- `tests/test_llm_raw.py`: `test_repeated_ranking_entries_count_once` covers `["a","a","a"]`, mixed repeats, and cached duplicate samples in `aggregate`. `test_malformed_confidence_is_a_parse_failure` covers `"85%"`, `[1]`, `150`, `-1`, `True` and `None`.
- `tests/test_safe_extract.py`: `test_receipt_records_archive_and_member_sha256`, `test_rerun_repairs_member_damaged_without_size_change`, `test_receipt_without_sha_fields_is_not_trusted`, `test_receipt_of_another_archive_is_not_trusted`, `test_member_named_like_the_receipt_rejected` (3 names) and `test_case_insensitive_name_collision_rejected` (tar and zip).
- `tests/test_analyze.py`: `test_headline_guard_refuses_train_rows`, through both `run()` and `guard_headline()`.

## Red to green
Before the fix: 16 failed. Reasons:
- `['a','a','a'] == ['a']` failed.
- `ValueError: could not convert string to float: '85%'`.
- `TypeError ... not 'list'` and `TypeError ... not 'NoneType'`.
- `150`, `-1` and `True` were accepted as ok.
- `KeyError: 'archive_sha256'`.
- `b'alphX' == b'alpha'` failed twice (same-size damage and old receipt).
- `b'alpha' == b'omega'` failed (receipt of another archive was trusted).
- `DID NOT RAISE UnsafeArchive` x4.
- `DID NOT RAISE HeadlineGuardError`.

After the fix: `16 passed, 43 deselected`.

## Test runs
```
PYTHONPATH=src <python> -m pytest -q -p no:cacheprovider -m "not realdata" tests/test_llm_raw.py tests/test_safe_extract.py tests/test_analyze.py
59 passed in 34.51s

PYTHONPATH=src <python> -m pytest -q -p no:cacheprovider -m "not realdata" tests/test_pipeline.py tests/test_confidence.py \
  tests/test_baselines.py tests/test_feasibility.py tests/test_im1_leakage.py tests/test_leakage.py tests/test_ra_pipeline.py \
  tests/test_reproduce.py tests/test_run_grid_canonical.py tests/test_run_grid_train_split.py tests/test_visibility.py \
  tests/test_selective.py tests/test_prep_driver.py tests/test_adapter_aiops2025.py tests/test_contrasts.py
152 passed, 1 deselected, 1 warning in 424.04s
```

## Concerns
- `uniqueItems` was not added to the schema, for the `PROMPT_VERSION` reason above. Adding it later needs a deliberate `PROMPT_VERSION` bump. It also needs a check that the structured-output backend of vLLM 0.30 accepts `uniqueItems`, since some guided-decoding backends reject or fall back on it.
- `confidence.borda_margin` (in `confidence.py`, outside the allowed files) still counts duplicates in cached samples written before this fix. New samples are deduped at parse time.
- `parse()` still raises `AttributeError` when a completion is valid JSON that is not an object, for example `[1,2]`. This is outside the brief. With guided decoding it is unlikely.
- Resume now hashes the whole archive and every extracted member on each rerun. That is extra I/O on large datasets.
- An existing extraction with an old receipt (no `archive_sha256`) is fully re-extracted on its next `prep extract`.
