#!/usr/bin/env python3
"""Live catalog/reader sample; requires BeautifulSoup, Playwright and Chromium.

Chromium requests are transported by curl so the Cloud proxy CA is verified by
its configured system trust store. No TLS verification is disabled.
"""
import datetime
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE = 'https://imperiomanhwa.com'
ROOT = Path(__file__).resolve().parents[1]
MANGA = '/manga/saqueando-innumerables-talentos-me-converti-en-dios/'


def fetch(url):
    time.sleep(1)
    return subprocess.check_output(['curl', '-fsSL', '--max-time', '40', url])


def props(path):
    doc = BeautifulSoup(fetch(BASE + path), 'html.parser')
    return json.loads(doc.select_one('script[data-page]').string)['props']


def main():
    checks = []
    for path in ['/mejores-manhwas-2026/', '/mejores-manhwas-2026/page/2/', '/manga/', '/manga/page/2/']:
        data = props(path)
        assert data['series'] and data['pagination']['page'] == (2 if '/2/' in path else 1)
        checks.append(path)
    search = props('/buscar?q=saqueando')
    assert any(m['url'] == MANGA for m in search['series'])
    checks.append('búsqueda por título')
    detail = props(MANGA)
    assert detail['series']['title'] and detail['series']['cover']
    chapters = list(detail['chapters'])
    for page in range(2, detail['chapters_pagination']['last'] + 1):
        chapters.extend(json.loads(fetch(BASE + MANGA + f'capitulos/{page}.json'))['items'])
    assert len(chapters) == detail['chapters_pagination']['total']
    assert len({c['url'] for c in chapters}) == len(chapters)
    checks.append(f'ficha y {len(chapters)} capítulos sin duplicados')
    reader_url = BASE + chapters[0]['url']
    source = (ROOT / 'src/es/imperiomanhwa/src/eu/kanade/tachiyomi/extension/es/imperiomanhwa/ImperioManhwa.kt').read_text()
    script = re.search(r'val READER_SCRIPT = """(.*?)"""', source, re.S)[1]
    with sync_playwright() as p, tempfile.TemporaryDirectory() as temp:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page()

        def transport(route):
            req = route.request
            if req.resource_type in ('image', 'font', 'media') or req.method != 'GET':
                route.abort()
                return
            headers_path = str(Path(temp) / 'headers')
            result = subprocess.run(['curl', '-sS', '--max-time', '40', '-D', headers_path,
                                     '-H', 'User-Agent: ' + req.headers.get('user-agent', ''),
                                     '-H', 'Referer: ' + req.headers.get('referer', ''), '--url', req.url], capture_output=True)
            if result.returncode:
                route.abort()
                return
            head = Path(headers_path).read_text().strip().split('\n\n')[-1].splitlines()
            headers = {}
            for line in head[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    if key.lower() not in ('content-length', 'transfer-encoding', 'content-encoding'):
                        headers[key] = value.strip()
            route.fulfill(status=int(head[0].split()[1]), headers=headers, body=result.stdout)

        page.route('**/*', transport)
        page.goto(reader_url, wait_until='domcontentloaded', timeout=90000)
        result = None
        deadline = time.monotonic() + 60
        while result is None and time.monotonic() < deadline:
            page.wait_for_timeout(1000)
            result = page.evaluate(script)
        assert result is not None, 'El lector no entregó todas las imágenes en 60 segundos'
        assert 'error' not in result, result
        urls = result['urls']
        assert len(urls) == props(chapters[0]['url'])['total']
        checks.append(f'lector JavaScript: {len(urls)} imágenes completas')
        # Include an actual comic page, not only the first banner/preview.
        for index in sorted({0, 1, len(urls) - 1}):
            data = fetch(urls[index])
            assert data.startswith((b'\xff\xd8\xff', b'\x89PNG', b'RIFF')), f'Imagen {index} inválida'
            checks.append(f'descarga de imagen {index + 1}: {len(data)} bytes')
        browser.close()
    report = {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scope': 'HTTP y JavaScript del lector en Chromium; no ejecuta el APK ni Android WebView',
              'status': 'passed_live_sample', 'checks_passed': checks}
    out = ROOT / 'reports/imperiomanhwa.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
