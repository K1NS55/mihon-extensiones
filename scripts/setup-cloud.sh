#!/usr/bin/env bash
# Entorno Cloud x86_64; no modifica archivos fuente ni requiere Android Studio.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
test "$(uname -m)" = x86_64
mkdir -p /workspace/toolchains /workspace/downloads /workspace/.cache/gradle /workspace/.android /workspace/.home
fetch() {
  local url=$1 target=$2 digest=$3
  if [[ ! -f "$target" ]] || ! printf '%s  %s\n' "$digest" "$target" | sha256sum --check --status; then
    curl --fail --location --show-error --retry 2 "$url" --output "$target"
  fi
  printf '%s  %s\n' "$digest" "$target" | sha256sum --check --status
}
if [[ ! -x /workspace/toolchains/jdk-25.0.4.1/bin/javac ]]; then
  fetch https://download.oracle.com/java/25/archive/jdk-25.0.4.1_linux-x64_bin.tar.gz \
    /workspace/downloads/jdk25.tar.gz dd7e7f51d23bcffe85f1a439577ce1c0190a33417b34afdb338f9b3897bdeaec53
  tar -xzf /workspace/downloads/jdk25.tar.gz -C /workspace/toolchains
fi
if [[ ! -x /workspace/android-sdk/cmdline-tools/19.0/bin/sdkmanager ]]; then
  fetch https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip \
    /workspace/downloads/cmdline19.zip 7ec965280a073311c339e571cd5de778b9975026cfcbe79f2b1cdcb1e15317ee
  staging=$(mktemp -d /workspace/downloads/android-tools.XXXXXX)
  unzip -q /workspace/downloads/cmdline19.zip -d "$staging"
  mkdir -p /workspace/android-sdk/cmdline-tools/19.0
  cp -a "$staging/cmdline-tools/." /workspace/android-sdk/cmdline-tools/19.0/
  rm -rf "$staging"
fi
python3 - <<'PY'
import os
import shlex
import urllib.parse
from pathlib import Path
trust = Path('/etc/ssl/certs/java/cacerts')
if not trust.is_file():
    raise SystemExit('Falta el truststore Java del sistema; instalar ca-certificates-java sin desactivar TLS')
proxy = urllib.parse.urlsplit(os.environ.get('HTTPS_PROXY', ''))
options = ['-Djavax.net.ssl.trustStore=' + str(trust), '-Duser.home=/workspace/.home']
if proxy.hostname:
    for protocol in ['http', 'https']:
        options.extend([f'-D{protocol}.proxyHost={proxy.hostname}', f'-D{protocol}.proxyPort={proxy.port or 80}'])
Path('/workspace/toolchains/activate.sh').write_text('''export JAVA_HOME=/workspace/toolchains/jdk-25.0.4.1
export ANDROID_HOME=/workspace/android-sdk
export ANDROID_USER_HOME=/workspace/.android
export GRADLE_USER_HOME=/workspace/.cache/gradle
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/19.0/bin:$ANDROID_HOME/platform-tools:$PATH"
''' + 'export JAVA_TOOL_OPTIONS=' + shlex.quote(' '.join(options)) + '\n')
PY
source /workspace/toolchains/activate.sh
# yes termina por SIGPIPE cuando sdkmanager deja de leer: comprobar el estado del SDK.
set +o pipefail
yes | sdkmanager --sdk_root="$ANDROID_HOME" --licenses >/workspace/downloads/licenses.log 2>&1
set -o pipefail
sdkmanager --sdk_root="$ANDROID_HOME" 'platforms;android-37.0' 'build-tools;36.0.0' 'build-tools;37.0.0' 'platform-tools'
cd "$repo"
python3 -m venv /workspace/.venvs/mihon-smoke
/workspace/.venvs/mihon-smoke/bin/pip install --disable-pip-version-check -r scripts/requirements-smoke.txt
./gradlew --version
python3 -m unittest discover -s tests -v
