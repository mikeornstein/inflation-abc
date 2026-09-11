#!/usr/bin/env bash
# Run OpenRadioss A-inflate first light (starter + engine) then post.
set -euo pipefail
DECK_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DECK_DIR/../.." && pwd)"
RADIOSS_ROOT="$(cd "$DECK_DIR/.." && pwd)"
if [[ ! -f "$RADIOSS_ROOT/env.sh" ]]; then
  bash "$RADIOSS_ROOT/install_openradioss.sh"
fi
# shellcheck disable=SC1091
source "$RADIOSS_ROOT/env.sh"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

RUN="${RUN_DIR:-$DECK_DIR/run}"
mkdir -p "$RUN"
cp -f "$DECK_DIR"/Ainflate_0000.rad "$DECK_DIR"/Ainflate_0001.rad "$RUN"/
cd "$RUN"

echo "=== starter  nt=$OMP_NUM_THREADS ==="
starter_linux64_gf -i Ainflate_0000.rad -np 1 | tee starter.log
echo "=== engine ==="
# Wall-clock cap: CFL collapse ~28 ms used to spin at dt~1e-15 for hours.
set +e
set +o pipefail
timeout --signal=TERM 90 engine_linux64_gf -i Ainflate_0001.rad | tee engine.log
eng_ec=${PIPESTATUS[0]}
set -euo pipefail
if [[ "$eng_ec" -eq 124 ]]; then
  echo "engine timeout (ANIM kept if written)" | tee -a engine.log
elif [[ "$eng_ec" -ne 0 ]]; then
  echo "engine exit $eng_ec (post will use any ANIM written)" | tee -a engine.log
fi
echo "=== post ==="
python3 "$ROOT/tools/radioss_post.py" --run-dir "$RUN" --deck-dir "$DECK_DIR"
echo "done. artifacts in $DECK_DIR/artifacts"
