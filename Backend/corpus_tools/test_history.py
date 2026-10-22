import io
import json
import unittest
from unittest.mock import patch
from pathlib import Path
import zlib
import zipfile
from .remote_zip import HistoricalArchive
from .scan_history import scan_deflate, run, validate_member, MAX_ARCHIVE_UNCOMPRESSED


def compressed(body):
    encoder=zlib.compressobj(wbits=-15)
    return encoder.compress(body)+encoder.flush()


def record(number='362', name='ARAUCA - GOBERNACIÓN', **extra):
    return {'Release': {'ocid':'official-example','id':'release-example','buyer':{'id':'official-buyer','name':name},
                        'tender':{'title':'Proceso sin número buscado'},'contracts':[{'id':number,'title':'Suministro'}],**extra}}


class StreamHistoryTests(unittest.TestCase):
    def scan(self, rows, numbers=None, **kwargs):
        body=('\n'.join(json.dumps(row,ensure_ascii=False) for row in rows)+'\n').encode('cp1252')
        packed=compressed(body)
        chunks=[packed[i:i+13] for i in range(0,len(packed),13)]
        return scan_deflate(chunks,len(body),zlib.crc32(body),numbers or ['362'],**kwargs)

    def test_carries_line_boundaries_and_cp1252_across_chunks(self):
        result=self.scan([record(),record('497')])
        self.assertEqual(result['lines_scanned'],2)
        self.assertEqual(result['candidate_lines'],1)
        self.assertEqual(result['retained_candidates'][0]['ocid'],'official-example')
        self.assertIsNone(result['retained_candidates'][0]['training_label'])

    def test_phone_digits_do_not_match_contract(self):
        result=self.scan([record('497', parties=[{'telephone':'362'}])])
        self.assertEqual(result['candidate_lines'],0)

    def test_hospital_and_embedded_number_not_same_contract(self):
        result=self.scan([record(name='ARAUCA - HOSPITAL'),record('1362')])
        self.assertEqual(result['candidate_lines'],0)

    def test_capped_storage_keeps_total_count(self):
        result=self.scan([record(),record()],max_matches=1)
        self.assertEqual(result['candidate_lines'],2)
        self.assertEqual(len(result['retained_candidates']),1)
        self.assertTrue(result['candidate_storage_truncated'])

    def test_wrong_crc_cannot_complete(self):
        body=b'{}\n'
        with self.assertRaises(ValueError):
            scan_deflate([compressed(body)],len(body),0,['362'])

    def test_truncated_stream_cannot_complete(self):
        body=b'{}\n'
        with self.assertRaises(ValueError):
            scan_deflate([compressed(body)[:-1]],len(body),zlib.crc32(body),['362'])

    def test_profiles_select_buyer_without_cross_entity_matches(self):
        rows=[record(name='PUTUMAYO - GOBERNACIÓN'),record(name='GUAINÍA - GOBERNACIÓN'),record()]
        for profile, expected in [('gobernacion-putumayo','PUTUMAYO'),('gobernacion-guainia','GUAINÍA'),('gobernacion-arauca','ARAUCA')]:
            with self.subTest(profile=profile):
                result=self.scan(rows,buyer_profile=profile)
                self.assertEqual(result['buyer_profile'],profile)
                self.assertEqual(result['entity_lines'],1)
                self.assertEqual(result['candidate_lines'],1)
                self.assertIn(expected,result['retained_candidates'][0]['buyer']['name'])

    def test_default_profile_preserves_arauca_scope(self):
        result=self.scan([record(name='PUTUMAYO - GOBERNACIÓN'),record(name='GUAINÍA - GOBERNACIÓN')])
        self.assertEqual(result['entity_lines'],0)
        self.assertEqual(result['candidate_lines'],0)

    def test_guainia_escaped_unicode_and_unaccented_names(self):
        rows=[record(name='GUAINÍA - GOBERNACIÓN'),record(name='GUAINIA - GOBERNACION')]
        body=('\n'.join(json.dumps(row,ensure_ascii=True) for row in rows)+'\n').encode('ascii')
        result=scan_deflate([compressed(body)],len(body),zlib.crc32(body),['362'],buyer_profile='gobernacion-guainia')
        self.assertEqual(result['entity_lines'],2)
        self.assertEqual(result['candidate_lines'],2)

    def test_entity_in_object_does_not_replace_buyer_name(self):
        row=record(name='GUAINÍA - ALCALDÍA INÍRIDA',tender={'title':'Gobernación contrato 362'})
        result=self.scan([row],buyer_profile='gobernacion-guainia')
        self.assertEqual(result['entity_lines'],0)
        self.assertEqual(result['candidate_lines'],0)

    def test_new_profile_keeps_number_boundaries_and_telephone_exclusion(self):
        result=self.scan([record('1362',name='PUTUMAYO - GOBERNACIÓN'),record('497',name='PUTUMAYO - GOBERNACIÓN',parties=[{'telephone':'362'}])],buyer_profile='gobernacion-putumayo')
        self.assertEqual(result['entity_lines'],2)
        self.assertEqual(result['candidate_lines'],0)

    def test_invalid_profile_rejected_before_stream_or_network(self):
        def forbidden_chunks():
            self.fail('An invalid profile must not consume the stream')
            yield b''
        with self.assertRaisesRegex(ValueError,'Perfil'):
            scan_deflate(forbidden_chunks(),0,0,['362'],buyer_profile='unknown')
        with patch('corpus_tools.scan_history.HistoricalArchive') as archive:
            with self.assertRaisesRegex(ValueError,'Perfil'):
                run(2013,['362'],Path('unused'),Path('unused.json'),buyer_profile='unknown')
            archive.assert_not_called()

    def test_new_profile_still_requires_complete_crc(self):
        body=(json.dumps(record(name='GUAINÍA - GOBERNACIÓN'),ensure_ascii=False)+'\n').encode('cp1252')
        with self.assertRaises(ValueError):
            scan_deflate([compressed(body)],len(body),zlib.crc32(body)^1,['362'],buyer_profile='gobernacion-guainia')


class Response(io.BytesIO):
    def __init__(self,body,status,headers):
        super().__init__(body);self.status=status;self.headers=headers


class Opener:
    def __init__(self,*,ignore_range=False,changed=False,short=False):
        self.ignore_range=ignore_range;self.changed=changed;self.short=short
        self.headers={'Content-Length':'10','Accept-Ranges':'bytes','ETag':'generation-one','Last-Modified':'fixed'}
        self.calls=[]

    def open(self,request,timeout):
        self.calls.append(request)
        if request.get_method()=='HEAD':
            return Response(b'',200,self.headers)
        assert request.get_header('Range')=='bytes=2-5'
        headers={**self.headers,'Content-Range':'bytes 2-5/10'}
        if self.changed:headers['ETag']='generation-two'
        return Response(b'234' if self.short else b'2345',200 if self.ignore_range else 206,headers)


class RangeHistoryTests(unittest.TestCase):
    def test_reviewed_streaming_member_limit(self):
        info=zipfile.ZipInfo('SI2015.json')
        info.compress_type=8
        # Size observed in the official directory, followed by the exact cap.
        for size in (3361249396,MAX_ARCHIVE_UNCOMPRESSED):
            info.file_size=size
            validate_member(info,2015)
        for size in (-1,MAX_ARCHIVE_UNCOMPRESSED+1):
            info.file_size=size
            with self.assertRaises(ValueError):validate_member(info,2015)

    def test_unreviewed_member_shapes_rejected(self):
        for name,compression,flags in [('other.json',8,0),('SI2015.json',0,0),('SI2015.json',8,1)]:
            info=zipfile.ZipInfo(name);info.compress_type=compression;info.flag_bits=flags;info.file_size=10
            with self.subTest(name=name,compression=compression,flags=flags):
                with self.assertRaises(ValueError):validate_member(info,2015)

    def test_reads_only_requested_range(self):
        opener=Opener()
        with HistoricalArchive(2012,opener=opener) as source:
            source.seek(2);self.assertEqual(source.read(4),b'2345')
            self.assertEqual(source.network_bytes,4)

    def test_ignored_range_rejected(self):
        with HistoricalArchive(2012,opener=Opener(ignore_range=True)) as source:
            source.seek(2)
            with self.assertRaises(ValueError):source.read(4)
            self.assertEqual(source.network_bytes,0)

    def test_changed_generation_rejected(self):
        with HistoricalArchive(2012,opener=Opener(changed=True)) as source:
            source.seek(2)
            with self.assertRaises(ValueError):source.read(4)

    def test_incomplete_range_rejected(self):
        with HistoricalArchive(2012,opener=Opener(short=True)) as source:
            source.seek(2)
            with self.assertRaises(ValueError):source.read(4)

    def test_unlisted_year_rejected(self):
        with self.assertRaises(ValueError):HistoricalArchive(2020,opener=Opener())


if __name__=='__main__':
    unittest.main()
