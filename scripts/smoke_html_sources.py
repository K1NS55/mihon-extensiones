#!/usr/bin/env python3
"""Comprueba los selectores de las fuentes HTML contra una muestra pública real."""
import argparse
import datetime
import json
import urllib.parse
import urllib.request
import time
from pathlib import Path

from bs4 import BeautifulSoup

from smoke_sources import Probe, require


class HtmlProbe(Probe):
    def html(self, url, label):
        self.last_url = url
        time.sleep(3)
        req = urllib.request.Request(url, headers={
            "User-Agent": "mihon-extensiones-connectivity-check/1.0",
            "Referer": self.base_url + "/", "Origin": self.base_url,
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            doc = BeautifulSoup(response.read(16 * 1024 * 1024), "html.parser")
            doc.source_url = response.url
        self.passed.append(label)
        return doc


def link(doc, node, attr="href"):
    require(node, f"Elemento HTML ausente: {attr}")
    return urllib.parse.urljoin(doc.source_url, require(node.get(attr), f"Atributo {attr} ausente"))


def leercapitulo(p):
    home = p.html(p.base_url, "dominio y portada")
    popular = home.select(".lc-slide a.lc-slide-name")
    latest = home.select("article.lc-release a.lc-release-title")
    require(popular, "Selector de populares vacío")
    require(latest, "Selector de últimas actualizaciones vacío")
    p.passed.extend(["catálogo popular", "últimas actualizaciones"])
    selected = popular[0]
    title = selected.get_text(strip=True)
    manga_url = link(home, selected)
    results = p.html(p.base_url + "/manga/?" + urllib.parse.urlencode({"q": title}), "búsqueda por título")
    result_urls = [link(results, a) for a in results.select("article.lc-card a.lc-card-name")]
    require(manga_url.rstrip("/") in [u.rstrip("/") for u in result_urls], "La búsqueda no devuelve la obra seleccionada")
    details = p.html(manga_url, "ficha")
    require(details.select_one("h1"), "Ficha sin título")
    cover = link(details, details.select_one(".lc-cover-lg img"), "src")
    require(urllib.parse.urlsplit(cover).scheme in {"http", "https"}, "URL de portada inválida")
    chapters = details.select("a.lc-chapter-row")
    require(chapters, "La obra no tiene capítulos en el selector esperado")
    require(all(c.select_one(".n") for c in chapters), "Hay capítulos sin nombre")
    p.passed.append(f"lista de {len(chapters)} capítulos")
    reader = p.html(link(details, chapters[0]), "lector del capítulo")
    images = [link(reader, img, "data-src") for img in reader.select("#lcPages img[data-src]")]
    p.pages(images)


SOURCES = {"leercapitulo": ("https://www.leercapitulo.co", leercapitulo)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", choices=tuple(SOURCES))
    parser.add_argument("--output", type=Path, default=Path("reports/html-sources.json"))
    args = parser.parse_args()
    report = {"timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "Muestra HTTP y selectores HTML; no ejecuta APK ni Mihon", "sources": {}}
    for name in args.sources or SOURCES:
        base, check = SOURCES[name]
        p = HtmlProbe(base)
        try:
            check(p)
            result = {"status": "passed_http_sample"}
        except Exception as error:
            result = {"status": "blocked_or_failed", "reason": f"{type(error).__name__}: {error}",
                      "last_url": p.last_url}
        result["checks_passed"] = p.passed
        result["observations"] = p.observations
        report["sources"][name] = result
        print(name, result["status"], result.get("reason", ""), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return int(any(r["status"] != "passed_http_sample" for r in report["sources"].values()))


if __name__ == "__main__":
    raise SystemExit(main())
