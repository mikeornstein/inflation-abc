#!/usr/bin/env bash
# Shared OpenRadioss refine ladder for letters B and C (Mike 2026-09-12).
# Same tools as A-refine. Ship / fine / finer only — no coarse, no finest.
# μ and ρ are never retuned. Ishell=1. Hang guard /DT/NODA/STOP (not CST).
#
#   bash radioss/refine_ladder.sh B
#   bash radioss/refine_ladder.sh C
set -euo pipefail
LETTER="${1:?letter B or C}"
shift || true
LETTER="${LETTER^^}"
if [[ "$LETTER" != "B" && "$LETTER" != "C" ]]; then
  echo "usage: $0 B|C" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RADIOSS_ROOT="$(cd "$(dirname "$0")" && pwd)"
DECK_ROOT="$RADIOSS_ROOT/${LETTER}-refine"
if [[ ! -f "$RADIOSS_ROOT/env.sh" ]]; then
  bash "$RADIOSS_ROOT/install_openradioss.sh"
fi
# shellcheck disable=SC1091
source "$RADIOSS_ROOT/env.sh"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

run_one() {
  local dens="$1"
  local timeout_s="${2:-180}"
  local extra_post="${3:-}"
  local deck="${4:-$DECK_ROOT/$dens}"
  local run="${RUN_DIR:-$deck/run}"
  mkdir -p "$run"
  cp -f "$deck"/Ainflate_0000.rad "$deck"/Ainflate_0001.rad "$run"/
  cd "$run"
  # Drop leftover ANIM/VTK/T01 from a previous engine so post cannot mix tapes.
  rm -f AinflateA[0-9]* Ainflate_A*.vtk AinflateT01
  echo "=== ${LETTER} ${dens} starter  nt=$OMP_NUM_THREADS ==="
  starter_linux64_gf -i Ainflate_0000.rad -np 1 | tee starter.log
  echo "=== ${LETTER} ${dens} engine (timeout ${timeout_s}s) ==="
  set +e
  set +o pipefail
  timeout --signal=TERM "$timeout_s" engine_linux64_gf -i Ainflate_0001.rad | tee engine.log
  eng_ec=${PIPESTATUS[0]}
  set -euo pipefail
  if [[ "$eng_ec" -eq 124 ]]; then
    echo "engine timeout (ANIM kept if written)" | tee -a engine.log
  elif [[ "$eng_ec" -ne 0 ]]; then
    echo "engine exit $eng_ec (post will use any ANIM written)" | tee -a engine.log
  fi
  echo "=== ${LETTER} ${dens} post ==="
  # shellcheck disable=SC2086
  python3 "$ROOT/tools/radioss_post.py" --run-dir "$run" --deck-dir "$deck" \
    --label "# ${LETTER}-refine ${dens} — RUN" ${extra_post}
  echo "done ${LETTER} ${dens}. artifacts in $deck/artifacts"
}

mkdir -p "$DECK_ROOT"
python3 "$ROOT/tools/refine_letter_a.py" --letter "$LETTER" --out-dir "$DECK_ROOT" --with-finer
python3 "$ROOT/tools/mesh_to_radioss.py" --allow-n --check \
  --mesh "$DECK_ROOT/meshes/${LETTER}-ship.json" --out-dir "$DECK_ROOT/ship" \
  --note "${LETTER}-refine ship; same LAW42/PLOAD/ADYREL; do not retune μ/ρ"
python3 "$ROOT/tools/mesh_to_radioss.py" --allow-n --check \
  --mesh "$DECK_ROOT/meshes/${LETTER}-fine.json" --out-dir "$DECK_ROOT/fine" \
  --note "${LETTER}-refine fine 1-to-4 nested; same LAW42/PLOAD/ADYREL; do not retune μ/ρ"
python3 "$ROOT/tools/mesh_to_radioss.py" --allow-n --check \
  --mesh "$DECK_ROOT/meshes/${LETTER}-finer.json" --out-dir "$DECK_ROOT/finer" \
  --note "${LETTER}-refine finer 1-to-4 of fine; same LAW42/PLOAD/ADYREL; do not retune μ/ρ"

run_one ship "${SHIP_TIMEOUT:-300}"
run_one fine "${FINE_TIMEOUT:-900}"
run_one finer "${FINER_TIMEOUT:-1800}" "--metrics-only"

python3 "$ROOT/tools/refine_same_load.py" --root "$DECK_ROOT" \
  --session-rerun ship --session-rerun fine --session-rerun finer
python3 "$ROOT/tools/refine_report.py" --root "$DECK_ROOT"
echo "${LETTER}-refine ladder done."
