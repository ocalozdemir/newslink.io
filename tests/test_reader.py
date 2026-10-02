import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from summary_inputs import ArticleParser

class ReaderDataTests(unittest.TestCase):
    def test_article_parser_excludes_navigation_and_scripts(self):
        p = ArticleParser()
        p.feed('<nav>Navigation</nav><div id="story-content-wrapper"><p>News</p><div><p>Details</p></div><script>unsafe()</script></div><footer>Footer</footer>')
        self.assertIn('News', ''.join(p.parts))
        self.assertIn('Details', ''.join(p.parts))
        self.assertNotIn('Navigation', ''.join(p.parts))
        self.assertNotIn('unsafe()', ''.join(p.parts))
        self.assertNotIn('Footer', ''.join(p.parts))

    def test_summaries_are_paragraphs_without_full_article_fields(self):
        d = json.loads((ROOT / 'summaries.json').read_text(encoding='utf-8'))
        self.assertTrue(d['articles'])
        for url, item in d['articles'].items():
            self.assertTrue(url.startswith('https://t24.com.tr/haber/'))
            self.assertEqual(item['source'], 't24')
            self.assertGreaterEqual(len(item['paragraphs']), 1)
            self.assertLessEqual(len(' '.join(item['paragraphs']).split()), 190)
            self.assertTrue(all(isinstance(p, str) and p.strip() for p in item['paragraphs']))
            self.assertNotIn('text', item)
            self.assertNotIn('articleBody', item)

if __name__ == '__main__': unittest.main()
