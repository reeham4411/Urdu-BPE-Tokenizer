"""Collect longer Urdu Wikimedia pages with respectful batched API requests.

Run from project root:
python scripts/collect_wikimedia_long.py --project urwiki --target-mb 55 --batch-size 10 --max-pages 20 --max-attempts 20

Requires existing scripts/common.py and .env; does not overwrite existing page IDs.
"""
import argparse
import os
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import requests
from common import (
    ROOT, require_config, clean_wikitext, urdu_ratio,
    append_csv, directory_size, timestamp,
)

PROJECTS = {
    'urwiki': ('https://ur.wikipedia.org/w/api.php', 'https://ur.wikipedia.org/wiki/'),
    'urwikisource': ('https://ur.wikisource.org/w/api.php', 'https://ur.wikisource.org/wiki/'),
}
FIELDS = ['source_id', 'page_id', 'title', 'url', 'revision_id',
          'retrieved_utc', 'text_bytes', 'file_path', 'status']


def retry_after_seconds(value):
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
            now = datetime.now(timezone.utc)
            return max(0.0, (parsed - now).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def fetch_batch(session, url, params, delay, retries=5):
    """Serial requests, delay after each attempt, retry transient faults only."""
    for attempt in range(retries + 1):
        response = None
        try:
            response = session.get(url, params=params, timeout=(15, 90))
            if response.status_code in (429, 503, 502, 504, 500):
                wait_hint = retry_after_seconds(response.headers.get('Retry-After'))
                if attempt == retries:
                    response.raise_for_status()
                pause = max(wait_hint or 0, 5.0, min(120.0, 5 * 2 ** attempt))
                print(f'HTTP {response.status_code}; waiting {pause:.0f}s before retry.', flush=True)
                time.sleep(pause)
                continue
            response.raise_for_status()  # Other 4xx errors should not be retried
            data = response.json()
            if 'error' in data:
                error = data['error']
                if error.get('code') in ('maxlag', 'ratelimited', 'readonly'):
                    if attempt == retries:
                        raise RuntimeError(f'API error after retries: {error}')
                    pause = max(5.0, min(120.0, 5 * 2 ** attempt))
                    print(f'API {error.get("code")}; waiting {pause:.0f}s.', flush=True)
                    time.sleep(pause)
                    continue
                raise RuntimeError(f'Non-retryable API error: {error}')
            return data
        except (requests.ConnectionError, requests.Timeout) as exc:
            if attempt == retries:
                raise
            pause = min(120.0, 5 * 2 ** attempt)
            print(f'Network issue ({type(exc).__name__}); retrying in {pause:.0f}s.', flush=True)
            time.sleep(pause)
        finally:
            time.sleep(delay)
    raise RuntimeError('Unexpected retry exhaustion')


def run(project, target_mb, min_wiki_bytes, min_text_bytes,
        max_pages, max_attempts, batch_size):
    if min_wiki_bytes < 0 or min_text_bytes < 0:
        raise SystemExit('Minimum byte thresholds must be non-negative.')
    if batch_size < 1 or batch_size > 20:
        raise SystemExit('Choose a batch size between 1 and 20.')
    if target_mb <= 0 or max_pages < 0 or max_attempts < 0:
        raise SystemExit('Target must be positive; caps cannot be negative.')

    agent = require_config()
    api_url, page_base = PROJECTS[project]
    destination = ROOT / 'data' / 'raw' / project
    destination.mkdir(parents=True, exist_ok=True)
    evidence_dir = ROOT / 'evidence' / 'logs'
    evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path = evidence_dir / f'{project}_pages.csv'
    delay = max(1.0, float(os.getenv('REQUEST_DELAY_SECONDS', '2')))
    min_urdu = float(os.getenv('MIN_URDU_RATIO', '.20'))
    maxlag = int(os.getenv('MAXLAG_SECONDS', '5'))
    target_bytes = int(target_mb * 1_000_000)
    size_bytes = directory_size(destination)
    saved = api_calls = duplicates = skipped = 0

    session = requests.Session()
    session.headers.update({'User-Agent': agent, 'Accept': 'application/json'})
    print(f'Source: {project} | existing {size_bytes/1e6:.2f} MB | target {target_mb:.2f} MB')
    print(f'Batch size: {batch_size} | wiki source >= {min_wiki_bytes} bytes | extracted >= {min_text_bytes} bytes')

    try:
        while size_bytes < target_bytes:
            if max_pages and saved >= max_pages:
                break
            if max_attempts and api_calls >= max_attempts:
                break
            # Each new batch has a new random starting point; the pages in a
            # batch are adjacent in the wiki's underlying random ordering.
            params = {
                'action': 'query', 'format': 'json', 'formatversion': '2',
                'generator': 'random', 'grnnamespace': '0',
                'grnfilterredir': 'nonredirects',
                'grnminsize': str(min_wiki_bytes),
                'grnlimit': str(batch_size),
                'prop': 'revisions', 'rvprop': 'ids|content', 'rvslots': 'main',
                'maxlag': str(maxlag),
            }
            # Resume an incomplete API batch using its continuation token.
            # No persistence needed: already saved page IDs are deduplicated.
            while True:
                if max_attempts and api_calls >= max_attempts:
                    break
                try:
                    data = fetch_batch(session, api_url, params, delay)
                except (requests.RequestException, RuntimeError, ValueError) as exc:
                    print(f'Collection paused after retries: {exc}', flush=True)
                    print('Saved files are intact. Re-run the same command to resume.', flush=True)
                    return
                api_calls += 1
                pages = data.get('query', {}).get('pages', [])
                if isinstance(pages, dict):
                    pages = list(pages.values())
                for page in pages:
                    if (max_pages and saved >= max_pages) or size_bytes >= target_bytes:
                        break
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
                    content = plain + '\n'
                    byte_count = len(content.encode('utf-8'))
                    if byte_count < min_text_bytes or urdu_ratio(plain) < min_urdu:
                        status, bytes_saved = 'skipped_short_or_non_urdu', 0
                        skipped += 1
                    else:
                        # Exclusive create prevents accidental overwrites.
                        try:
                            with output.open('x', encoding='utf-8', newline='\n') as fh:
                                fh.write(content)
                        except FileExistsError:
                            duplicates += 1
                            continue
                        bytes_saved = output.stat().st_size
                        size_bytes += bytes_saved
                        saved += 1
                        status = 'saved'
                    append_csv(log_path, FIELDS, {
                        'source_id': project, 'page_id': page_id,
                        'title': page.get('title', ''),
                        'url': page_base + quote(page.get('title', '').replace(' ', '_')),
                        'revision_id': rev.get('revid', ''),
                        'retrieved_utc': timestamp(), 'text_bytes': bytes_saved,
                        'file_path': str(output.relative_to(ROOT)) if bytes_saved else '',
                        'status': status,
                    })
                if api_calls % 10 == 0 or (max_pages and saved >= max_pages) or size_bytes >= target_bytes:
                    print(f'{project}: {size_bytes/1e6:.2f} MB | new saved: {saved} | API calls: {api_calls} | duplicates: {duplicates} | quality skips: {skipped}', flush=True)
                if (max_pages and saved >= max_pages) or size_bytes >= target_bytes:
                    break
                cont = data.get('continue')
                if not cont:
                    break
                # API continuation is normally absent with small batches;
                # if present, follow it so no eligible pages are lost.
                params.update(cont)
            if max_attempts and api_calls >= max_attempts:
                break
    except KeyboardInterrupt:
        print('\nInterrupted. Previously saved files remain available.', flush=True)
    finally:
        session.close()
    print(f'Done: {size_bytes/1e6:.2f} MB total; {saved} new articles; {api_calls} API calls.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', choices=PROJECTS, default='urwiki')
    parser.add_argument('--target-mb', type=float, default=55)
    parser.add_argument('--min-wiki-bytes', type=int, default=6000)
    parser.add_argument('--min-text-bytes', type=int, default=2000)
    parser.add_argument('--max-pages', type=int, default=20, help='New saved articles; 0 for no cap')
    parser.add_argument('--max-attempts', type=int, default=100, help='API calls; 0 for no cap')
    parser.add_argument('--batch-size', type=int, default=10, help='Pages per API call, 1 to 20')
    args = parser.parse_args()
    run(args.project, args.target_mb, args.min_wiki_bytes, args.min_text_bytes,
        args.max_pages, args.max_attempts, args.batch_size)
