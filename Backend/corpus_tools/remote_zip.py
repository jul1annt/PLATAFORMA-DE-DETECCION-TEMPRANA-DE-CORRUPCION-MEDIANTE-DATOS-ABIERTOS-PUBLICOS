"""Read selected members of fixed official historical archives through ranges.

No full ZIP download, extraction to filesystem or change to published SECOP data.
Every response is bounded and tied to the archive generation observed by HEAD.
"""
import argparse
import io
import json
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
import zipfile
from .acquire import stamp, checksum

ROOT = 'https://apiocds.colombiacompra.gov.co/ArchivosSECOP/Archivos/'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class HistoricalArchive(io.RawIOBase):
    def __init__(self, year, *, opener=None):
        super().__init__()
        if type(year) is not int or not 2011 <= year <= 2019:
            raise ValueError('Seleccionar un archivo anual SECOP I enlazado por CCE')
        self.url = ROOT + f'SI{year}.zip'
        self.opener = opener or build_opener(NoRedirect())
        with self.opener.open(Request(self.url, method='HEAD'), timeout=20) as response:
            if response.status != 200 or response.headers.get('Accept-Ranges') != 'bytes':
                raise ValueError('Archivo sin soporte explícito de rangos')
            self.length = int(response.headers['Content-Length'])
            self.etag = response.headers.get('ETag')
            self.modified = response.headers.get('Last-Modified')
            if not self.etag and not self.modified:
                raise ValueError('Archivo sin identificador de generación')
        self.position = 0
        self.network_bytes = 0
        self.requests = []

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        bases = {0: 0, 1: self.position, 2: self.length}
        if whence not in bases or bases[whence]+offset < 0:
            raise ValueError('Posición de archivo inválida')
        self.position = bases[whence]+offset
        return self.position

    def read(self, size=-1):
        if self.position >= self.length or size == 0:
            return b''
        size = min(self.length-self.position, size if size >= 0 else self.length-self.position)
        if size > 8*1024*1024:
            raise ValueError('Lectura individual mayor de 8 MiB; seleccionar un miembro más pequeño')
        start, end = self.position, self.position+size-1
        request = Request(self.url, headers={'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity'})
        with self.opener.open(request, timeout=25) as response:
            if (response.status != 206
                    or response.headers.get('Content-Range') != f'bytes {start}-{end}/{self.length}'):
                raise ValueError('El servidor no respetó el rango; no se descarga el archivo completo')
            if ((self.etag and response.headers.get('ETag') != self.etag)
                    or (self.modified and response.headers.get('Last-Modified') != self.modified)):
                raise ValueError('Cambió la generación del archivo histórico')
            body = response.read(size+1)
            if len(body) != size:
                raise ValueError('Rango incompleto o excesivo')
        self.network_bytes += len(body)
        self.requests.append({'start': start, 'end': end, 'sha256': checksum(body)})
        self.position += size
        return body

    def manifest(self):
        return {'url': self.url, 'archive_bytes': self.length, 'etag': self.etag,
                'last_modified': self.modified, 'network_bytes': self.network_bytes, 'ranges': self.requests}


def inspect(year):
    with HistoricalArchive(year) as source:
        with zipfile.ZipFile(source) as archive:
            members = [{'name': info.filename, 'bytes': info.file_size, 'compressed_bytes': info.compress_size,
                        'compression': info.compress_type, 'encrypted': bool(info.flag_bits & 1)}
                       for info in archive.infolist()]
        return {'checked_at': stamp(), **source.manifest(), 'members': members,
                'scope': 'Archive directory only; publication/award history and case linkage not verified'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.year)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
    print(json.dumps({'members': len(result['members']), 'archive_bytes': result['archive_bytes'],
                      'network_bytes': result['network_bytes'], 'sample': result['members'][:10]}))


if __name__ == '__main__':
    main()
