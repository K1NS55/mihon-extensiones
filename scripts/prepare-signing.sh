#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SIGNING_KEY:?Falta el secreto SIGNING_KEY (JKS en base64)}"
: "${KEY_STORE_PASSWORD:?Falta el secreto KEY_STORE_PASSWORD}"
umask 077
test ! -e signingkey.jks || { echo 'Ya existe signingkey.jks' >&2; exit 1; }
printf '%s' "$SIGNING_KEY" | base64 --decode > signingkey.jks
keytool -list -keystore signingkey.jks -alias mihon -storepass:env KEY_STORE_PASSWORD >/dev/null
