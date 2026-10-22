"""Bounded acquisition of explicitly selected official public sources.

Run as a module from Backend. No crawler, credentials, database or ML imports.
Successful URLs are reused with integrity checks. Changed documents require an
explicit refresh and remain preserved under their previous content hash.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request

HOSTS = frozenset({
    'www.ramajudicial.gov.co', 'portalhistorico.ramajudicial.gov.co',
    'publicacionesprocesales.ramajudicial.gov.co',
    'consultajurisprudencial.ramajudicial.gov.co',
    'cortesuprema.gov.co', 'www.cortesuprema.gov.co',
    'archivodigitalapi.cortesuprema.gov.co',
    'www.fiscalia.gov.co', 'www.defensajuridica.gov.co',
    # Original procurement documents used to reconstruct stage variables.
    'www.ani.gov.co', 'ani.gov.co', 'wwwold.ani.gov.co',
    'www.consejodeestado.gov.co', 'consejodeestado.gov.co',
})
MAX_BYTES = 32 * 1024 * 1024


def official_url(value):
    parts = urlsplit(value)
    if (parts.scheme != 'https' or parts.hostname not in HOSTS
            or parts.username or parts.password or parts.port not in (None, 443)):
        raise ValueError('Se requiere URL HTTPS de una fuente oficial admitida')
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Validate before urllib contacts a redirect destination.
        return super().redirect_request(req, fp, code, msg, headers, official_url(newurl))


class Links(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag not in ('a', 'iframe'):
            return
        attr = dict(attrs).get('href' if tag == 'a' else 'src')
        if attr:
            try:
                self.links.add(official_url(urljoin(self.base, attr)))
            except ValueError:
                pass


def stamp():
    return datetime.now(timezone.utc).isoformat()


def checksum(body):
    return hashlib.sha256(body).hexdigest()


def read_cached(root, record):
    sha = record['sha256']
    if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
        raise ValueError('Hash de archivo inválido')
    body = (root / 'objects' / sha).read_bytes()
    if len(body) != record['bytes'] or checksum(body) != sha:
        raise ValueError('La copia local no coincide con su registro de adquisición')
    return body


def fetch(url):
    url = official_url(url)
    request = Request(url, headers={'User-Agent': 'JudicialCorpusResearch/1.0', 'Accept-Encoding': 'identity'})
    opener = build_opener(OfficialRedirects())
    with opener.open(request, timeout=25) as response:
        final_url = official_url(response.url)
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('Fuente mayor de 32 MiB')
        media = response.headers.get_content_type()
        if body.startswith(b'%PDF'):
            media = 'application/pdf'
        elif media not in ('text/html', 'application/xhtml+xml'):
            raise ValueError('Tipo de contenido no admitido')
        if media == 'application/pdf' and not body.startswith(b'%PDF'):
            raise ValueError('Respuesta PDF sin cabecera PDF')
        return body, media, final_url


def acquire(catalog, root, *, refresh=False, fetcher=fetch):
    # Validate the complete selection before fetching or appending the ledger.
    # A missing kind in a later entry must not leave a partially acquired run
    # without a receipt after earlier sources have already been downloaded.
    if not isinstance(catalog, dict) or not isinstance(catalog.get('sources'), list):
        raise ValueError('El catálogo debe contener una lista de fuentes')
    sources = catalog['sources']
    if not 1 <= len(sources) <= 25:
        raise ValueError('Seleccionar entre 1 y 25 fuentes explícitas por ejecución')
    for item in sources:
        if (not isinstance(item, dict)
                or any(not isinstance(item.get(key), str) or not item[key].strip()
                       for key in ('id', 'kind', 'url'))):
            raise ValueError('Cada fuente requiere id, kind y url textuales no vacíos')
    urls = [official_url(item['url']) for item in sources]
    if len(set(urls)) != len(urls) or len({item['id'] for item in sources}) != len(sources):
        raise ValueError('Fuentes duplicadas')
    root = Path(root)
    (root / 'objects').mkdir(parents=True, exist_ok=True)
    (root / 'runs').mkdir(exist_ok=True)
    ledger = root / 'acquisitions.jsonl'
    latest = {}
    if ledger.exists():
        for line in ledger.read_text(encoding='utf-8').splitlines():
            record = json.loads(line)
            latest[record['requested_url']] = record
    records, errors = [], []
    for source, url in zip(sources, urls):
        try:
            reused = url in latest and not refresh
            if reused:
                record = latest[url]
                body = read_cached(root, record)
            else:
                body, media, final_url = fetcher(url)
                sha = checksum(body)
                target = root / 'objects' / sha
                if target.exists():
                    if target.read_bytes() != body:
                        raise ValueError('Colisión o archivo local alterado')
                else:
                    with target.open('xb') as output:
                        output.write(body)
                record = {'requested_url': url, 'final_url': final_url,
                          'acquired_at': stamp(), 'sha256': sha, 'bytes': len(body), 'media_type': media}
                with ledger.open('a', encoding='utf-8') as output:
                    output.write(json.dumps(record, ensure_ascii=False) + '\n')
                latest[url] = record
                time.sleep(.5)
            links = []
            if record['media_type'] in ('text/html', 'application/xhtml+xml'):
                parser = Links(record['final_url'])
                parser.feed(body.decode('utf-8', errors='replace'))
                links = sorted(parser.links)
            records.append({**record, 'source_id': source['id'], 'kind': source['kind'],
                            'reused': reused, 'official_links': links,
                            'review_status': 'PENDIENTE_REVISION', 'training_label': None})
        except (OSError, ValueError, HTTPError) as exc:
            errors.append({'source_id': source['id'], 'url': url,
                           'error_type': type(exc).__name__, 'http_status': getattr(exc, 'code', None)})
    report = {'created_at': stamp(), 'sources': records, 'errors': errors,
              'collector_sha256': checksum(Path(__file__).read_bytes()),
              'catalog_sha256': checksum(json.dumps(catalog, sort_keys=True, ensure_ascii=False).encode()),
              'training_labels_created': 0, 'database_accessed': False,
              'scope': 'Descubrimiento documental; adquirir no acredita condena, firmeza ni vínculo SECOP.'}
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'
    with (root / 'runs' / name).open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2, ensure_ascii=False)
    return report, root / 'runs' / name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    report, path = acquire(json.loads(args.catalog.read_text(encoding='utf-8')), args.root, refresh=args.refresh)
    print(json.dumps({'sources': len(report['sources']), 'errors': len(report['errors']), 'report': str(path)}))
    return bool(report['errors'])


if __name__ == '__main__':
    raise SystemExit(main())
