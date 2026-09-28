#!/usr/bin/env bash
# Dead-pressure 54100 Pa fork (web-mbd qs-ish-dead-pressure family).
# Same LAW42 μ/ρ as qs-ish-pload-400ms. 1 ms step then hold. Not a μ retune.
set -euo pipefail
DECK_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DECK_DIR/../../../.." && pwd)"
RADIOSS_ROOT="$(cd "$DECK_DIR/../../.." && pwd)"
# shellcheck disable=SC1091
source "$RADIOSS_ROOT/env.sh"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

RUN="${RUN_DIR:-$DECK_DIR/run}"
mkdir -p "$RUN"
cp -f "$DECK_DIR"/Ainflate_0000.rad "$DECK_DIR"/Ainflate_0001.rad "$RUN"/
cd "$RUN"
rm -f AinflateA[0-9]* Ainflate_A*.vtk AinflateT01

echo "=== dead-pressure starter  nt=$OMP_NUM_THREADS ==="
starter_linux64_gf -i Ainflate_0000.rad -np 1 | tee starter.log
echo "=== dead-pressure engine ==="
TIMEOUT_S="${ENGINE_TIMEOUT:-180}"
set +e
set +o pipefail
timeout --signal=TERM "$TIMEOUT_S" engine_linux64_gf -i Ainflate_0001.rad | tee engine.log
eng_ec=${PIPESTATUS[0]}
set -euo pipefail
if [[ "$eng_ec" -eq 124 ]]; then
  echo "engine timeout (ANIM kept if written)" | tee -a engine.log
elif [[ "$eng_ec" -ne 0 ]]; then
  echo "engine exit $eng_ec (post will use any ANIM written)" | tee -a engine.log
fi
echo "=== post ==="
python3 "$ROOT/tools/radioss_post.py" --run-dir "$RUN" --deck-dir "$DECK_DIR" \
  --label "# A-inflate QS-ish dead-pressure 54100 Pa — RUN"
if [[ -f "$DECK_DIR/artifacts/inflate-a-radioss-qs-golden.json" ]]; then
  cp -f "$DECK_DIR/artifacts/inflate-a-radioss-qs-golden.json" \
    "$DECK_DIR/inflate-a-radioss-qs-golden.json"
fi
echo "done. artifacts in $DECK_DIR/artifacts"
