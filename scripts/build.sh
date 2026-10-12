#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
modules=("${@}")
if ((${#modules[@]} == 0)); then
  modules=(:src:es:olympusscanlation :src:all:mangadex :src:es:manhwaweb :src:es:leercapitulo)
fi
tasks=()
for module in "${modules[@]}"; do
  case "$module" in
    :src:es:olympusscanlation|:src:all:mangadex|:src:es:manhwaweb|:src:es:leercapitulo) ;;
    *) echo "Módulo no autorizado: $module" >&2; exit 1 ;;
  esac
  tasks+=("${module}:assembleRelease" "${module}:lintRelease")
done
./gradlew --no-daemon --max-workers=4 "${tasks[@]}"
