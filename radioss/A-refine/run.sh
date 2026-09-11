#!/usr/bin/env bash
# Run the all-quad + /ADYREL A-refine ladder (coarse / ship / fine), then report.
# μ and ρ are never retuned. Ishell=1. Same PLOAD unless a labeled Kareem fork.
set -euo pipefail
DECK_ROOT="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DECK_ROOT/../.." && pwd)"
RADIOSS_ROOT="$(cd "$DECK_ROOT/.." && pwd)"
if [[ ! -f "$RADIOSS_ROOT/env.sh" ]]; then
  bash "$RADIOSS_ROOT/install_openradioss.sh"
fi
# shellcheck disable=SC1091
source "$RADIOSS_ROOT/env.sh"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

run_one() {
  local dens="$1"
  local timeout_s="${2:-180}"
  local deck="$DECK_ROOT/$dens"
  local run="${RUN_DIR:-$deck/run}"
  mkdir -p "$run"
  cp -f "$deck"/Ainflate_0000.rad "$deck"/Ainflate_0001.rad "$run"/
  cd "$run"
  echo "=== $dens starter  nt=$OMP_NUM_THREADS ==="
  starter_linux64_gf -i Ainflate_0000.rad -np 1 | tee starter.log
  echo "=== $dens engine (timeout ${timeout_s}s) ==="
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
  echo "=== $dens post ==="
  python3 "$ROOT/tools/radioss_post.py" --run-dir "$run" --deck-dir "$deck" \
    --label "# A-refine ${dens} — RUN"
  echo "done $dens. artifacts in $deck/artifacts"
}

python3 "$ROOT/tools/refine_letter_a.py" --out-dir "$DECK_ROOT"
python3 "$ROOT/tools/mesh_to_radioss.py" --allow-n --check \
  --mesh "$DECK_ROOT/meshes/A-coarse.json" --out-dir "$DECK_ROOT/coarse" \
  --note "A-refine coarse; same LAW42/PLOAD/ADYREL; do not retune μ/ρ"
python3 "$ROOT/tools/mesh_to_radioss.py" --allow-n --check \
  --mesh "$DECK_ROOT/meshes/A-ship.json" --out-dir "$DECK_ROOT/ship" \
  --note "A-refine ship N=1554; same LAW42/PLOAD/ADYREL; do not retune μ/ρ"
python3 "$ROOT/tools/mesh_to_radioss.py" --allow-n --check \
  --mesh "$DECK_ROOT/meshes/A-fine.json" --out-dir "$DECK_ROOT/fine" \
  --note "A-refine fine 1-to-4 nested; same LAW42/PLOAD/ADYREL; do not retune μ/ρ"

run_one coarse 180
run_one ship 180
run_one fine "${FINE_TIMEOUT:-600}"

python3 "$ROOT/tools/refine_report.py" --root "$DECK_ROOT"
echo "A-refine ladder done."
