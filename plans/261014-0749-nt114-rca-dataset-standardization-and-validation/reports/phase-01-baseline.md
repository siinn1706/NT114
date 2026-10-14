# Phase 01 report: baseline audit, environment lock, golden set (2026-10-14)

## Environment

- Python 3.12.10 (Windows 11, `py -3.12`), venv at `RCA_ROOT/.venv` (git-ignored).
- `requirements.txt` gained `jsonschema>=4.21`; `requirements-lock.txt` is the `pip freeze` of the venv.
- Key versions: pandas 3.0.6, pyarrow 26.0.0, numpy 2.5.4, jsonschema 4.26.0, pytest 9.1.1,
  PyYAML 6.0.3, scikit-learn 1.9.1, sentence-transformers 6.1.0, torch 2.14.1.
  pandas 3 is a major version above the one the code was written against; the existing suites pass with it.

## Existing suites (T01)

| Command | Result |
|---|---|
| `PYTHONPATH=src .venv/Scripts/python -m pytest -q tests/test_pipeline.py` | 6 passed |
| `.venv/Scripts/python -I tests/test_datasets_acquire.py` | 16 tests OK |

## Raw integrity

- `sha256sum -c --quiet data/manifests/checksums.sha256`: exit 0 over 31,495 files (6 min 38 s).
- `acquire.py status`: 10 sources VERIFIED (publisher-hash); OpenRCA, GAIA, Eadro, LEMMA, LO2,
  AIOps 2020/2021 archives PENDING, as in the acquisition plan.

## Baseline hashes (sha256 before any change)

```text
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 *src/rca/__init__.py
03c4d262c712149e807efbf55877eebe39393602bc7314e84b32abc371618f39 *src/rca/ablate.py
bfd1713d5229337511cd4ae334fee0a9109d177f5c17642330b5a73730db4e8e *src/rca/analyze.py
d5f4dec755797227835f5776968bbd223eb7edc07cfcee40fc914857efbd92da *src/rca/data.py
1239c45c3b75e46e9330bb525a677ebfc2b4b380a4ce2db35275f6afa10ecd4d *src/rca/evidence.py
32cc9ae5c49a6b6f8e7469d7dc6afb369f7920b51b9613070a6c9127b83a9a69 *src/rca/gate.py
074781fd5b2eacde953b574108a2d8bdd433b30a09b925bc2c2ca0cfadedb710 *src/rca/llm.py
c2ba8cbe5e504bbad988bd1f583315a1e6670799717a25e142ed3fcb79e0ce0e *src/rca/metrics.py
5aeb9720286c33f8f36bc5c1135eccc3e218a7f24b21c46cefd95fa342026281 *src/rca/retrieve.py
7119bfeb0be5203c462eb1a8787385974bf14d0f2380f77c1ec24886081ea324 *src/rca/run_grid.py
f587c4e61a83f752f397ea762ee6ff1a5a217ac7dcb01f07a4daacd3a1423cb7 *configs/pilot.yaml
4fa923b375516373c664307ecb50f592ae93769bfa73c2d318dbf5bc167b281c *configs/synthetic.yaml
ad012ae0e76f861ffcf9774f54d1fe09c4323967e649b98b24b30eb1cfefb930 *tests/test_pipeline.py
```

## Golden set (T02)

`make_synthetic.py` + `run_grid prepare configs/synthetic.yaml` ran twice into separate temp
directories. Both runs produced 72 evidence files with identical canonical dumps of
`{candidates, conditions}`, so no source of non-determinism was found. The hashes are stored in
`tests/golden/synthetic_evidence.sha256` (one line per case).

## Documentation fix (D11)

`docs/dataset_quality_audit.md` now states that the 8 RE3-SS `root_cause.txt` files are in the
Zenodo `RE3-SS.zip` (members `RE3-SS/{carts_f1,carts_f3,front-end_f1,front-end_f2}/{1,2}/root_cause.txt`)
as well as in HF, and that they are label artefacts.

## Other files

- `pytest.ini` (`testpaths = tests`, `pythonpath = src`, marker `realdata`).
- `.gitattributes` (LF for JSON, JSONL, sha256, YAML, shell).
- `.gitignore`: `!data/reports/` and `!data/splits/` added (phases 02 and 04 in the plan; done here once).

## Defects and the phase that fixes them

| Defect | Phase |
|---|---|
| D1 parser and colliding `case_id` | 05 |
| D2 non-UTF-8 `open()` | 03 (store), 05 (`data.py`), 11 (`run_grid.py`) |
| D3 labels in evidence files | 11 |
| D4 store not split-aware | 10, 11 |
| D5 no `blind_root` control | 10 |
| D6 empty vs absent merged | 03 (ModalityInfo status) |
| D7 lossy identity without checks | 03, 05 |
| D8 `metrics.csv` never read | 05 (`metric_set` full/simple) |
| D9 fixed windows on streams | 06, 09 |
| D10 unpinned environment | 01 (this phase) |
| D11 wrong provenance claim | 01 (this phase) |
| D12 absolute paths in evidence | 11 |
| D13 label-bearing `Case` in model-facing code | 05, 11 |
| D14 label-conditioned `no_precedent` feeds Jev | 10, 11 |
