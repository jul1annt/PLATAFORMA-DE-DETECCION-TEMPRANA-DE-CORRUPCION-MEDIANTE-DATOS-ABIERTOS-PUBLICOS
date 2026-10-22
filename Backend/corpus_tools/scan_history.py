"""Bounded streaming search of one archived SECOP I JSON-lines member.

Only candidate lines are retained. Identifiers are preserved as published and
never assigned to a training case automatically. CRC, size and generation must
all pass before the run is described as complete.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import unicodedata
from urllib.request import Request
import zipfile
import zlib
from .remote_zip import HistoricalArchive
from .acquire import checksum, stamp

BLOCK = 256 * 1024
OUTPUT_BLOCK = 1024 * 1024
MAX_LINE = 2 * 1024 * 1024
# The reviewed 2015 member is about 3.36 GB uncompressed. It is consumed in
# bounded blocks, never materialized as a file or a complete byte string.
MAX_ARCHIVE_UNCOMPRESSED = 4 * 1024**3
DEFAULT_BUYER_PROFILE = 'gobernacion-arauca'
# Explicit discovery scopes. Stems stay ASCII in both cp1252 JSON and escaped
# Unicode JSON; the buyer name is decoded and verified again below.
BUYER_PROFILES = {
    'gobernacion-arauca': ('ARAUCA', 'GOBERN'),
    'gobernacion-putumayo': ('PUTUMAYO', 'GOBERN'),
    'gobernacion-guainia': ('GUAIN', 'GOBERN'),
}


def buyer_terms(profile):
    if profile not in BUYER_PROFILES:
        raise ValueError('Perfil de entidad no revisado')
    return BUYER_PROFILES[profile]


def validate_member(info, year):
    if info.filename != f'SI{year}.json':
        raise ValueError('Miembro distinto del archivo anual revisado')
    if (info.flag_bits & 1 or info.compress_type != 8
            or info.file_size < 0 or info.file_size > MAX_ARCHIVE_UNCOMPRESSED):
        raise ValueError('Perfil de compresión fuera de alcance')


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.upper()) if not unicodedata.combining(c))


def scan_deflate(chunks, expected_bytes, expected_crc, numbers, *, max_matches=50, retain=None,
                 buyer_profile=DEFAULT_BUYER_PROFILE):
    entity_terms = buyer_terms(buyer_profile)
    decoder = zlib.decompressobj(-15)
    crc = count = lines = selected = entity_lines = 0
    pending_line = bytearray()
    matches, entity_samples = [], []
    compressed_sha = hashlib.sha256()
    patterns = [re.compile(r'(?<!\d)'+re.escape(number)+r'(?!\d)') for number in numbers]
    if not patterns or any(not re.fullmatch(r'\d{1,8}', number) for number in numbers):
        raise ValueError('Indicar números contractuales explícitos')

    def line(raw):
        nonlocal lines, selected, entity_lines
        lines += 1
        # Cheap byte filter first. Unicode matching below verifies entity and
        # contract fields; digits in a telephone or address cannot create a hit.
        upper_raw = raw.upper()
        if any(term.encode('ascii') not in upper_raw for term in entity_terms):
            return
        text = raw.decode('cp1252', errors='strict')
        record = json.loads(text)
        release = record.get('Release')
        if not isinstance(release, dict):
            raise ValueError('Formato distinto del perfil de archivo revisado')
        buyer = release.get('buyer') or {}
        entity = normalize(str(buyer.get('name', '')))
        if any(term not in entity for term in entity_terms):
            return
        entity_lines += 1
        contracts = release.get('contracts') or []
        if len(entity_samples) < 3:
            entity_samples.append({'line': lines, 'ocid': release.get('ocid'),
                                   'release_keys': sorted(release),
                                   'tender': release.get('tender'), 'contracts': contracts})
        fields = [str(contract.get(key, '')) for contract in contracts for key in ('id', 'title')]
        # Tender title is a discovery reference, not necessarily a contract ID.
        fields.append(str((release.get('tender') or {}).get('title', '')))
        matched = sorted({number for number, pattern in zip(numbers, patterns) if any(pattern.search(value) for value in fields)})
        if not matched:
            return
        selected += 1
        if len(matches) >= max_matches:
            return
        sha = checksum(raw)
        if retain:
            retain(sha, raw)
        matches.append({'line': lines, 'raw_line_sha256': sha, 'matched_search_numbers': matched,
                        'ocid': release.get('ocid'), 'release_id': release.get('id'),
                        'release_date_as_published': release.get('date'), 'buyer': buyer,
                        'tender_title': (release.get('tender') or {}).get('title'),
                        'contracts': [{'id': c.get('id'), 'title': c.get('title'), 'dateSigned': c.get('dateSigned')} for c in contracts],
                        'review_status': 'CORRESPONDENCIA_DOCUMENTAL_PENDIENTE', 'training_label': None})

    def output(body):
        nonlocal crc, count
        crc = zlib.crc32(body, crc)
        count += len(body)
        if count > expected_bytes:
            raise ValueError('Tamaño descomprimido mayor del declarado')
        pending_line.extend(body)
        while True:
            end = pending_line.find(b'\n')
            if end < 0:
                break
            raw = bytes(pending_line[:end]).strip()
            del pending_line[:end+1]
            if len(raw) > MAX_LINE:
                raise ValueError('Línea mayor del límite')
            if raw:
                line(raw)
        if len(pending_line) > MAX_LINE:
            raise ValueError('Línea mayor del límite')

    for chunk in chunks:
        compressed_sha.update(chunk)
        remaining = chunk
        while remaining:
            body = decoder.decompress(remaining, OUTPUT_BLOCK)
            remaining = decoder.unconsumed_tail
            output(body)
    output(decoder.flush())
    if pending_line.strip():
        line(bytes(pending_line).strip())
    if not decoder.eof or decoder.unused_data or count != expected_bytes or crc != expected_crc:
        raise ValueError('Integridad CRC, tamaño o fin del miembro ZIP no comprobados')
    return {'uncompressed_bytes': count, 'lines_scanned': lines, 'crc32': crc,
            'compressed_member_sha256': compressed_sha.hexdigest(), 'candidate_lines': selected,
            'retained_candidates': matches, 'candidate_storage_truncated': selected > len(matches),
            'entity_lines': entity_lines, 'entity_samples_for_schema_review': entity_samples,
            'buyer_profile': buyer_profile, 'buyer_terms': list(entity_terms)}


def run(year, numbers, root, report_path, *, buyer_profile=DEFAULT_BUYER_PROFILE):
    entity_terms = buyer_terms(buyer_profile)
    root.mkdir(parents=True, exist_ok=True)
    report = {'started_at': stamp(), 'state': 'STARTED', 'year': year,
              'search_numbers': numbers, 'encoding_profile': 'cp1252-strict-json-lines-Release',
              'buyer_profile': buyer_profile, 'buyer_terms': list(entity_terms),
              'training_labels_created': 0, 'database_accessed': False,
              'scope': 'Candidate search only; dates and IDs do not establish finality or historical feature availability.'}
    with HistoricalArchive(year) as source:
        try:
            with zipfile.ZipFile(source) as archive:
                infos = archive.infolist()
                if len(infos) != 1 or infos[0].filename != f'SI{year}.json':
                    raise ValueError('Directorio distinto del archivo anual revisado')
                info = infos[0]
                validate_member(info, year)
                source.seek(info.header_offset)
                header = source.read(30)
                if header[:4] != b'PK\x03\x04':
                    raise ValueError('Cabecera local inválida')
                name_size, extra_size = struct.unpack_from('<HH', header, 26)
                start = info.header_offset + 30 + name_size + extra_size
            end = start + info.compress_size - 1
            request = Request(source.url, headers={'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity'})
            def retain(sha, body):
                target = root / (sha+'.line')
                if target.exists():
                    if checksum(target.read_bytes()) != sha:
                        raise ValueError('Candidato local alterado')
                else:
                    with target.open('xb') as output:
                        output.write(body)
            with source.opener.open(request, timeout=30) as response:
                if (response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{source.length}'
                        or response.headers.get('ETag') != source.etag or response.headers.get('Last-Modified') != source.modified):
                    raise ValueError('Rango o generación del archivo no coincide')
                downloaded = 0
                def chunks():
                    nonlocal downloaded
                    while True:
                        chunk = response.read(min(BLOCK, info.compress_size-downloaded+1))
                        if not chunk:
                            break
                        downloaded += len(chunk)
                        if downloaded > info.compress_size:
                            raise ValueError('Miembro comprimido excede tamaño declarado')
                        yield chunk
                results = scan_deflate(chunks(), info.file_size, info.CRC, numbers, retain=retain,
                                       buyer_profile=buyer_profile)
                if downloaded != info.compress_size:
                    raise ValueError('Lectura comprimida incompleta')
            # Recheck the current generation before accepting results.
            with source.opener.open(Request(source.url, method='HEAD'), timeout=20) as response:
                if (response.status != 200 or response.headers.get('ETag') != source.etag
                        or response.headers.get('Last-Modified') != source.modified
                        or int(response.headers['Content-Length']) != source.length):
                    raise ValueError('El archivo cambió durante la lectura')
            report.update(state='COMPLETE', finished_at=stamp(), **results,
                          archive=source.manifest(), streamed_compressed_bytes=downloaded,
                          full_archive_written_to_disk=False, code_sha256=checksum(Path(__file__).read_bytes()))
        except Exception as exc:
            report.update(state='FAILED', error_type=type(exc).__name__, finished_at=stamp())
            raise
        finally:
            with report_path.open('x', encoding='utf-8') as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--number', action='append', required=True)
    parser.add_argument('--buyer-profile', choices=sorted(BUYER_PROFILES), default=DEFAULT_BUYER_PROFILE)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.year, args.number, args.root, args.output, buyer_profile=args.buyer_profile)
    print(json.dumps({'state': report['state'], 'lines': report['lines_scanned'],
                      'candidate_lines': report['candidate_lines'], 'written_lines': len(report['retained_candidates'])}))


if __name__ == '__main__':
    main()
