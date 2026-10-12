#!/usr/bin/env bash
# Ejecutar una sola vez. Conservar una copia privada del directorio resultante.
set -euo pipefail
destination=${1:?Indica un directorio privado fuera del repositorio}
umask 077
mkdir -p "$destination"
destination=$(cd "$destination" && pwd)
repo=$(cd "$(dirname "$0")/.." && pwd)
case "$destination/" in "$repo/"*) echo 'La clave debe permanecer fuera del repositorio' >&2; exit 1;; esac
if [[ -e "$destination/release.jks" || -e "$destination/password" ]]; then
  echo 'El destino ya contiene una clave o contraseña; no se sobrescribe' >&2
  exit 1
fi
python3 -c 'import secrets; print(secrets.token_urlsafe(48), end="")' > "$destination/password"
keytool -genkeypair -keystore "$destination/release.jks" -storetype JKS \
  -alias mihon -keyalg RSA -keysize 4096 -validity 10000 \
  -storepass:file "$destination/password" -keypass:file "$destination/password" \
  -dname 'CN=K1NS55 Mihon Extensiones'
base64 -w0 "$destination/release.jks" > "$destination/keystore.base64"
keytool -exportcert -keystore "$destination/release.jks" -alias mihon \
  -storepass:file "$destination/password" -file "$destination/certificate.der"
sha256sum "$destination/certificate.der" > "$destination/fingerprint.sha256"
echo 'Clave creada. Subir keystore.base64 como SIGNING_KEY y password como KEY_STORE_PASSWORD a GitHub Actions. No publicar estos archivos.'
