import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('fetch_news', Path(__file__).resolve().parents[1] / 'scripts/fetch_news.py')
news = importlib.util.module_from_spec(spec)
spec.loader.exec_module(news)
SOURCE = {'id':'t24', 'name':'T24', 'website':'https://t24.com.tr', 'category':'Gündem', 'domains':['t24.com.tr']}


class CollectorTests(unittest.TestCase):
    def test_rdf_and_missing_dates(self):
        data = news.parse_feed(b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><item><title>Test</title><link>https://t24.com.tr/haber/test</link></item></rdf:RDF>', SOURCE)
        self.assertIsNone(data[0]['published_at'])

    def test_google_rejects_wrong_publisher(self):
        payload = b'<rss><channel><item><title>Test</title><link>https://news.google.com/rss/articles/test</link><source url="https://fake-t24.com.tr">Fake</source></item></channel></rss>'
        with self.assertRaises(ValueError): news.parse_feed(payload, SOURCE, 'google')

    def test_unsafe_link_rejected(self):
        with self.assertRaises(ValueError):
            news.parse_feed(b'<rss><channel><item><title>Test</title><link>javascript:alert(1)</link></item></channel></rss>', SOURCE)

    def test_failure_preserves_cache_and_timestamp(self):
        old = {'source':'t24', 'url':'https://t24.com.tr/haber/test', 'published_at':news.NOW.isoformat(), 'title':'Test'}
        previous = {'items':[old], 'updated_at':'2026-10-01T10:00:00+00:00'}
        data = news.build([SOURCE], previous, lambda _: ([], 'error', 'HTTPError'))
        self.assertEqual(data['items'], [old])
        self.assertEqual(data['sources'][0]['status'], 'cached')
        self.assertEqual(data['updated_at'], previous['updated_at'])

    def test_html_response_not_a_feed(self):
        with self.assertRaises(ValueError): news.parse_feed(b'<html><body>Not Found</body></html>', SOURCE)

    def test_homepage_deduplicates_and_does_not_invent_date(self):
        payload = b'<a href="/haber/test,123"><img src="https://t24.com.tr/test.jpg" alt="A headline long enough"><h4>A headline long enough</h4></a><a href="/haber/test,123"><h3>A headline long enough</h3></a>'
        items = news.parse_homepage(payload, SOURCE)
        self.assertEqual(len(items), 1)
        self.assertIsNone(items[0]['published_at'])
        self.assertEqual(items[0]['url'], 'https://t24.com.tr/haber/test,123')


if __name__ == '__main__': unittest.main()
