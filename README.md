# Urdu BPE Assignment — Member 1-Adeena / Part A starter

This is a runnable **collection** project, not a completed 500 MB corpus. The API collector can target 55 MB but depends on availability and network. It does not bypass permissions. Run on Python 3.10+ (tested with Python 3.11+ syntax). The data files, `.env`, and logs stay local and are excluded from Git.

## Setup (Windows PowerShell)

```powershell

py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Edit `USER_AGENT` to contain a contact address **you control**, and not `example.com`. Follow Wikimedia's API conditions. If PowerShell refuses to activate, run `.venv\Scripts\python.exe` in place of `python` or use CMD `\.venv\Scripts\activate.bat`.

## Setup (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` before collection.

## Small smoke tests — do these first

```bash
python scripts/collect_wikimedia_api.py --project urwiki --target-mb 55 --max-pages 10
python scripts/collect_wikimedia_api.py --project urwikisource --target-mb 5 --max-pages 10
python scripts/build_manifest.py
```

Check `data/raw/{project}/` contains readable UTF-8 text; check `evidence/logs/` has timestamps, URLs, page revision IDs, and actual byte counts. Save screenshots of your own run into `evidence/`.

## Independent collection — after the smoke test

```bash
python scripts/collect_wikimedia_api.py --project urwiki --target-mb 55
```

The program will resume from its cursor on restart (a partial last batch may be checked again, without rewriting existing article files). Monitor progress; target 55 MB is a buffer beyond the required 50 MB. If the source runs out before target, use another **permitted, genuinely independent collection**; do not count pages downloaded from the Wikipedia dump twice.

## Literature — third source / second genre

```bash
python scripts/collect_wikimedia_api.py --project urwikisource --target-mb 5
```

**Caution**: Wikisource works have _individual_ copyright statuses. Inspect included works and delete works you are not permitted to use, following your course rules. See https://ur.wikisource.org/wiki/ and site copyright policies.

## Optional published Wikipedia dump (also required if you choose the dump as a source)

Open https://dumps.wikimedia.org/urwiki/ , choose a **completed dated dump**, and copy the actual `pages-articles-multistream.xml.bz2` download URL (often hundreds of MB compressed). Run:

```bash
python scripts/collect_wikipedia_dump.py --url "PASTE_VERIFIED_DATED_DUMP_URL_HERE"
python scripts/build_manifest.py
```

This streams bz2 XML to text files, stripping wiki markup; API-collected page IDs are skipped to prevent duplicate counting. `wikipedia_dump` is the same encyclopedia genre as `urwiki`, and it must **not** be counted as a separate independent source for the three-source requirement unless the instructor accepts two acquisition paths as distinct (assume not). Record compressed size separately. Consult your cleaning teammate for the final deduplication.

## Published UFAL corpus

Visit https://ufal.mff.cuni.cz/node/998 and use its repository download link; review its non-commercial research terms. Download and unpack the plain text **manually**, then import:

```bash
python scripts/import_published.py --input "C:\\path\\to\\unpacked\\plain_text" --source ufal
python scripts/build_manifest.py
```

If downloaded files are `.gz`/`.zip`, unpack first. If there are no `.txt` files or text encoding is unusual, inspect the published dataset's structure and adjust the importer; it intentionally doesn't silently decode unknown encodings. Keep the original download filesize in `source_manifest.csv` (`raw_download_mb`).

## Evidence and manifest

- `evidence/logs/urwiki_pages.csv` and `urwikisource_pages.csv`: article URL, UTC timestamp, revision ID, saved bytes, status.
- `evidence/logs/{project}_state.json`: restart position.
- `source_manifest.csv`: one row per source. `extracted_text_mb` measures text files; raw compressed-download size and final cleaned size are separate fields.
- `docs/DATA_CARD_member1_template.md`: draft for the group data card; fill in verified numbers, licensing, and actual biases.

## Boundaries and ethics

- Check source terms and relevant content licenses before collection; follow Wikimedia policy including correct User-Agent, maxlag, throttling, no concurrency, and server-requested backoff.
- This uses an API instead of scraping webpage HTML. Do not scrape login/paywall/private profiles.
- `mwparserfromhell` strips wiki markup during _collection_; it is not used as a BPE tokenizer. The team's normalisation code must be their own implementation.
- Wikimedia page text commonly carries CC BY-SA requirements. Preserve source URLs and revision IDs for attribution. Wikisource individual works may have separate rights; rights need review.
- Your group must later handle common cleaning, Unicode normalization, deduplication, 98/1/1 document splits, `<|endoftext|>` delimiters, and report accurate final totals.
- The group still needs at least **500 MB cleaned corpus**, even if this independently collected API text reaches 50 MB.
