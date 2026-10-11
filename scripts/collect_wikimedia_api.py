"""Collect random public Urdu Wikipedia/Wikisource articles via Wikimedia API.

Run from project root:
    python scripts/collect_wikimedia_api.py --project urwiki --target-mb 55 --max-pages 20
    python scripts/collect_wikimedia_api.py --project urwiki --target-mb 55

Keeps existing page-ID files and appends evidence logs. Random mode does not
use the old sequential `continue` cursor. Source rights must be reviewed.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote

import requests
from common import (
    ROOT, require_config, api_request, clean_wikitext,
    urdu_ratio, append_csv, directory_size, timestamp,
)

PROJECTS = {
    'urwiki': ('https://ur.wikipedia.org/w/api.php', 'https://ur.wikipedia.org/wiki/'),
    'urwikisource': ('https://ur.wikisource.org/w/api.php', 'https://ur.wikisource.org/wiki/'),
}
FIELDS = [
    'source_id', 'page_id', 'title', 'url', 'revision_id',
    'retrieved_utc', 'text_bytes', 'file_path', 'status',
]


def run(project, target_mb, max_pages=0, min_page_bytes=1000, max_attempts=0):
    agent = require_config()
    api_url, page_base = PROJECTS[project]
    destination = ROOT / 'data' / 'raw' / project
    destination.mkdir(parents=True, exist_ok=True)
    evidence = ROOT / 'evidence' / 'logs'
    evidence.mkdir(parents=True, exist_ok=True)
    log_path = evidence / f'{project}_pages.csv'
    # Deliberately separate from old sequential state; random API has no
    # useful sequential cursor to restore.
    state_path = evidence / f'{project}_random_state.json'

    delay = max(1.0, float(os.getenv('REQUEST_DELAY_SECONDS', '2')))
    min_urdu = float(os.getenv('MIN_URDU_RATIO', '0.20'))
    target_bytes = int(target_mb * 1_000_000)
    total_bytes = directory_size(destination)
    saved_count = 0
    attempted = 0
    skipped_existing = 0
    skipped_quality = 0
    # Track low-quality/duplicate IDs within this run without holding corpus texts.
    seen_this_run = set()

    session = requests.Session()
    session.headers.update({
        'User-Agent': agent,
        'Accept': 'application/json',
    })

    print(f'Source: {project} | existing: {total_bytes / 1e6:.2f} MB '
          f'| target: {target_mb:.2f} MB | mode: random', flush=True)
    if total_bytes >= target_bytes:
        print('Target already reached. No new API calls needed.')
        return

    try:
        while total_bytes < target_bytes:
            if max_pages and saved_count >= max_pages:
                break
            if max_attempts and attempted >= max_attempts:
                print('Stopped: maximum API attempts reached.', flush=True)
                break

            # grnlimit=1 is intentional. The API documents that in a single
            # random batch only the starting position is random, and the
            # subsequent pages follow a fixed sequence.
            params = {
                'action': 'query',
                'generator': 'random',
                'grnnamespace': 0,
                'grnlimit': 1,
                'grnfilterredir': 'nonredirects',
                'grnminsize': min_page_bytes,
                'prop': 'revisions',
                'rvprop': 'ids|content',
                'rvslots': 'main',
            }
            data = api_request(session, api_url, params, delay)
            attempted += 1
            pages = data.get('query', {}).get('pages', [])
            if isinstance(pages, dict):
                pages = list(pages.values())

            for page in pages:
                page_id = page.get('pageid')
                if page_id is None:
                    continue
                output = destination / f'{page_id}.txt'
                if output.exists() or page_id in seen_this_run:
                    skipped_existing += 1
                    continue
                seen_this_run.add(page_id)

                revs = page.get('revisions') or []
                rev = revs[0] if revs else {}
                main_slot = rev.get('slots', {}).get('main', {})
                wikitext = main_slot.get('content', '')
                plain = clean_wikitext(wikitext)
                if len(plain) < 200 or urdu_ratio(plain) < min_urdu:
                    status = 'skipped_short_or_non_urdu'
                    bytes_saved = 0
                    skipped_quality += 1
                else:
                    # x mode prevents accidental overwrites, even if files
                    # were created between the existence check and the write.
                    try:
                        with output.open('x', encoding='utf-8', newline='\n') as fp:
                            fp.write(plain + '\n')
                        bytes_saved = output.stat().st_size
                        total_bytes += bytes_saved
                        status = 'saved'
                        saved_count += 1
                    except FileExistsError:
                        skipped_existing += 1
                        continue

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

            if attempted % 10 == 0 or (max_pages and saved_count >= max_pages):
                state_path.write_text(json.dumps({
                    'mode': 'random',
                    'updated_utc': timestamp(),
                    'size_bytes': total_bytes,
                    'attempted_this_run': attempted,
                    'saved_this_run': saved_count,
                    'duplicates_this_run': skipped_existing,
                    'quality_skips_this_run': skipped_quality,
                }, indent=2), encoding='utf-8')
                print(f'{project}: {total_bytes / 1e6:.2f} MB | '
                      f'new saved: {saved_count} | API calls: {attempted} | '
                      f'existing/duplicate: {skipped_existing} | '
                      f'quality skips: {skipped_quality}', flush=True)
    except KeyboardInterrupt:
        print('\nStopped by user. Already saved files are preserved.', flush=True)
    finally:
        session.close()
        state_path.write_text(json.dumps({
            'mode': 'random',
            'updated_utc': timestamp(),
            'size_bytes': directory_size(destination),
            'attempted_this_run': attempted,
            'saved_this_run': saved_count,
            'duplicates_this_run': skipped_existing,
            'quality_skips_this_run': skipped_quality,
        }, indent=2), encoding='utf-8')

    print(f'Done: {directory_size(destination) / 1e6:.2f} MB total; '
          f'{saved_count} new articles this run.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', choices=PROJECTS, default='urwiki')
    parser.add_argument('--target-mb', type=float, default=55)
    parser.add_argument('--max-pages', type=int, default=0,
                        help='Max NEW articles to save in this run (0 = unlimited)')
    parser.add_argument('--min-page-bytes', type=int, default=1000,
                        help='Minimum original wiki page size for random selection')
    parser.add_argument('--max-attempts', type=int, default=0,
                        help='Max random API requests this run (0 = unlimited)')
    args = parser.parse_args()
    if args.target_mb <= 0 or args.max_pages < 0 or args.min_page_bytes < 0 or args.max_attempts < 0:
        parser.error('Target must be positive and limits must be nonnegative.')
    run(args.project, args.target_mb, args.max_pages, args.min_page_bytes, args.max_attempts)
