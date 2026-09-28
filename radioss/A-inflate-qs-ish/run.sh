#!/usr/bin/env bash
# Run OpenRadioss A-inflate QS-ish tape (slower PLOAD / longer T_end / /ADYREL).
# μ and ρ are never retuned. Hang guard /DT/NODA/STOP (not CST). No /AMS unless CFL dies before λ≥2.
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

python3 "$ROOT/tools/mesh_to_radioss.py" --check --qs-ish \
  --out-dir "$DECK_DIR" \
  --note "QS-ish A-inflate; slower PLOAD 0.40 s; μ/ρ locked; not dynamic-pload-40ms"

RUN="${RUN_DIR:-$DECK_DIR/run}"
mkdir -p "$RUN"
cp -f "$DECK_DIR"/Ainflate_0000.rad "$DECK_DIR"/Ainflate_0001.rad "$RUN"/
cd "$RUN"
rm -f AinflateA[0-9]* Ainflate_A*.vtk AinflateT01

echo "=== QS-ish starter  nt=$OMP_NUM_THREADS ==="
starter_linux64_gf -i Ainflate_0000.rad -np 1 | tee starter.log
echo "=== QS-ish engine ==="
# 10× slower ramp than the 90 s dynamic first-light cap. CFL still dies after λ≥2.
TIMEOUT_S="${ENGINE_TIMEOUT:-1800}"
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
  --label "# A-inflate QS-ish (qs-ish-pload-400ms) — RUN"
if [[ -f "$DECK_DIR/artifacts/inflate-a-radioss-qs-golden.json" ]]; then
  cp -f "$DECK_DIR/artifacts/inflate-a-radioss-qs-golden.json" \
    "$DECK_DIR/inflate-a-radioss-qs-golden.json"
fi
echo "done. artifacts in $DECK_DIR/artifacts"
