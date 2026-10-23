#!/usr/bin/env python3
"""Sondeos HTTP de una muestra pública. No sustituyen pruebas del APK en Mihon."""
import datetime
import json
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)
    return value


class Probe:
    def __init__(self, base_url):
        self.passed = []
        self.last_url = None
        self.observations = []
        self.base_url = base_url

    def get(self, url, label, as_json=True):
        self.last_url = url
        time.sleep(1)
        # KeiSource envía Referer y Origin del sitio también en las peticiones de imágenes.
        request = urllib.request.Request(url, headers={
            "User-Agent": "mihon-extensiones-connectivity-check/1.0",
            "Referer": self.base_url + "/", "Origin": self.base_url,
        })
        with urllib.request.urlopen(request, timeout=20) as response:
            if as_json:
                body = response.read(16 * 1024 * 1024)
                value = json.loads(body)
            else:
                value = {"url": response.url, "content_type": response.headers.get_content_type()}
                response.read(1024)
        self.passed.append(label)
        return value

    def pages(self, urls):
        require(urls, "No hay imágenes públicas")
        require(all(urllib.parse.urlsplit(u).scheme in {"http", "https"} and urllib.parse.urlsplit(u).netloc for u in urls),
                "La lista incluye URLs de imágenes inválidas")
        self.passed.append(f"extracción de {len(urls)} URLs de imágenes")
        image = self.get(urls[0], "solicitud de primera imagen", False)
        require(image["content_type"].startswith("image/"), "La respuesta no es una imagen")
        self.passed.append("primera imagen con tipo de contenido válido")


def olympus(p):
    base = "https://olympusxyz.com"
    p.get(base, "dominio", False)
    catalog = p.get(base + "/api/series/list", "catálogo de búsqueda")["data"]
    manga = next(m for m in catalog if m.get("type") == "comic")
    require(manga["name"] and manga["slug"], "Título/slug ausente")
    require(any(manga["name"].lower() in m["name"].lower() for m in catalog), "Búsqueda vacía")
    p.passed.append("búsqueda por título en catálogo")
    require(p.get(base + "/api/rankings?page=1&period=total_ranking", "populares")["data"], "Sin populares")
    require(p.get(base + "/api/new-chapters?page=1", "actualizaciones")["data"], "Sin actualizaciones")
    slug = urllib.parse.quote(manga["slug"], safe="")
    require(p.get(base + f"/api/series/{slug}?type=comic", "ficha")["data"]["name"], "Sin título en ficha")
    chapters = p.get(f"https://panel.olympusxyz.com/api/series/{slug}/chapters?page=1&direction=desc&type=comic", "primera página de capítulos")["data"]
    chapter = require(chapters, "Sin capítulos públicos")[0]
    pages = p.get(base + f"/api/capitulo/comic-{slug}/{chapter['id']}", "páginas del capítulo")["chapter"]["pages"]
    p.pages(pages)


def mangadex(p):
    p.get("https://mangadex.org", "dominio", False)
    api = "https://api.mangadex.org"
    require(p.get(api + "/manga?limit=1&order[followedCount]=desc", "populares")["data"], "Sin populares")
    chapters = p.get(api + "/chapter?limit=100&translatedLanguage[]=es&translatedLanguage[]=es-la&order[publishAt]=desc&includeExternalUrl=0", "actualizaciones en español")["data"]
    available = [c for c in chapters if c["attributes"]["pages"] > 0 and not c["attributes"].get("externalUrl")]
    require(available, "La muestra de 100 capítulos no contiene páginas públicas alojadas en MangaDex")
    data = None
    for chapter in available[:5]:
        try:
            data = p.get(api + f"/at-home/server/{chapter['id']}", "URLs de imágenes")
            break
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            p.observations.append(f"Capítulo {chapter['id']}: at-home devuelve 404; no está disponible")
    require(data, "Ninguno de los cinco capítulos consultados tiene servidor de imágenes disponible")
    manga_id = next(r["id"] for r in chapter["relationships"] if r["type"] == "manga")
    manga = p.get(api + f"/manga/{manga_id}?includes[]=cover_art", "ficha")["data"]
    title = next(iter(manga["attributes"]["title"].values()))
    found = p.get(api + "/manga?" + urllib.parse.urlencode({"title": title, "limit": 100}), "búsqueda por título")["data"]
    require(any(m["id"] == manga_id for m in found), "La búsqueda no devuelve la obra")
    require(p.get(api + f"/manga/{manga_id}/feed?limit=10&translatedLanguage[]=es&translatedLanguage[]=es-la&order[chapter]=desc", "capítulos en español")["data"], "Sin capítulos")
    require(len(data["chapter"]["data"]) == chapter["attributes"]["pages"], "Recuento de páginas inconsistente")
    p.pages([f"{data['baseUrl']}/data/{data['chapter']['hash']}/{file}" for file in data["chapter"]["data"]])


def manhwaweb(p):
    p.get("https://manhwaweb.com", "dominio", False)
    api = "https://api.manhwaweb.com"
    popular = p.get(api + "/manhwa/nuevos", "populares")["top"]
    require(popular["manhwas_esp"] or popular["manhwas_raw"], "Sin populares")
    latest = p.get(api + "/latest/new-manhwa", "actualizaciones")["manhwas"]["manhwas_esp"]
    manga = require(latest, "Sin actualizaciones en español")[0]
    title = manga["name_manhwa"]
    found = p.get(api + "/manhwa/library?" + urllib.parse.urlencode({"buscar": title, "page": 0}), "búsqueda por título")["data"]
    require(found, "Búsqueda vacía")
    slug = urllib.parse.quote(found[0]["real_id"], safe="")
    details = p.get(api + f"/manhwa/see/{slug}", "ficha y capítulos")
    require(details["name_esp"], "Ficha sin título")
    require(isinstance(details["autor"], list) and isinstance(details["artista"], list), "Créditos inválidos")
    chapters = sorted(details["chapters"], key=lambda c: float(c["chapter"]), reverse=True)
    links = [v["link"] for c in chapters for v in c["versions"] if v.get("create") is not None]
    p.passed.append(f"{len(links)} versiones de capítulos publicados")
    link = next(link for link in links if link)
    chapter_slug = link.replace(details["_id"], details["real_id"]).rstrip("/").split("/")[-1]
    pages = p.get(api + "/chapters/see/" + urllib.parse.quote(chapter_slug, safe=""), "páginas del capítulo")["chapter"]["img"]
    p.pages(pages)


def main():
    report = {"timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "HTTP público; no ejecuta los APK ni Mihon", "sources": {}}
    for name, base, check in [("Olympus", "https://olympusxyz.com", olympus),
                              ("MangaDex", "https://mangadex.org", mangadex),
                              ("ManhwaWeb", "https://manhwaweb.com", manhwaweb)]:
        probe = Probe(base)
        try:
            check(probe)
            result = {"status": "passed_http_sample"}
        except Exception as error:
            result = {"status": "blocked_or_failed", "reason": f"{type(error).__name__}: {error}", "last_url": probe.last_url}
        result["checks_passed"] = probe.passed
        result["observations"] = probe.observations
        report["sources"][name] = result
        print(name, result["status"], result.get("reason", ""), flush=True)
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "reports/source-smoke.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return int(any(s["status"] != "passed_http_sample" for s in report["sources"].values()))


if __name__ == "__main__":
    sys.exit(main())
