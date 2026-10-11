# Urdu BPE Assignment — Member 1: Collection and Licensing

This project collects and documents source text for **Part A** of the Urdu BPE assignment. It is **not** the finished cleaned corpus or the trained tokenizer. The group must deliver **at least 500 MB of cleaned UTF-8 Urdu** from **at least three sources across two genres**, including **at least 50 MB independently collected via scraping or API**.

## Collection status — 11 October 2026

| Source | Method | Extracted UTF-8 size (decimal MB) | Status |
|---|---|---:|---|
| Urdu Wikipedia (`data/raw/urwiki/`) | Independent MediaWiki API collection | **55.01** | Source-volume target reached |
| Urdu Wikisource (`data/raw/urwikisource/`) | Independent MediaWiki API collection | **2.03** | Collected; verify work rights |
| UFAL UrMonoCorp (`data/raw/ufal/`) | Published corpus download | **717.41** | Imported |
| **Total extracted text** | | **774.45** | **Not the final cleaned size** |

**Independent API total: ~57.04 MB** (Wikipedia + Wikisource), over the minimum 50 MB of independently acquired text. The Wikipedia `55.01 MB total` already includes articles from earlier runs: **do not add earlier progress snapshots again**. The original UFAL `urdu-plain-text-corpus.gz` was listed at **213.46 MB compressed**; extracted `urmono.txt` was **717,409,467 bytes** (717.409 MB / ~684.17 MiB). Sizes are based on previous terminal reports, not a fresh audit. Final cleaned volume and legal eligibility still require verification.

## Setup

Run commands from the repository root.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:WITH_EXTENSION = '0'  # Optional: avoids mwparserfromhell C build error on Python 3.14
python -m pip install -r requirements.txt
Copy-Item .env.example .env  # Only if .env does not already exist
notepad .env
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env  # Only if .env does not already exist
```

Use an email you control. **Do not commit `.env`**.

```dotenv
WIKIMEDIA_CONTACT=your-email@example.org
USER_AGENT=UrduBPEStudentCorpus/1.0 (your-email@example.org) requests-python
REQUEST_DELAY_SECONDS=2.0
MAXLAG_SECONDS=5
TARGET_MB=55
MIN_URDU_RATIO=0.20
```

No Wikimedia account is required for public API requests. Follow Wikimedia rate limits, server-requested backoff and API usage rules.

## Collection scripts

- `scripts/collect_wikimedia_api.py`: original random-page API collector (ensure it is the **updated random** version, not the original sequential `generator=allpages` version).
- `scripts/collect_wikimedia_long.py`: **updated batched longer-article collector**, with duplicate checks, bounded requests and retries. Use the version supporting `--batch-size`.
- `scripts/import_published.py`: **streaming/chunked version** used to import UFAL; the original whole-file `read_text()` implementation raised `MemoryError` on 717 MB input.
- `scripts/build_manifest.py`: measures source directories and writes `source_manifest.csv`.

Example smoke test if new collection is ever needed:

```powershell
python scripts/collect_wikimedia_long.py --project urwiki --target-mb 55 --min-wiki-bytes 6000 --batch-size 10 --max-pages 20 --max-attempts 10
```

The Wikipedia source target has **already been reached**; a new collection run is not currently necessary. `--max-pages` counts newly saved pages per run; `--max-attempts` limits API calls. Requests can be interrupted and restarted without overwriting page-ID files. Batch random-page selection can produce neighboring/topic-clustered pages, so inspect diversity and deduplicate during cleaning.

## UFAL corpus

Original source: https://ufal.mff.cuni.cz/node/998 . The plain-text compressed file was `urdu-plain-text-corpus.gz` (not the tagged corpus); it was extracted to `data/downloads/ufal/urdu-plain-text-corpus/urmono.txt` and imported with:

```powershell
python scripts/import_published.py --input ".\data\downloads\ufal\urdu-plain-text-corpus" --source ufal
```

The imported file is `data/raw/ufal/document_000000.txt` (717,409,467 bytes). It is a **single large text file, not a known single document**; the cleaning teammate must define defensible document boundaries before splitting train/validation/test. Original compressed-download size and the LINDAT item licence should be recorded separately. Published UFAL text **does not** count toward the 50 MB independent API/scraping threshold.

## Manifest and data card

Run from the repository root after changes in `data/raw/`:

```powershell
python scripts/build_manifest.py
```

**Known issue:** A hand-edited CSV may lack the exact `source_id` header (or contain a BOM), triggering `KeyError: 'source_id'`. Back it up, verify the header, and reconcile metadata rather than discarding licence and source information. For a fresh generated CSV, first rename the old file and then rerun the generator. Remove any `wikipedia_dump` row if no dump was acquired. The CSV should have **one row per actually acquired source** and record source URL, licence/terms, collection date, extracted raw-text size, original compressed-download size where applicable, collection method, and eventually cleaned size.

Your contribution to `DATA_CARD.md` is **Sources** and **Known gaps and biases**. Member 2 supplies cleaning steps, normalization rationale, removed-byte statistics, final cleaned sizes, document/word totals and the split. The group Data Card must fit on **one page**.

## Evidence and sharing

Retain `evidence/logs/urwiki_pages.csv` and `urwikisource_pages.csv`, including article URLs, revision IDs, UTC timestamps, saved byte counts and statuses; keep collection scripts and sample screenshots. Logs, `.env`, virtual environment and raw data should **not** be pushed to Git. Share permitted data privately with teammates through the course-authorized shared Drive. The existing Drive upload was a snapshot: **upload/sync the final 55.01 MB Wikipedia folder** if it still contains earlier files. Member 2 can begin development from a sample but should use the final snapshot for final cleaning.

**Rights and quality:** Verify licence/terms for each source and individual Wikisource works. Preserve attribution; do not collect private data, bypass logins/paywalls or redistribute restricted material. Remaining HTML/wiki markup, category lines, duplicated templates, Unicode variants and data imbalance must be addressed during cleaning. Only the **final post-cleaning** corpus can establish compliance with the 500 MB requirement.

## Member 1 remaining steps

1. Verify the three source rows and licence references in `source_manifest.csv`; fix malformed headers and remove uncollected dump placeholders.
2. Sync final raw data and collection evidence to the permitted shared location for Member 2.
3. Merge Member 1 sections of `DATA_CARD.md` with Member 2's measured cleaning results and final corpus counts.
4. Later, perform **Part C Q2–Q3**: compare tokens per word on `test.txt` and seven handpicked inputs for your BPE, GPT-2 (`gpt2`) and `o200k_base`; show a table/plot and explain three bad cases. `tiktoken` is allowed for comparison only, not for the Part B BPE implementation.
