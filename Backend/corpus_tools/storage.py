"""Resolve public storage links actually present in archived court bulletins.

Uses only the judicial tenant below and public anonymous session cookies. Does
not follow authentication redirects or create judicial/SECOP training labels.
"""
import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qs
from urllib.request import build_opener, Request, HTTPRedirectHandler, HTTPCookieProcessor
from urllib.error import HTTPError
from .acquire import checksum, read_cached, stamp, MAX_BYTES

TENANT = 'etbcsj-my.sharepoint.com'
PREFIX = '/personal/relspts_cendoj_ramajudicial_gov_co/'


def public_tenant_url(url):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.hostname != TENANT or parts.username
            or parts.password or parts.port not in (None, 443)
            or any(word in parts.path.lower() for word in ('login', 'authenticate', 'accessdenied'))):
        raise ValueError('Destino fuera del almacenamiento judicial público previsto')
    return parts


class PublicRedirects(HTTPRedirectHandler):
    max_redirections = 4

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_tenant_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def observed_downloads(html):
    urls = set()
    # Decode JSON strings already present in the public viewer. No JavaScript
    # execution, guessed endpoints, credential acquisition or URL rewriting.
    for match in re.finditer(r'"(?:[^"\\]|\\.)*"', html):
        if 'download.aspx' not in match.group():
            continue
        value = json.loads(match.group())
        if not isinstance(value, str) or not value.startswith('https://'):
            continue
        try:
            parts = public_tenant_url(value)
        except ValueError:
            continue
        if parts.path == PREFIX + '_layouts/15/download.aspx':
            urls.add(value)
    ids = {parse_qs(urlsplit(url).query).get('UniqueId', [''])[0] for url in urls}
    if len(ids) != 1 or '' in ids:
        raise ValueError('Visor sin un documento único verificable')
    return sorted(urls, key=lambda url: ('tempauth=' not in url.lower(), url))


def store(root, body):
    sha = checksum(body)
    path = root / 'objects' / sha
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError('Objeto documental alterado')
    else:
        with path.open('xb') as output:
            output.write(body)
    return sha


def resolve(root, index, output):
    links = {}
    for lead in index['leads']:
        # Validate the archived parent before trusting its recorded links.
        parent = root / 'objects' / lead['sha256']
        if not re.fullmatch('[a-f0-9]{64}', lead['sha256']) or checksum(parent.read_bytes()) != lead['sha256']:
            raise ValueError('Boletín padre alterado')
        for url in lead.get('external_links_for_provenance_review', []):
            public_tenant_url(url)
            links.setdefault(url, []).append({'bulletin_sha256': lead['sha256'], 'physical_page': lead['physical_page']})
    if len(links) > 6:
        raise ValueError('Seleccionar como máximo seis enlaces de almacenamiento por lote')
    ledger = root / 'storage-acquisitions.jsonl'
    previous = {}
    if ledger.exists():
        for line in ledger.read_text(encoding='utf-8').splitlines():
            record = json.loads(line)
            previous[record['requested_url']] = record
    records, errors = [], []
    for url, provenance in links.items():
        try:
            if url in previous:
                record = previous[url]
                read_cached(root, record)
                records.append({**record, 'reused': True})
                continue
            opener = build_opener(PublicRedirects(), HTTPCookieProcessor(CookieJar()))
            with opener.open(Request(url, headers={'Accept-Encoding': 'identity'}), timeout=25) as response:
                parts = public_tenant_url(response.url)
                body = response.read(8*1024*1024+1)
                if len(body) > 8*1024*1024:
                    raise ValueError('Visor mayor del límite')
                viewer_sha = store(root, body)
                paths = parse_qs(parts.query).get('id', [])
                if len(paths) != 1 or not paths[0].startswith(PREFIX+'Documents/'):
                    raise ValueError('Visor sin ruta documental judicial comprobable')
                observed_path = paths[0]
            downloads = observed_downloads(body.decode('utf-8', errors='replace'))
            with opener.open(Request(downloads[0], headers={'Accept-Encoding': 'identity'}), timeout=25) as response:
                public_tenant_url(response.url)
                pdf = response.read(MAX_BYTES+1)
                if len(pdf) > MAX_BYTES or not pdf.startswith(b'%PDF'):
                    raise ValueError('Respuesta sin PDF público dentro del límite')
            record = {'requested_url': url, 'provenance': provenance, 'viewer_sha256': viewer_sha,
                      'observed_file_path': observed_path, 'download_url_sha256': checksum(downloads[0].encode()),
                      'sha256': store(root, pdf), 'bytes': len(pdf), 'media_type': 'application/pdf',
                      'acquired_at': stamp(), 'credentials_used': False, 'training_label': None}
            with ledger.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False)+'\n')
            records.append({**record, 'reused': False})
        except (OSError, ValueError, HTTPError) as exc:
            errors.append({'requested_url': url, 'provenance': provenance,
                           'error_type': type(exc).__name__, 'http_status': getattr(exc, 'code', None)})
    report = {'created_at': stamp(), 'sources': records, 'errors': errors,
              'resolver_sha256': checksum(Path(__file__).read_bytes()), 'training_labels_created': 0,
              'scope': 'Documentos públicos enlazados por el Tribunal; contenido, condena, firmeza y vínculo SECOP pendientes de revisión.'}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--index', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = resolve(args.root, json.loads(args.index.read_text(encoding='utf-8')), args.output)
    print(json.dumps({'documents': len(report['sources']), 'errors': len(report['errors']), 'training_labels_created': 0}))
    return bool(report['errors'])


if __name__ == '__main__':
    raise SystemExit(main())
