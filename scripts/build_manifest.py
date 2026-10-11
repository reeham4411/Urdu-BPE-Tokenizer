"""Create source manifest with measured text bytes and editable licence fields.
Do not call the measured extraction size the original compressed-download size.
"""
import csv
from datetime import datetime, timezone
from common import ROOT, directory_size

SOURCES = [
    ('urwiki', 'Urdu Wikipedia API', 'encyclopedia', 'https://ur.wikipedia.org/w/api.php', 'Wikipedia page text: usually CC BY-SA 4.0; verify page exceptions', 'official API'),
    ('wikipedia_dump', 'Urdu Wikipedia XML dump (API overlaps excluded)', 'encyclopedia', 'https://dumps.wikimedia.org/urwiki/', 'Wikipedia page text: usually CC BY-SA 4.0; verify exceptions', 'published dump download'),
    ('urwikisource', 'Urdu Wikisource API', 'literature', 'https://ur.wikisource.org/w/api.php', 'Varies by work/page; verify individual work and metadata', 'official API'),
    ('ufal', 'UFAL UrMonoCorp', 'mixed (news/blogs/literature/etc)', 'https://ufal.mff.cuni.cz/node/998', 'Non-commercial research; review LINDAT item terms', 'published corpus download'),
]


def main():
    destination = ROOT / 'source_manifest.csv'
    old = {}
    if destination.exists():
        with destination.open(encoding='utf-8', newline='') as fh:
            old = {r['source_id']: r for r in csv.DictReader(fh)}
    fields = ['source_id','source_name','genre','url','license_or_terms','collection_date_utc','extracted_text_mb','raw_download_mb','cleaned_mb','collection_method','local_path','notes']
    with destination.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fields)
        writer.writeheader()
        for source_id,name,genre,url,terms,method in SOURCES:
            p = ROOT / 'data' / 'raw' / source_id
            earlier = old.get(source_id, {})
            size = directory_size(p)
            writer.writerow({
                'source_id': source_id, 'source_name': name, 'genre': genre,
                'url': url, 'license_or_terms': earlier.get('license_or_terms') or terms,
                'collection_date_utc': earlier.get('collection_date_utc') or (datetime.now(timezone.utc).date().isoformat() if size else ''),
                'extracted_text_mb': f'{size/1e6:.3f}',
                'raw_download_mb': earlier.get('raw_download_mb', ''),
                'cleaned_mb': earlier.get('cleaned_mb', ''),
                'collection_method': method, 'local_path': str(p.relative_to(ROOT)),
                'notes': earlier.get('notes', '')
            })
    print('Saved', destination)
    print('Note: verify all licence fields; fill original download sizes and final cleaned sizes manually.')

if __name__ == '__main__':
    main()
