"""Extract UTF-8 text from a locally downloaded/licensed UFAL corpus.
No redistribution or authentication bypass is performed.
Usage: python scripts/import_published.py --input path/to/unpacked/plaintext_dir --source ufal
"""
import argparse
from pathlib import Path
from common import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True, help='Unpacked, plain text files/folder')
    parser.add_argument('--source', default='ufal')
    args = parser.parse_args()
    if not args.input.exists():
        raise SystemExit('Input path not found. Download the published corpus from its official repository first.')
    paths = [args.input] if args.input.is_file() else sorted(p for p in args.input.rglob('*') if p.is_file() and p.suffix.lower() in ('.txt', '.text', '.utf8'))
    dest = ROOT / 'data' / 'raw' / args.source
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for i, source in enumerate(paths):
        try:
            content = source.read_text(encoding='utf-8-sig')
        except UnicodeError:
            print('Skipped non-UTF-8 file:', source)
            continue
        if not content.strip():
            continue
        target = dest / f'document_{i:06d}.txt'
        target.write_text(content, encoding='utf-8')
        count += 1
    print(f'Imported {count} files. If the corpus is one sentence per line, ask the cleaning owner how to define document boundaries.')


if __name__ == '__main__':
    main()
