"""Import locally downloaded UTF-8 plain-text corpus without loading it into RAM.

Example:
    python scripts/import_published.py --input "data/downloads/ufal/urdu-plain-text-corpus" --source ufal

Preserves the original, validates UTF-8 incrementally, and removes an optional
UTF-8 BOM. It does not normalize or infer document boundaries.
"""
import argparse
import codecs
import os
from pathlib import Path

from common import ROOT

CHUNK_SIZE = 1024 * 1024  # 1 MiB


def copy_utf8(source: Path, target: Path) -> int:
    """Stream source to target safely; return written byte count."""
    tmp = target.with_name(target.name + '.partial')
    decoder = codecs.getincrementaldecoder('utf-8-sig')(errors='strict')
    total = 0
    try:
        with source.open('rb') as src, tmp.open('wb') as dst:
            while chunk := src.read(CHUNK_SIZE):
                text = decoder.decode(chunk, final=False)
                encoded = text.encode('utf-8')
                dst.write(encoded)
                total += len(encoded)
            final_text = decoder.decode(b'', final=True)
            final_bytes = final_text.encode('utf-8')
            dst.write(final_bytes)
            total += len(final_bytes)
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True,
                        help='Unpacked UTF-8 text file or folder')
    parser.add_argument('--source', default='ufal')
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f'Input not found: {args.input}')
    if not args.source.replace('_', '').replace('-', '').isalnum():
        parser.error('Source must contain only letters, digits, _ or -')

    if args.input.is_file():
        paths = [args.input]
    else:
        paths = sorted(p for p in args.input.rglob('*')
                       if p.is_file() and p.suffix.lower() in ('.txt', '.text', '.utf8'))
    if not paths:
        parser.error('No .txt/.text/.utf8 files found at input')

    destination = ROOT / 'data' / 'raw' / args.source
    destination.mkdir(parents=True, exist_ok=True)
    imported = 0
    total_bytes = 0
    for i, source in enumerate(paths):
        if source.stat().st_size == 0:
            print(f'Skipping empty file: {source}', flush=True)
            continue
        target = destination / f'document_{i:06d}.txt'
        if target.exists() and target.stat().st_size > 0:
            print(f'Already imported, skipping: {target}', flush=True)
            continue
        print(f'Importing {source} ({source.stat().st_size / 1e6:.2f} MB) ...', flush=True)
        try:
            written = copy_utf8(source, target)
        except UnicodeError as exc:
            print(f'Skipped invalid UTF-8 file: {source}: {exc}', flush=True)
            continue
        print(f'  Saved: {target} ({written / 1e6:.2f} MB)', flush=True)
        imported += 1
        total_bytes += written

    print(f'Finished: {imported} new file(s), {total_bytes / 1e6:.2f} MB copied.', flush=True)
    print('Note: sentence-per-line text is not yet separated into documents.')


if __name__ == '__main__':
    main()
