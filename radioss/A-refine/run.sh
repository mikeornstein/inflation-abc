#!/usr/bin/env bash
# Run the all-quad + /ADYREL A-refine ladder, then report.
# μ and ρ are never retuned. Ishell=1. Same PLOAD unless a labeled Kareem fork.
#
#   bash radioss/A-refine/run.sh              # coarse / ship / fine
#   bash radioss/A-refine/run.sh --finest-only # nested 1-to-4 of finer (does not wipe lower tapes)
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

FINER_ONLY=0
FINEST_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --finer-only) FINER_ONLY=1 ;;
    --finest-only) FINEST_ONLY=1 ;;
  esac
done

run_one() {
  local dens="$1"
  local timeout_s="${2:-180}"
  local extra_post="${3:-}"
  local deck="${4:-$DECK_ROOT/$dens}"
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
  # shellcheck disable=SC2086
  python3 "$ROOT/tools/radioss_post.py" --run-dir "$run" --deck-dir "$deck" \
    --label "# A-refine ${dens} — RUN" ${extra_post}
  echo "done $dens. artifacts in $deck/artifacts"
}

if [[ "$FINEST_ONLY" -eq 1 ]]; then
  python3 "$ROOT/tools/refine_letter_a.py" --out-dir "$DECK_ROOT" --finest-only
  mkdir -p "$DECK_ROOT/forks/finest-stop5e7"
  python3 "$ROOT/tools/mesh_to_radioss.py" --allow-n --check \
    --mesh "$DECK_ROOT/meshes/A-finest.json" --out-dir "$DECK_ROOT/forks/finest-stop5e7" \
    --noda-stop 5e-7 \
    --note "A-refine finest 1-to-4 of finer; STOP Tmin=5e-7 (mesh CFL ~9.7e-7 at 1e-6); same LAW42/PLOAD/ADYREL; do not retune μ/ρ"
  run_one finest "${FINEST_TIMEOUT:-2400}" "--metrics-only" "$DECK_ROOT/forks/finest-stop5e7"
  python3 "$ROOT/tools/refine_same_load.py" --root "$DECK_ROOT" --session-rerun finest
elif [[ "$FINER_ONLY" -eq 1 ]]; then
  python3 "$ROOT/tools/refine_letter_a.py" --out-dir "$DECK_ROOT" --finer-only
  python3 "$ROOT/tools/mesh_to_radioss.py" --allow-n --check \
    --mesh "$DECK_ROOT/meshes/A-finer.json" --out-dir "$DECK_ROOT/finer" \
    --note "A-refine finer 1-to-4 of fine; same LAW42/PLOAD/ADYREL; do not retune μ/ρ"
  run_one finer "${FINER_TIMEOUT:-900}" "--metrics-only"
else
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
fi

python3 "$ROOT/tools/refine_report.py" --root "$DECK_ROOT"
echo "A-refine ladder done."
