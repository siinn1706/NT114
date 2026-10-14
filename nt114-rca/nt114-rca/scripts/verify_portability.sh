#!/usr/bin/env bash
# Portability check on the target machine (Linux / WSL2), run from the repo root:
#   bash scripts/verify_portability.sh <bundle_dir>
# 0. the checkout contains the bundle's code commit and src/configs/schemas are unchanged since it
# 1. byte check of every bundle file (and `sha256sum -c` as an independent check)
# 2. deep check: recompute every telemetry content_sha256 and blind_nonroot target vs bundle.json
# 3. status and split verification with the bundle's parts as the data home
# 4. fast test suite (no real data needed)
# 5. canonical synthetic run_grid prepare + run with the mock backend
set -euo pipefail
BUNDLE="$(cd "${1:?usage: verify_portability.sh <bundle_dir>}" && pwd)"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
export PYTHONPATH="$ROOT/src"
cd "$ROOT"

echo "== python and pinned packages"
"$PY" -c "import sys, pyarrow, pandas, numpy; print(sys.version.split()[0], 'pyarrow', pyarrow.__version__, 'pandas', pandas.__version__, 'numpy', numpy.__version__)"
grep -E '^(pyarrow|pandas|numpy)==' requirements-lock.txt

echo "== code revision tied to the bundle"
WANT="$("$PY" -c "import json, sys; c = json.load(open(sys.argv[1]))['code']; print(c['git_commit'] if not c.get('git_dirty') else 'DIRTY')" "$BUNDLE/bundle.json")"
[ "$WANT" != "DIRTY" ] || { echo "bundle was exported from uncommitted code"; exit 1; }
git -C "$ROOT" merge-base --is-ancestor "$WANT" HEAD || { echo "checkout does not contain bundle commit $WANT"; exit 1; }
git -C "$ROOT" diff --quiet "$WANT" HEAD -- src configs schemas || { echo "src/configs/schemas changed since $WANT"; exit 1; }
echo "code $(git -C "$ROOT" rev-parse HEAD) contains bundle commit $WANT with identical src/configs/schemas"

echo "== sha256sum -c"
(cd "$BUNDLE" && sha256sum --quiet -c MANIFEST.sha256)

echo "== verify-bundle --deep"
"$PY" -m rca.prep verify-bundle "$BUNDLE" --deep

echo "== status / verify-splits on the bundle"
"$PY" -m rca.prep --data-home "$BUNDLE/parts" status
"$PY" -m rca.prep --data-home "$BUNDLE/parts" verify-splits

echo "== fast test suite"
"$PY" -m pytest -q -m "not realdata"

echo "== canonical synthetic run (mock backend)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
"$PY" scripts/make_synthetic.py "$WORK/data_synth_home/raw/synthetic" --anchor-gap 12000 >/dev/null
for step in "normalize --dataset rcaeval" "conditions --dataset rcaeval" "split --protocol within-rcaeval-retrieval --seed 0"; do
  # shellcheck disable=SC2086
  "$PY" -m rca.prep --config configs/prep_synthetic.yaml --data-home "$WORK/data_synth_home" $step >/dev/null || [ $? -eq 3 ]
done
sed -e "s#^data_home: .*#data_home: $WORK/data_synth_home#" -e "s#results_canon_synth#$WORK/results#g" \
    configs/canonical_synthetic.yaml > "$WORK/cfg.yaml"
"$PY" -m rca.run_grid prepare "$WORK/cfg.yaml" >/dev/null
"$PY" -m rca.run_grid run "$WORK/cfg.yaml" >/dev/null
echo "grid rows: $(wc -l < "$WORK/results/grid.jsonl")"
echo "PORTABILITY OK"
