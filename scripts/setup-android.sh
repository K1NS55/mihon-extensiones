#!/usr/bin/env bash
# Instala un SDK reproducible en runners sin Android preinstalado.
set -euo pipefail
sdk_root=${1:?Indica el directorio del SDK}
mkdir -p "$sdk_root"
sdk_root=$(cd "$sdk_root" && pwd)
if [[ ! -x "$sdk_root/cmdline-tools/19.0/bin/sdkmanager" ]]; then
  staging=$(mktemp -d)
  trap 'rm -rf "$staging"' EXIT
  curl --fail --location --show-error --retry 2 \
    https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip \
    --output "$staging/tools.zip"
  printf '%s  %s\n' 7ec965280a073311c339e571cd5de778b9975026cfcbe79f2b1cdcb1e15317ee "$staging/tools.zip" | sha256sum --check --status
  unzip -q "$staging/tools.zip" -d "$staging"
  mkdir -p "$sdk_root/cmdline-tools/19.0"
  cp -a "$staging/cmdline-tools/." "$sdk_root/cmdline-tools/19.0/"
fi
sdkmanager="$sdk_root/cmdline-tools/19.0/bin/sdkmanager"
set +o pipefail
yes | "$sdkmanager" --sdk_root="$sdk_root" --licenses >/dev/null
set -o pipefail
"$sdkmanager" --sdk_root="$sdk_root" 'platforms;android-37.0' 'build-tools;36.0.0' 'build-tools;37.0.0'
if [[ -n "${GITHUB_ENV:-}" ]]; then
  printf 'ANDROID_HOME=%s\nANDROID_SDK_ROOT=%s\n' "$sdk_root" "$sdk_root" >> "$GITHUB_ENV"
fi
