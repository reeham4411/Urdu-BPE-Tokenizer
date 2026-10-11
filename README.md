# Urdu BPE Assignment — Part A

This repository contains **data collection and documentation scripts**, not a finished 500 MB training corpus or BPE tokenizer. Our group's target is **at least 500 MB of cleaned UTF-8 Urdu text**, including **at least 50 MB obtained independently by scraping or API**. We must use **at least three sources and at least two genres**, record permissions, and avoid duplicate counting. A target flag is not evidence that a target has been achieved.

## Current progress (11 October 2026)

- **Urdu Wikipedia API (`urwiki`)**: 2.42 MB of extracted UTF-8 text after random-sampling test; original sequential collection was dominated by asteroid articles, so it was replaced with random sampling.
- **Urdu Wikisource API (`urwikisource`)**: 10 documents, approximately 0.028 MB, including poems and literary prose. Work-level rights still need review.
- **UFAL UrMonoCorp (`ufal`)**: not yet imported.
- **Data quality**: the API extraction is readable but still contains occasional HTML tags, category lines, boilerplate and empty section headings. These must be addressed by the group's cleaning pipeline.

These numbers are historical check-in values, **not live counters**. Regenerate the manifest for up-to-date sizes. Wikisource and Wikipedia are different source projects and genres, but a Wikipedia API collection and Wikipedia dump should not be counted as independent sources of distinct content.

## Setup — Windows PowerShell

From the repository root (where `requirements.txt` is located):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Edit `.env` with your own contact email and descriptive Wikimedia User-Agent. Example **with placeholders**:

```dotenv
WIKIMEDIA_CONTACT=your-email@example.org
USER_AGENT=UrduBPEStudentCorpus/1.0 (your-email@example.org) requests-python
REQUEST_DELAY_SECONDS=2.0
MAXLAG_SECONDS=5
TARGET_MB=55
MIN_URDU_RATIO=0.20
```

The User-Agent is **not** an API key and a Wikimedia account is not required for public pages. Keep your personal contact email out of public repositories; `.env` is ignored by `.gitignore`.

**If `mwparserfromhell` fails to build on Python 3.14 because Microsoft Visual C++ is missing:**

```powershell
$env:WITH_EXTENSION = '0'
python -m pip install -r requirements.txt
```

Alternatively, use a Python 3.12 virtual environment. If activation is blocked, call `.\.venv\Scripts\python.exe` directly. Install dependencies before running scripts.

## Setup — macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your contact details before API requests.

## Important: use the UPDATED random API script

`scripts/collect_wikimedia_api.py` should be the **random-article version**, not the original `generator=allpages` collector. The random version uses `generator=random`, `grnlimit=1`, filters redirects, skips existing page IDs, and supports `--max-pages`, `--min-page-bytes`, and `--max-attempts`. Check which file is installed before starting a long run.

**Random-mode restarts:** There is **no pagination cursor** to resume. The script scans the existing destination files, never overwrites existing article IDs, and requests further random articles. It writes `evidence/logs/{project}_random_state.json` as a **progress summary**, not a cursor. The old `{project}_state.json` belongs to the sequential collector and is no longer used. A random request may encounter an already-saved or previously rejected page.

## Small smoke tests

Run the collector from the repository root:

```powershell
python scripts/collect_wikimedia_api.py --project urwiki --target-mb 55 --max-pages 20
python scripts/collect_wikimedia_api.py --project urwikisource --target-mb 5 --max-pages 10
```

`--max-pages` limits **new documents saved in that invocation**, not the number of API requests. For a bounded test, optionally add `--max-attempts 100` to avoid waiting indefinitely on duplicates or unsuitable pages.

Inspect the files under `data/raw/urwiki/` and `data/raw/urwikisource/`; check that they contain real Urdu text, not page navigation, template remnants or mostly identical articles. Look for per-page evidence under `evidence/logs/{project}_pages.csv` (URLs, revision IDs, UTC retrieval time, saved byte counts and status). Save screenshots if required by the instructor.

## Continue independent collection

After validating quality, collect more **permitted API text**:

```powershell
python scripts/collect_wikimedia_api.py --project urwiki --target-mb 55 --max-pages 500 --max-attempts 2000
python scripts/collect_wikimedia_api.py --project urwikisource --target-mb 5 --max-pages 500 --max-attempts 2000
```

These are **bounded runs**, not promises that the targets will be reached. Omit `--max-pages` and `--max-attempts` only when intentionally starting a longer collection run. You can press `Ctrl+C`; saved documents remain. A request delay of at least two seconds means large collections can take many hours. Follow Wikimedia usage policies, `429`/`Retry-After`, and all source rights restrictions.

**Caution:** Urdu Wikipedia random sampling is broader than the old sequential run, but not automatically balanced: many short entries are templated biographies or places. Evaluate source/genre dominance and near-duplicates. Public pages are not necessarily freely redistributable. Review Wikisource's **individual work licences** before including its contents, and keep any restricted material out of the final corpus.

## Optional published Wikipedia dump

If you also need a bulk encyclopedia corpus, locate a **completed dated** `urwiki` pages/articles dump at https://dumps.wikimedia.org/urwiki/ and pass its _verified_ download URL:

```powershell
python scripts/collect_wikipedia_dump.py --url "PASTE_VERIFIED_DATED_DUMP_URL_HERE"
```

The dump is **published corpus acquisition**, not independent collection through your own scraping/API. It does not count as a different genre from the Wikipedia API data. Keep the compressed-download size separately and deduplicate content overlapping with the API collection. Review the dump script's performance and storage requirements before large downloads.

## Third source — published UFAL UrMonoCorp

Review the official dataset page and licence: https://ufal.mff.cuni.cz/node/998 . Follow its repository link, download the **plain-text** distribution, and unpack it. Then:

```powershell
python scripts/import_published.py --input "C:\path\to\unpacked\plain_text" --source ufal
```

Inspect its actual file format before import (the importer expects supported text files). Preserve the original archive/download size and licence details. **A published dataset does not count toward the separately required 50 MB of independent collection.** A third named source is not proof of a third distinct genre; record actual contents and composition.

## Manifest and data card — when to run

You **may run the manifest at any point** to see current extracted sizes, including after a smoke test. Run it **again after importing the third source and after further collection**:

```powershell
python scripts/build_manifest.py
```

It creates/updates `source_manifest.csv`, measuring `extracted_text_mb` from files under each source folder. The script preserves some manually entered fields, but **check it after each regeneration** and back up any custom edits. Verify the licence/terms entries: starter values are reminders, **not legal approvals**. Manually provide original download sizes (`raw_download_mb` where relevant), final cleaned corpus sizes (`cleaned_mb`), and source-specific acquisition dates/links as appropriate. API text size is not downloaded HTML size.

Use `docs/DATA_CARD_member1_template.md` to prepare your sections of the one-page group `DATA_CARD.md`:

- Sources table: source URL, actual terms/licence, collection date, raw size and cleaned size.
- Known gaps/biases: asteroid-heavy early Wikipedia sample, repetitive place/biography articles, literary/poetry concentration in Wikisource, uneven genre and writing-style coverage. Re-evaluate these against final data.

Coordinate with your teammates for cleaning statistics, total documents/words/unique words, and the final sizes. The shared cleaning stage must remove remaining HTML/wiki/boilerplate, normalize Urdu Unicode in the team's own implementation, deduplicate, split **by document** into **98% train / 1% validation / 1% test** with a fixed seed, and append `<|endoftext|>` after each document.

## Evidence, permissions and repository hygiene

- Keep `evidence/logs/urwiki_pages.csv` and `urwikisource_pages.csv` (retrieval events); `*_random_state.json` is only a progress snapshot.
- `.env`, `data/raw/`, `data/downloads/` and `evidence/logs/` are ignored by the supplied `.gitignore`; this means logs/data do **not** go into Git automatically. Transfer evidence privately or submit as your course requires.
- Respect Wikimedia API rules and terms; do not collect private or paywalled material or bypass restrictions. Preserve URLs and revision identifiers for attribution, and honor work-specific licences and any applicable share-alike conditions.
- `mwparserfromhell` is used only to remove wiki markup during **collection**, not to implement BPE. The group's tokenizer and Urdu normalizer must be original code, as the assignment requires.
- Don't claim the 50 MB independent quota or 500 MB cleaned quota until the corresponding files have been measured and verified.
