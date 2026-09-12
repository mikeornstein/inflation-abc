#!/usr/bin/env bash
# Install OpenRadioss binaries for Inflation ABC first-light (cloud VM).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${OPENRADIOSS_PREFIX:-$ROOT/opt}"
TAG="${OPENRADIOSS_TAG:-latest-20260728}"
ZIP_URL="https://github.com/OpenRadioss/OpenRadioss/releases/download/${TAG}/OpenRadioss_linux64.zip"
mkdir -p "$PREFIX"
if [[ -x "$PREFIX/OpenRadioss/exec/starter_linux64_gf" ]]; then
  echo "OpenRadioss already present at $PREFIX/OpenRadioss"
else
  tmp="$(mktemp -d)"
  echo "Downloading $ZIP_URL"
  curl -L --fail --retry 4 --retry-delay 4 -o "$tmp/OpenRadioss_linux64.zip" "$ZIP_URL"
  unzip -q -o "$tmp/OpenRadioss_linux64.zip" -d "$PREFIX"
  rm -rf "$tmp"
fi
OR="$PREFIX/OpenRadioss"
test -x "$OR/exec/starter_linux64_gf"
test -x "$OR/exec/engine_linux64_gf"
test -x "$OR/exec/anim_to_vtk_linux64_gf"
cat > "$ROOT/env.sh" <<EOF
# shellcheck disable=SC2148
export OPENRADIOSS_PATH="$OR"
export RAD_CFG_PATH="\$OPENRADIOSS_PATH/hm_cfg_files"
export RAD_H3D_PATH="\$OPENRADIOSS_PATH/extlib/h3d/lib/linux64"
export OMP_STACKSIZE="\${OMP_STACKSIZE:-400m}"
export OMP_NUM_THREADS="\${OMP_NUM_THREADS:-4}"
export LD_LIBRARY_PATH="\$OPENRADIOSS_PATH/extlib/hm_reader/linux64:\${RAD_H3D_PATH}:\${LD_LIBRARY_PATH:-}"
export PATH="\$OPENRADIOSS_PATH/exec:\$PATH"
EOF
# shellcheck disable=SC1091
source "$ROOT/env.sh"
echo "starter: $(command -v starter_linux64_gf)"
ldd "$OR/exec/starter_linux64_gf" | grep -E 'not found' && {
  echo "BLOCKER: missing shared libraries for starter" >&2
  exit 1
} || true
echo "install ok  tag=$TAG"
