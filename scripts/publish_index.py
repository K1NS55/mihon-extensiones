#!/usr/bin/env python3
"""Genera un índice Mihon desde APK reales, verificados con las herramientas Android."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

MODULES = ("es/olympusscanlation", "all/mangadex", "es/manhwaweb", "es/leercapitulo")
REPOSITORY = "K1NS55/mihon-extensiones"


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def check_version(entry, previous, fingerprint, identical=False):
    if previous.get("signingKey") != fingerprint:
        raise ValueError("La firma cambió; se requiere la clave original")
    for old in previous["extensionList"]["extensions"]:
        if old["packageName"] == entry["packageName"]:
            if identical and int(entry["versionCode"]) == int(old["versionCode"]):
                return
            if int(entry["versionCode"]) <= int(old["versionCode"]):
                raise ValueError(f"Incrementa versionCode de {entry['name']} antes de publicar")


def generate(root, output, tools, tag, previous=None, previous_dir=None, apk_base_url=None):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", tag):
        raise ValueError("Tag inválido")
    if not 1 <= len(MODULES) <= 10:
        raise ValueError("El repositorio debe contener entre 1 y 10 extensiones")
    if output.exists():
        raise ValueError("El directorio de salida ya existe; usa uno vacío/nuevo")
    entries, assets, fingerprints, legacy = [], [], set(), []
    base = f"https://raw.githubusercontent.com/{REPOSITORY}/repo"
    release = f"https://github.com/{REPOSITORY}/releases/download/{tag}"
    if apk_base_url:
        parsed = urlsplit(apk_base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("La base de APK debe ser una URL HTTPS sin query ni fragmento")
        release = apk_base_url.rstrip("/")
    for module in MODULES:
        build = root / "src" / module / "build"
        info = json.loads((build / "keiyoushi-source-info.json").read_text())
        apks = list((build / "outputs/apk/release").glob("*.apk"))
        if len(apks) != 1:
            raise ValueError(f"{module}: se esperaba exactamente un APK actual")
        apk = apks[0]
        verify = run(str(tools / "apksigner"), "verify", "--verbose", "--print-certs", str(apk))
        if "Android Debug" in verify:
            raise ValueError("No se publican APK con firma de depuración")
        digest = sorted(set(re.findall(r"certificate SHA-256 digest: ([a-fA-F0-9]{64})", verify)))
        signer_count = re.search(r"Number of signers: (\d+)", verify)
        if not signer_count or signer_count.group(1) != "1" or len(digest) != 1:
            raise ValueError("Se requiere un único certificado verificable")
        fingerprints.add(digest[0].lower())
        badging = run(str(tools / "aapt"), "dump", "badging", str(apk))
        match = re.search(r"package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", badging)
        if not match or match.groups() != (info["packageName"], str(info["versionCode"]), info["versionName"]):
            raise ValueError(f"Metadatos no coinciden con el APK: {module}")
        if not info["sources"] or info["extensionLib"] != "1.6":
            raise ValueError(f"Fuentes o versión de API incorrectas: {module}")
        if len({s['id'] for s in info['sources']}) != len(info['sources']):
            raise ValueError(f"IDs de fuente duplicados: {module}")
        icon = root / "src" / module / "res/mipmap-xhdpi/ic_launcher.png"
        if not icon.exists():
            icon = root / "core/src/main/res/mipmap-xhdpi/ic_launcher.png"
        icon_name = info["packageName"] + ".png"
        entry = {
            "name": info["name"], "packageName": info["packageName"],
            "resources": {"apkUrl": f"{release}/{apk.name}", "iconUrl": f"{base}/icon/{icon_name}"},
            "extensionLib": info["extensionLib"], "versionCode": str(info["versionCode"]),
            "versionName": info["versionName"],
            "contentWarning": {1: "CONTENT_WARNING_SAFE", 2: "CONTENT_WARNING_MIXED", 3: "CONTENT_WARNING_NSFW"}[info["contentWarning"]],
            "sources": [{"id": str(s["id"]), "name": s["name"], "language": s["lang"],
                         "homeUrl": s["baseUrl"], "mirrorUrls": s.get("mirrorUrls", [])} for s in info["sources"]],
        }
        if previous:
            old_apk = previous_dir / "apk" / apk.name if previous_dir else None
            identical = bool(old_apk and old_apk.is_file() and
                             hashlib.sha256(old_apk.read_bytes()).digest() == hashlib.sha256(apk.read_bytes()).digest())
            check_version(entry, previous, digest[0].lower(), identical)
            if identical:
                old_entry = next((old for old in previous["extensionList"]["extensions"]
                                  if old["packageName"] == entry["packageName"]), None)
                if old_entry:
                    entry["resources"]["apkUrl"] = old_entry["resources"]["apkUrl"]
        entries.append(entry)
        legacy.append({"name": "Tachiyomi: " + info["name"], "pkg": info["packageName"],
                       "apk": apk.name, "lang": "all" if len(info["sources"]) > 1 else info["sources"][0]["lang"],
                       "code": info["versionCode"], "version": info["versionName"],
                       "nsfw": int(info["contentWarning"] != 1),
                       "sources": [{"id": str(s["id"]), "name": s["name"], "lang": s["lang"], "baseUrl": s["baseUrl"]} for s in info["sources"]]})
        assets.append((apk, icon, icon_name))
    if len(fingerprints) != 1:
        raise ValueError("Los APK no comparten la misma firma")
    fingerprint = fingerprints.pop()
    index = {"name": "Mihon extensiones de K1NS55", "badgeLabel": "K1NS55", "signingKey": fingerprint,
             "contact": {"website": f"https://github.com/{REPOSITORY}", "discord": None},
             "extensionList": {"extensions": entries}, "extensionListUrl": None}
    (output / "apk").mkdir(parents=True)
    (output / "icon").mkdir()
    checksums = []
    for apk, icon, icon_name in assets:
        shutil.copy2(apk, output / "apk" / apk.name)
        shutil.copy2(icon, output / "icon" / icon_name)
        checksums.append(f"{hashlib.sha256(apk.read_bytes()).hexdigest()}  apk/{apk.name}")
    (output / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    (output / "index.min.json").write_text(json.dumps(legacy, ensure_ascii=False, separators=(",", ":")) + "\n")
    (output / "repo.json").write_text(json.dumps({"index_v2": f"{base}/index.json", "meta": {
        "name": index["name"], "shortName": index["badgeLabel"], "website": index["contact"]["website"],
        "signingKeyFingerprint": fingerprint}}, indent=2) + "\n")
    (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build-tools", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--apk-base-url", help="Alojamiento HTTPS alternativo para los APK, por ejemplo una rama Git")
    args = parser.parse_args()
    previous = json.loads(args.previous.read_text()) if args.previous else None
    result = generate(args.root, args.output, args.build_tools, args.tag, previous,
                      args.previous.parent if args.previous else None, args.apk_base_url)
    print(f"Índice validado: {len(result['extensionList']['extensions'])} extensiones")
