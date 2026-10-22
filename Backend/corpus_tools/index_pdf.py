"""Extract page-located research leads with optional, separate PDF tooling.

Text terms only prioritize manual review. No labels, names-as-predictors, dates
of finality or SECOP identities are inferred by this process.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit, urlunsplit
from .acquire import official_url, read_cached, stamp, checksum

TERMS = re.compile(r'peculado|cohecho|concusi[oó]n|inter[eé]s\s+indebido|contrato\s+sin\s+cumplimiento|celebraci[oó]n\s+indebida\s+de\s+contratos|SECOP|UNGRD|MinTIC|carrotanques|centros\s+poblados', re.I)


def index(root, acquisition, output):
    import pypdf
    if pypdf.__version__ != '6.10.0':
        raise ValueError('Usar la versión PDF fijada, separada de API y modelos')
    leads, documents = [], []
    for source in acquisition['sources']:
        if source['media_type'] != 'application/pdf':
            continue
        # A content hash is a document key, never an inferred judicial case ID.
        source_id = source.get('source_id', 'sha256:' + source['sha256'])
        base_url = source.get('final_url', source['requested_url'])
        body = read_cached(root, source)
        from io import BytesIO
        reader = pypdf.PdfReader(BytesIO(body), strict=True)
        if reader.is_encrypted:
            raise ValueError('No se procesa automáticamente un documento cifrado')
        if len(reader.pages) > 1000:
            raise ValueError('Revisar el alcance de documentos mayores de 1000 páginas')
        hits = 0
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            matches = list(TERMS.finditer(text))
            if not matches:
                continue
            hits += 1
            links, external_links = set(), set()
            for annotation in page.get('/Annots', []):
                item = annotation.get_object()
                action = item.get('/A')
                if action:
                    action = action.get_object()
                    uri = action.get('/URI')
                    if uri:
                        try:
                            links.add(official_url(urljoin(base_url, str(uri))))
                        except ValueError:
                            # Preserve institutional storage links for manual
                            # provenance/access review; never fetch them here.
                            parts = urlsplit(urljoin(base_url, str(uri)))
                            if (parts.scheme == 'https' and parts.hostname and not parts.username
                                    and not parts.password and parts.port in (None, 443)):
                                external_links.add(urlunsplit((*parts[:4], '')))
            leads.append({'source_id': source_id, 'sha256': source['sha256'],
                          'physical_page': number, 'matched_terms': sorted({m.group().lower() for m in matches}),
                          'context': [text[max(0,m.start()-160):m.end()+260] for m in matches[:8]],
                          'official_links_on_page': sorted(links),
                          'external_links_for_provenance_review': sorted(external_links),
                          'review_pages': list(range(max(1, number-1), min(len(reader.pages), number+1)+1)),
                          'review_status': 'PENDIENTE_REVISION',
                          'training_label': None})
        documents.append({'source_id': source_id, 'sha256': source['sha256'],
                          'pages': len(reader.pages), 'pages_prioritized': hits})
    report = {'created_at': stamp(), 'documents': documents, 'leads': leads,
              'tool_versions': {'pypdf': importlib.metadata.version('pypdf')},
              'indexer_sha256': checksum(Path(__file__).read_bytes()),
              'training_labels_created': 0,
              'scope': 'Texto y enlaces por página para revisión; una coincidencia no identifica una condena ni un expediente independiente.'}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--acquisition', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = index(args.root, json.loads(args.acquisition.read_text(encoding='utf-8')), args.output)
    print(json.dumps({'documents': len(report['documents']), 'leads': len(report['leads']), 'training_labels_created': 0}))


if __name__ == '__main__':
    main()
