import csv
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import requests
import mwparserfromhell

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def require_config():
    agent = os.getenv('USER_AGENT', '')
    if not agent or 'example.com' in agent or 'your-email' in agent:
        raise SystemExit('Edit .env USER_AGENT with your real contact address before using Wikimedia APIs.')
    return agent


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def clean_wikitext(wikitext):
    if not wikitext:
        return ''
    code = mwparserfromhell.parse(wikitext)
    text = code.strip_code(normalize=True, collapse=True, keep_template_params=False)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'(?m)^\s*(?:\*|#|\||\{|\})\s*$', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def urdu_ratio(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(0x0600 <= ord(c) <= 0x06FF for c in letters) / len(letters)


def api_request(session, endpoint, params, delay=2):
    params = dict(params, format='json', formatversion='2', maxlag=os.getenv('MAXLAG_SECONDS', '5'))
    for attempt in range(9):
        try:
            response = session.get(endpoint, params=params, timeout=60)
            if response.status_code in (429, 500, 502, 503, 504):
                wait = min(120, max(float(response.headers.get('Retry-After', 0) or 0), 2**attempt))
                print('HTTP', response.status_code, 'sleep', wait, flush=True)
                time.sleep(wait)
                continue
            response.raise_for_status()
            data = response.json()
            if 'error' in data:
                if data['error'].get('code') == 'maxlag':
                    time.sleep(min(120, 3 * (attempt + 1)))
                    continue
                raise RuntimeError(str(data['error']))
            time.sleep(delay)
            return data
        except requests.RequestException as exc:
            if attempt == 8:
                raise
            print('Request error:', exc, flush=True)
            time.sleep(min(120, 2**attempt))
    raise RuntimeError('Maximum API retries exceeded')


def append_csv(path, fields, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open('a', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        if not exists:
            writer.writeheader()
        writer.writerow(record)


def directory_size(path):
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob('*.txt') if p.is_file())
