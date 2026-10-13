"""Download and extract a Wikipedia pages-articles XML dump (.bz2).

Examples:
  python scripts/collect_wikipedia_dump.py --url https://dumps.wikimedia.org/urwiki/LATEST/urwiki-LATEST-pages-articles-multistream.xml.bz2
  python scripts/collect_wikipedia_dump.py --file data/downloads/urwiki.xml.bz2

Use a real dated dump URL from https://dumps.wikimedia.org/urwiki/;
LATEST placeholder URL above is NOT guaranteed to exist. Output excludes page IDs
already saved via the independent urwiki API, preventing double-counting.
"""
import argparse
import bz2
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
from common import ROOT, require_config, clean_wikitext, urdu_ratio, directory_size


def download(url, target):
    agent = require_config()
    if not url.startswith('https://dumps.wikimedia.org/urwiki/'):
        raise SystemExit('Use a verified official urwiki dump URL from dumps.wikimedia.org')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print('Using downloaded file:', target)
        return
    with requests.get(url, headers={'User-Agent': agent}, stream=True, timeout=120) as response:
        response.raise_for_status()
        with target.open('wb') as output:
            for block in response.iter_content(1024 * 1024):
                if block:
                    output.write(block)
    print('Downloaded', target, 'bytes:', target.stat().st_size)


def extract(source, limit=0, destination=None, api_dir=None):
    destination = destination or ROOT / 'data' / 'raw' / 'wikipedia_dump'
    destination.mkdir(parents=True, exist_ok=True)
    api_dir = api_dir or ROOT / 'data' / 'raw' / 'urwiki'
    saved = 0
    ns = '{http://www.mediawiki.org/xml/export-0.11/}'
    with bz2.open(source, 'rb') as stream:
        # Namespace-insensitive parsing for different dump schema versions.
        context = ET.iterparse(stream, events=('start', 'end'))
        _, root = next(context)
        for event, elem in context:
            if event != 'end' or elem.tag.split('}')[-1] != 'page':
                continue
            def child_text(parent, name):
                for c in parent:
                    if c.tag.split('}')[-1] == name:
                        return c.text or ''
                return ''
            page_id = child_text(elem, 'id')
            namespace = child_text(elem, 'ns')
            if namespace != '0' or not page_id or (api_dir / (page_id + '.txt')).exists():
                elem.clear()
                root.clear()
                continue
            text_raw = ''
            for node in elem.iter():
                if node.tag.split('}')[-1] == 'text':
                    text_raw = node.text or ''
                    break
            plain = clean_wikitext(text_raw)
            if len(plain) >= 200 and urdu_ratio(plain) >= .20:
                (destination / (page_id + '.txt')).write_text(plain + '\n', encoding='utf-8')
                saved += 1
            elem.clear()
            root.clear()
            if limit and saved >= limit:
                break
    print(f'Extracted {saved} documents, {directory_size(destination)/1e6:.2f} MB of text')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument('--url', help='Verified dated official XML .bz2 dump URL')
    sources.add_argument('--file', type=Path, help='Already downloaded XML .bz2 dump')
    parser.add_argument('--max-pages', type=int, default=0)
    parser.add_argument('--out', type=Path, default=None,
                        help='output folder (default: data/raw/wikipedia_dump)')
    parser.add_argument('--api-dir', type=Path, default=None,
                        help='urwiki API pages to skip (default: data/raw/urwiki)')
    args = parser.parse_args()
    if args.url:
        name = args.url.split('/')[-1]
        if not name.endswith('.xml.bz2'):
            raise SystemExit('Expected a pages-articles XML .bz2 dump URL')
        file = ROOT / 'data' / 'downloads' / name
        download(args.url, file)
    else:
        file = args.file
    if not file.exists():
        raise SystemExit('Local dump file not found')
    extract(file, args.max_pages, args.out, args.api_dir)
