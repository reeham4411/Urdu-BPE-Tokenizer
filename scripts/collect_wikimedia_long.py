"""Collect randomly selected, longer Urdu Wikimedia pages through the official API.

Place in scripts/collect_wikimedia_long.py and run from repository root.
Uses existing scripts/common.py helpers and existing .env.

Example:
python scripts/collect_wikimedia_long.py --project urwiki --target-mb 55 --min-wiki-bytes 6000 --max-pages 20 --max-attempts 100
"""
import argparse
import csv
import json
import os
from pathlib import Path
from urllib.parse import quote
import requests
from common import ROOT, require_config, api_request, clean_wikitext, urdu_ratio, append_csv, directory_size, timestamp

PROJECTS = {
    'urwiki': ('https://ur.wikipedia.org/w/api.php', 'https://ur.wikipedia.org/wiki/'),
    'urwikisource': ('https://ur.wikisource.org/w/api.php', 'https://ur.wikisource.org/wiki/'),
}
FIELDS = ['source_id', 'page_id', 'title', 'url', 'revision_id', 'retrieved_utc', 'text_bytes', 'file_path', 'status']


def run(project, target_mb, min_wiki_bytes, min_text_bytes, max_pages, max_attempts):
    if min_wiki_bytes < 0 or min_text_bytes < 0:
        raise SystemExit('Minimum byte thresholds must be non-negative.')
    agent = require_config()
    api_url, page_base = PROJECTS[project]
    destination = ROOT / 'data' / 'raw' / project
    destination.mkdir(parents=True, exist_ok=True)
    evidence_dir = ROOT / 'evidence' / 'logs'
    evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path = evidence_dir / f'{project}_pages.csv'
    delay = max(1.0, float(os.getenv('REQUEST_DELAY_SECONDS', '2')))
    min_urdu = float(os.getenv('MIN_URDU_RATIO', '.20'))
    target_bytes = int(target_mb * 1_000_000)
    size_bytes = directory_size(destination)
    saved = attempts = duplicates = skipped = 0
    session = requests.Session()
    session.headers.update({'User-Agent': agent, 'Accept': 'application/json'})
    print(f'Source: {project} | existing {size_bytes / 1e6:.2f} MB | target {target_mb:.2f} MB')
    print(f'Random pages with wiki source >= {min_wiki_bytes} bytes; extracted text >= {min_text_bytes} bytes')

    while size_bytes < target_bytes:
        if max_pages and saved >= max_pages:
            break
        if max_attempts and attempts >= max_attempts:
            break
        # Source-size filter is applied server-side, before transfer.
        params = {
            'action': 'query',
            'generator': 'random',
            'grnnamespace': '0',
            'grnfilterredir': 'nonredirects',
            'grnminsize': str(min_wiki_bytes),
            'grnlimit': '1',
            'prop': 'revisions',
            'rvprop': 'ids|content',
            'rvslots': 'main',
        }
        data = api_request(session, api_url, params, delay)
        attempts += 1
        pages = data.get('query', {}).get('pages', [])
        if isinstance(pages, dict):
            pages = list(pages.values())
        for page in pages:
            page_id = page.get('pageid')
            if not page_id:
                skipped += 1
                continue
            output = destination / f'{page_id}.txt'
            if output.exists():
                duplicates += 1
                continue
            revisions = page.get('revisions', [])
            rev = revisions[0] if revisions else {}
            raw = rev.get('slots', {}).get('main', {}).get('content', '')
            if not isinstance(raw, str):
                raw = ''
            plain = clean_wikitext(raw)
            byte_count = len((plain + '\n').encode('utf-8'))
            if byte_count < min_text_bytes or urdu_ratio(plain) < min_urdu:
                status, bytes_saved = 'skipped_short_or_non_urdu', 0
                skipped += 1
            else:
                output.write_text(plain + '\n', encoding='utf-8')
                bytes_saved = output.stat().st_size
                size_bytes += bytes_saved
                saved += 1
                status = 'saved'
            append_csv(log_path, FIELDS, {
                'source_id': project,
                'page_id': page_id,
                'title': page.get('title', ''),
                'url': page_base + quote(page.get('title', '').replace(' ', '_')),
                'revision_id': rev.get('revid', ''),
                'retrieved_utc': timestamp(),
                'text_bytes': bytes_saved,
                'file_path': str(output.relative_to(ROOT)) if bytes_saved else '',
                'status': status,
            })
        if attempts % 10 == 0 or (max_pages and saved >= max_pages) or size_bytes >= target_bytes:
            print(f'{project}: {size_bytes/1e6:.2f} MB | new saved: {saved} | API calls: {attempts} | duplicates: {duplicates} | quality skips: {skipped}', flush=True)
    print(f'Done: {size_bytes/1e6:.2f} MB total; {saved} new articles; {attempts} API calls.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', choices=PROJECTS, default='urwiki')
    parser.add_argument('--target-mb', type=float, default=55)
    parser.add_argument('--min-wiki-bytes', type=int, default=6000,
                        help='Server-side filter on original wiki page size in bytes')
    parser.add_argument('--min-text-bytes', type=int, default=2000,
                        help='Client-side filter on cleaned UTF-8 text size in bytes')
    parser.add_argument('--max-pages', type=int, default=20,
                        help='Number of new saved articles; 0 means no limit')
    parser.add_argument('--max-attempts', type=int, default=100,
                        help='Safety cap on API calls; 0 means no limit')
    args = parser.parse_args()
    run(args.project, args.target_mb, args.min_wiki_bytes,
        args.min_text_bytes, args.max_pages, args.max_attempts)
