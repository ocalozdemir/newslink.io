#!/usr/bin/env python3
"""Read public T24 articles into temporary summary input; never publish article text."""
import argparse
import concurrent.futures
import json
import re
import sys
from html.parser import HTMLParser
from fetch_news import ROOT, collect, download, timestamp

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.depth = 0; self.active = False; self.hidden = 0
        self.parts = []; self.meta = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('property') or attrs.get('name')] = attrs.get('content')
        if tag == 'div':
            if attrs.get('id') == 'story-content-wrapper': self.active = True; self.depth = 1
            elif self.active: self.depth += 1
        if self.active and tag in ('script', 'style'): self.hidden += 1
        if self.active and tag in ('p', 'h2', 'h3', 'li'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if self.active and tag == 'div':
            self.depth -= 1
            if self.depth == 0: self.active = False
        if self.active and tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
    def handle_data(self, value):
        if self.active and not self.hidden: self.parts.append(value)

def article_input(item):
    try:
        parser = ArticleParser(); parser.feed(download(item['url']).decode('utf-8', errors='replace'))
        text = '\n'.join(re.sub(r'\s+', ' ', p).strip() for p in ''.join(parser.parts).split('\n') if p.strip())
        text = re.sub(r'BU HABERİ.*?Üye girişi yapın', '', text, flags=re.S)
        if len(text) < 200: raise ValueError('Okunabilir haber içeriği bulunamadı')
        return {'url': item['url'], 'title': item['title'],
                'published_at': timestamp(parser.meta.get('article:published_time')),
                'text': text[:14000]}
    except Exception as exc:
        return {'url': item['url'], 'title': item['title'], 'error': type(exc).__name__}

def main():
    args = argparse.ArgumentParser(); args.add_argument('--limit', type=int, default=20)
    opts = args.parse_args()
    source = next(s for s in json.loads((ROOT / 'sources.json').read_text()) if s['id'] == 't24')
    existing = json.loads((ROOT / 'summaries.json').read_text())['articles'] if (ROOT / 'summaries.json').exists() else {}
    items, status, error = collect(source)
    if status in ('error', 'fallback'):
        print(json.dumps({'error': 'T24 ana kaynak haberleri okunamadı', 'items': []}, ensure_ascii=False)); return 1
    missing = [i for i in items if i['url'] not in existing][:max(1, min(opts.limit, 50))]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        result = list(pool.map(article_input, missing))
    print(json.dumps({'items': result}, ensure_ascii=False))
    return 0

if __name__ == '__main__': sys.exit(main())
