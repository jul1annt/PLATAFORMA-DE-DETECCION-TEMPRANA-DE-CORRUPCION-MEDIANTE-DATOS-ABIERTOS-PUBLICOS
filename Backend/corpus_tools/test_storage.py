import json
import unittest
from .storage import observed_downloads, public_tenant_url, PublicRedirects, PREFIX


BASE = 'https://etbcsj-my.sharepoint.com'
DOWNLOAD = BASE + PREFIX + '_layouts/15/download.aspx?UniqueId=example&Translate=false'


class PublicStorageTests(unittest.TestCase):
    def test_only_observed_json_download_url(self):
        html = 'download.aspx is mentioned but is not a URL; ' + json.dumps(DOWNLOAD)
        self.assertEqual(observed_downloads(html), [DOWNLOAD])

    def test_unicode_escaped_slashes_are_decoded(self):
        self.assertEqual(observed_downloads(json.dumps(DOWNLOAD).replace('/', r'\u002f')), [DOWNLOAD])

    def test_no_download_endpoint_is_invented(self):
        with self.assertRaises(ValueError):
            observed_downloads('<title>OneDrive</title>')

    def test_multiple_document_ids_require_manual_review(self):
        html = json.dumps(DOWNLOAD) + json.dumps(DOWNLOAD.replace('example', 'other'))
        with self.assertRaises(ValueError):
            observed_downloads(html)

    def test_foreign_tenant_download_is_not_selected(self):
        with self.assertRaises(ValueError):
            observed_downloads(json.dumps(DOWNLOAD.replace('etbcsj-my', 'other')))

    def test_only_expected_judicial_download_path(self):
        with self.assertRaises(ValueError):
            observed_downloads(json.dumps(DOWNLOAD.replace(PREFIX, '/personal/unrelated/')))

    def test_authentication_and_credentials_are_refused(self):
        for url in (BASE+'/_layouts/15/Authenticate.aspx', BASE+'/AccessDenied.aspx',
                    BASE+'/login', 'https://person:password@etbcsj-my.sharepoint.com/a',
                    'http://etbcsj-my.sharepoint.com/a'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                public_tenant_url(url)

    def test_redirect_to_login_host_is_not_followed(self):
        with self.assertRaises(ValueError):
            PublicRedirects().redirect_request(None, None, 302, '', {}, 'https://login.microsoftonline.com/')


if __name__ == '__main__':
    unittest.main()
