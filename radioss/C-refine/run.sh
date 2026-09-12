#!/usr/bin/env bash
# OpenRadioss C-refine: ship / fine / finer. Same A-refine tools; no coarse, no finest.
set -euo pipefail
exec bash "$(cd "$(dirname "$0")/.." && pwd)/refine_ladder.sh" C "$@"
