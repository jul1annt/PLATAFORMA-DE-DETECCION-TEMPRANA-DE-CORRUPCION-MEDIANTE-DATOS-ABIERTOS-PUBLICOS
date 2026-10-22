"""Acquire fixed official discovery documents. Acquisition never creates labels."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import requests

DOCUMENTS={
    'sp968-2024.pdf':'https://cortesuprema.gov.co/corte/wp-content/uploads/relatorias/pe/b1may2024/SP968-2024%2865559%29.pdf',
    'sep097-2024.pdf':'https://archivodigitalapi.cortesuprema.gov.co/share/2024/10/Sentencias/51414%20SEP%20097-2024%20DEL%2016-10-2024.pdf',
    'sep060-2025.pdf':'https://archivodigitalapi.cortesuprema.gov.co/share/2025/5/Sentencias/SEP-060-2025%20-%2012-05-2025%20RAD00641.pdf',
    'sep027-2026.pdf':'https://archivodigitalapi.cortesuprema.gov.co/share/2026/3/Sentencias/00158SEP02720260304.pdf',
    'secop-dictionary.json':'https://www.datos.gov.co/api/views/p6dx-8zbt.json',
    'centros-poblados-auto-victimas-20230217.pdf':'https://www.ramajudicial.gov.co/documents/2233304/f3ca3dcf-a687-3a3a-d026-c812a257ecfb',
    'sep077-2023.pdf':'https://www.cortesuprema.gov.co/corte/wp-content/uploads/prensa/SEP00077-2023.pdf',
    'antioquia-estado031-necocli-086-2020.pdf':'https://www.ramajudicial.gov.co/documents/14899929/137980794/EstadoElectronico%2B031%2BSalaPenalTribunalSuperiorAntioquia.pdf/695943a5-0550-280f-6b04-c6d2460d3001',
}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]/'var/risk/evidence')
    args=parser.parse_args();root=args.root.resolve();root.mkdir(parents=True,exist_ok=True)
    records=[]
    with requests.Session() as session:
        for name,url in DOCUMENTS.items():
            path=root/name
            reused=path.exists()
            if not reused:
                with session.get(url,timeout=(10,40),stream=True,allow_redirects=False) as response:
                    response.raise_for_status()
                    if response.status_code!=200:
                        raise ValueError('Respuesta inesperada; revisar URL oficial sin seguir redirecciones automáticamente')
                    pieces=[];size=0
                    for piece in response.iter_content(65536):
                        size+=len(piece)
                        if size>32*1024*1024:
                            raise ValueError('Documento mayor de 32 MiB')
                        pieces.append(piece)
                    body=b''.join(pieces)
                    if name.endswith('.pdf') and not body.startswith(b'%PDF'):
                        raise ValueError('El contenido no es PDF')
                    with path.open('xb') as output:
                        output.write(body)
            with path.open('rb') as source:
                sha=hashlib.file_digest(source,'sha256').hexdigest()
            records.append({'file':name,'url':url,'sha256':sha,'bytes':path.stat().st_size,'reused_local_file':reused})
    output=root/('acquisition-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    with output.open('x',encoding='utf-8') as out:
        json.dump({'documents':records,'training_labels_created':0},out,indent=2)
    print(json.dumps({'documents':len(records),'training_labels_created':0}))


if __name__=='__main__':
    main()
