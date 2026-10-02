#!/usr/bin/env python3
"""Collect public RSS metadata; never fetch full article bodies."""
import concurrent.futures
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime.now(timezone.utc)
MAX_BYTES = 5_000_000


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
    def handle_data(self, text):
        if not self.hidden: self.parts.append(text)


def clean(value, limit=240):
    parser = TextParser(); parser.feed(value or '')
    text = re.sub(r'\s+', ' ', html.unescape(' '.join(parser.parts))).strip()
    return text if len(text) <= limit else text[:limit].rsplit(' ', 1)[0] + '…'


def url_ok(value):
    parsed = urllib.parse.urlparse(value or '')
    return bool(parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username)


def local(tag):
    return tag.rsplit('}', 1)[-1]


def field(node, names):
    for child in node:
        if local(child.tag) in names and child.text:
            return child.text.strip()
    return ''


def timestamp(value):
    if not value: return None
    try:
        try: dt = parsedate_to_datetime(value)
        except (ValueError, TypeError): dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError): return None


def category(node, source):
    tags = [clean(child.text, 100).casefold() for child in node if local(child.tag) == 'category']
    aliases = {'Ekonomi': ('ekonomi', 'economy', 'finans', 'business', 'para', 'borsa'),
               'Teknoloji': ('teknoloji', 'technology', 'bilim'),
               'Spor': ('spor', 'sport', 'futbol'),
               'Dünya': ('dünya', 'world', 'avrupa', 'europe'),
               'Gündem': ('gündem', 'politika', 'siyaset', 'türkiye')}
    for name, terms in aliases.items():
        if any(any(term in tag for term in terms) for tag in tags): return name
    return source['category']


def parse_feed(payload, source, via='rss'):
    root = ET.fromstring(payload)
    entries = [node for node in root.iter() if local(node.tag) in ('item', 'entry')]
    result = []
    for entry in entries:
        title = clean(field(entry, ('title',)), 350)
        link = field(entry, ('link',))
        if not link:
            for child in entry:
                if local(child.tag) == 'link' and child.get('rel', 'alternate') == 'alternate':
                    link = child.get('href', ''); break
        if not title or not url_ok(link): continue
        if via == 'google':
            publisher = next((c for c in entry if local(c.tag) == 'source'), None)
            host = urllib.parse.urlparse(publisher.get('url', '') if publisher is not None else '').hostname or ''
            if not any(host == d or host.endswith('.' + d) for d in source['domains']): continue
            if publisher is not None and publisher.text:
                suffix = ' - ' + publisher.text.strip()
                if title.endswith(suffix): title = title[:-len(suffix)]
        published = timestamp(field(entry, ('pubDate', 'published', 'date', 'updated')))
        if published and datetime.fromisoformat(published) < NOW - timedelta(days=7): continue
        image = None
        if via == 'rss':
            for child in entry.iter():
                kind = local(child.tag)
                candidate = child.get('url')
                is_image = kind == 'thumbnail' or (kind in ('content','enclosure') and
                           (child.get('type', '').startswith('image/') or child.get('medium') == 'image'))
                if is_image and url_ok(candidate): image = candidate; break
        summary = '' if via == 'google' else clean(field(entry, ('description', 'summary')))
        result.append({'id': hashlib.sha256((source['id'] + link).encode()).hexdigest()[:20],
                       'source': source['id'], 'title': title, 'url': link, 'summary': summary,
                       'image': image, 'category': category(entry, source), 'published_at': published,
                       'first_seen_at': NOW.isoformat(), 'via': via})
    if not result: raise ValueError('Beslemede güncel ve geçerli haber bulunamadı')
    return result[:50]


class HomepageParser(HTMLParser):
    """T24 homepage headlines and links only; publication dates aren't guessed."""
    def __init__(self, source):
        super().__init__(); self.source = source; self.current = None; self.items = {}; self.heading = False
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            link = urllib.parse.urljoin(self.source['website'], attrs.get('href', ''))
            host = urllib.parse.urlparse(link).hostname
            if host in self.source['domains'] and '/haber/' in urllib.parse.urlparse(link).path:
                self.current = {'url':link, 'title':attrs.get('title', ''), 'image':None, 'parts':[]}
        elif self.current is not None:
            if tag in ('h2','h3','h4'): self.heading = True
            if tag == 'img':
                if not self.current['title']: self.current['title'] = attrs.get('alt', '')
                image = attrs.get('src') or attrs.get('data-src')
                if url_ok(image): self.current['image'] = image
    def handle_data(self, value):
        if self.current is not None and self.heading: self.current['parts'].append(value)
    def handle_endtag(self, tag):
        if tag in ('h2','h3','h4'): self.heading = False
        if tag == 'a' and self.current is not None:
            item = self.current; self.current = None; self.heading = False
            title = clean(' '.join(item['parts']) or item['title'], 350)
            if len(title) < 15: return
            if item['url'] in self.items: return
            self.items[item['url']] = {'id':hashlib.sha256((self.source['id'] + item['url']).encode()).hexdigest()[:20],
                'source':self.source['id'], 'title':title, 'url':item['url'], 'image':item['image'], 'summary':'',
                'category':self.source['category'], 'published_at':None, 'first_seen_at':NOW.isoformat(), 'via':'homepage'}


def parse_homepage(payload, source):
    parser = HomepageParser(source); parser.feed(payload.decode('utf-8', errors='replace'))
    items = list(parser.items.values())[:50]
    if not items: raise ValueError('Ana sayfada haber başlıkları bulunamadı')
    return items


def download(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; Haberlerim/1.0; personal RSS reader)',
                                                  'Accept': 'application/rss+xml, application/xml, text/xml'})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES: raise ValueError('Besleme boyut sınırını aştı')
        return payload


def collect(source):
    errors = []
    for feed in source['feeds']:
        try: return parse_feed(download(feed), source), 'ok', None
        except (urllib.error.URLError, OSError, ET.ParseError, ValueError) as exc:
            errors.append(type(exc).__name__)
    if source.get('homepage_fallback'):
        try: return parse_homepage(download(source['website']), source), 'homepage', None
        except (urllib.error.URLError, OSError, ValueError) as exc:
            errors.append(type(exc).__name__)
    if source.get('google_fallback'):
        query = urllib.parse.urlencode({'q': 'site:' + source['domains'][0], 'hl': 'tr', 'gl': 'TR', 'ceid': 'TR:tr'})
        try: return parse_feed(download('https://news.google.com/rss/search?' + query), source, 'google'), 'fallback', None
        except (urllib.error.URLError, OSError, ET.ParseError, ValueError) as exc:
            errors.append(type(exc).__name__)
    return [], 'error', ', '.join(errors)


def read_previous(path):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError): return {'items': [], 'sources': []}


def build(sources, previous, collector=collect):
    items = []; statuses = []; successes = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        results = list(pool.map(collector, sources))
    for source, (fresh, status, error) in zip(sources, results):
        old = [i for i in previous.get('items', []) if i.get('source') == source['id']]
        old_by_url = {i['url']: i for i in old}
        if fresh:
            successes += 1
            for i in fresh:
                if i['url'] in old_by_url: i['first_seen_at'] = old_by_url[i['url']].get('first_seen_at', i['first_seen_at'])
        merged = {i['url']: i for i in old}
        merged.update({i['url']: i for i in fresh})
        retained = []
        for i in merged.values():
            date = timestamp(i.get('published_at') or i.get('first_seen_at'))
            if date and datetime.fromisoformat(date) >= NOW - timedelta(days=7): retained.append(i)
        retained.sort(key=lambda i: i.get('published_at') or i.get('first_seen_at') or '', reverse=True)
        items.extend(retained[:50])
        if status == 'error' and retained: status = 'cached'
        statuses.append({'id': source['id'], 'name': source['name'], 'website': source['website'],
                         'status': status, 'count': min(len(retained), 50), 'error': error})
        print(f"{source['name']}: {status}, {min(len(retained), 50)} haber", flush=True)
    # Retain the last successful check timestamp if every endpoint fails.
    updated = NOW.isoformat() if successes else previous.get('updated_at')
    return {'updated_at': updated, 'checked_at': NOW.isoformat(), 'sources': statuses, 'items': items}


def atomic_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def main():
    sources = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
    cache = ROOT / '.news-cache' / 'news.json'
    previous = read_previous(cache if cache.exists() else ROOT / 'site' / 'news.json')
    data = build(sources, previous)
    if not data['items']:
        print('Hiçbir haber alınamadı; mevcut yayın değiştirilmiyor.', file=sys.stderr); return 1
    atomic_write(ROOT / 'site' / 'news.json', data)
    atomic_write(cache, data)
    return 0


if __name__ == '__main__': sys.exit(main())
