import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from .acquire import acquire, Links, official_url, OfficialRedirects


URL = 'https://www.ramajudicial.gov.co/documents/example'
CATALOG = {'sources': [{'id': 'test-source', 'kind': 'BOLETIN', 'url': URL}]}


class AcquisitionTests(unittest.TestCase):
    def test_selected_institutional_document_hosts_are_explicit(self):
        for host in ('www.ani.gov.co', 'ani.gov.co', 'wwwold.ani.gov.co',
                     'www.consejodeestado.gov.co', 'consejodeestado.gov.co'):
            with self.subTest(host=host):
                url = 'https://' + host + '/sites/default/files/original.pdf'
                self.assertEqual(official_url(url), url)
        for host in ('www.ani.gov.co.example.com', 'unreviewed.ani.gov.co',
                     'www.consejodeestado.gov.co.example.com', 'unreviewed.consejodeestado.gov.co'):
            with self.subTest(host=host), self.assertRaises(ValueError):
                official_url('https://' + host + '/original.pdf')

    def test_url_rejects_credentials_nonofficial_http_and_ports(self):
        for url in ('http://www.ramajudicial.gov.co/a', 'https://localhost/a',
                    'https://www.ramajudicial.gov.co.evil.test/a',
                    'https://user:pass@www.ramajudicial.gov.co/a',
                    'https://www.ramajudicial.gov.co:444/a'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                official_url(url)

    def test_fragment_is_removed(self):
        self.assertEqual(official_url(URL+'#page=10'), URL)

    def test_redirect_validated_before_following(self):
        with self.assertRaises(ValueError):
            OfficialRedirects().redirect_request(None, None, 302, '', {}, 'https://localhost/')

    def test_only_selected_official_links_are_extracted(self):
        parser = Links(URL)
        parser.feed('<a href="/documents/a#x">a</a><iframe src="/documents/b"></iframe>'
                    '<a href="https://example.com/x">x</a><script src="/code.js"></script>')
        self.assertEqual(parser.links, {'https://www.ramajudicial.gov.co/documents/a',
                                       'https://www.ramajudicial.gov.co/documents/b'})

    @patch('corpus_tools.acquire.time.sleep')
    def test_incremental_cache_avoids_refetch_and_never_labels(self, _sleep):
        calls=[]
        def fetch(url):
            calls.append(url)
            return b'%PDF-example', 'application/pdf', url
        with tempfile.TemporaryDirectory() as folder:
            first,_ = acquire(CATALOG, folder, fetcher=fetch)
            second,_ = acquire(CATALOG, folder, fetcher=fetch)
            self.assertEqual(calls,[URL])
            self.assertTrue(second['sources'][0]['reused'])
            self.assertIsNone(first['sources'][0]['training_label'])
            self.assertEqual(second['training_labels_created'],0)
            self.assertEqual(len((Path(folder)/'acquisitions.jsonl').read_text().splitlines()),1)

    @patch('corpus_tools.acquire.time.sleep')
    def test_corrupt_cache_is_reported_without_network_replacement(self, _sleep):
        with tempfile.TemporaryDirectory() as folder:
            first,_ = acquire(CATALOG, folder, fetcher=lambda url:(b'%PDF-a','application/pdf',url))
            target=Path(folder)/'objects'/first['sources'][0]['sha256']
            target.write_bytes(b'changed')
            report,_=acquire(CATALOG,folder,fetcher=lambda url:self.fail('No automatic refetch'))
            self.assertEqual(len(report['errors']),1)
            self.assertEqual(target.read_bytes(),b'changed')

    @patch('corpus_tools.acquire.time.sleep')
    def test_refresh_preserves_old_content(self, _sleep):
        with tempfile.TemporaryDirectory() as folder:
            first,_=acquire(CATALOG,folder,fetcher=lambda url:(b'%PDF-a','application/pdf',url))
            second,_=acquire(CATALOG,folder,refresh=True,fetcher=lambda url:(b'%PDF-b','application/pdf',url))
            self.assertNotEqual(first['sources'][0]['sha256'],second['sources'][0]['sha256'])
            self.assertEqual(len(list((Path(folder)/'objects').iterdir())),2)
            self.assertEqual(len((Path(folder)/'acquisitions.jsonl').read_text().splitlines()),2)

    def test_duplicate_sources_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as folder,self.assertRaises(ValueError):
            acquire({'sources':CATALOG['sources']*2},folder,fetcher=lambda url:self.fail('No network'))

    def test_malformed_catalog_rejected_before_network_and_filesystem_changes(self):
        malformed = [None, [], {}, {'sources': None}, {'sources': {}}, {'sources': []},
                     {'sources': [None]}, {'sources': ['not a source']},
                     {'sources': CATALOG['sources'] * 26}]
        for key in ('id', 'kind', 'url'):
            for value in (None, '', '  ', 123, [], {}):
                item = dict(CATALOG['sources'][0]); item[key] = value
                malformed.append({'sources': [item]})
            item = dict(CATALOG['sources'][0]); del item[key]
            malformed.append({'sources': [item]})
        for catalog in malformed:
            with self.subTest(catalog=catalog), tempfile.TemporaryDirectory() as folder:
                root = Path(folder) / 'not-created'
                with self.assertRaises(ValueError):
                    acquire(catalog, root, fetcher=lambda url:self.fail('No network'))
                self.assertFalse(root.exists())

    def test_invalid_later_source_cannot_leave_an_unreported_partial_acquisition(self):
        later = {'id': 'later', 'url': URL + '/second'}  # Missing required kind.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'not-created'
            with self.assertRaises(ValueError):
                acquire({'sources': [CATALOG['sources'][0], later]}, root,
                        fetcher=lambda url:self.fail('No source may be fetched'))
            self.assertFalse(root.exists())


if __name__=='__main__':
    unittest.main()
