# Urdu BPE Tokenizer

CS 417 Large Language Models, Assignment 1. The goal is a byte-level BPE tokenizer for Urdu, written from scratch and trained to 50,000 tokens on a cleaned Urdu corpus of at least 500 MB.

This repository currently holds Part A (the corpus). The tokenizer code, the analysis and the report are added by the other members, and their commands go in the last section.

## Layout

| Path | Purpose |
|---|---|
| `scripts/` | Collection scripts (Wikipedia and Wikisource API, UFAL import, manifest) |
| `source_manifest.csv` | One row per source: URL, licence, dates, sizes |
| `normalize.py` | `normalize(text)`, the Urdu Unicode normaliser |
| `textclean.py` | Markup stripping, link and personal data removal, language filters |
| `clean_corpus.py` | The cleaning pipeline that writes `train.txt`, `val.txt`, `test.txt` |
| `corpus_stats.py` | Measures and audits the cleaned files |
| `build_data_card.py` | Writes the one-page `DATA_CARD.md` and the longer `docs/DATA_CARD_full.md` from the measured reports |
| `normalization_cases.py` | Before and after table of spelling problems, used for the report |
| `normalization_effect.py` | Measures how much normalisation shrinks the vocabulary |
| `tests/` | Unit and end-to-end tests |
| `docs/` | Viva notes and the normalisation section for the report |
| `reports/` | `cleaning_report.json`, `cleaning_report.md`, `corpus_stats.json` |
| `bpe.py` | `BPETokenizer`: byte-level BPE, training (reference and fast), encode, decode, save, load |
| `train_tokenizer.py` | Trains on `train.txt` and saves `tokenizer/urdu_bpe.json` |
| `encode_corpus.py` | Writes `train.bin` and `val.bin` (uint16) |
| `tokenizer/` | The trained tokenizer, its readable vocabulary and the training log |
| `tools/` | Data paths, corpus interface audit, 1 MB sample, `.bin` checker, machine info |
| `analysis/` | Part C scripts (tiktoken for comparison only) |
| `report/` | `report.md`, generated tables and plots, `build_report.py` for `report.pdf` |

Data lives under `data/` and is not committed: `data/raw/` (collected text), `data/clean/` (final files), `data/interim/` (temporary).

## Setup

Python 3.10 or newer. From the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows run Python with `-X utf8` (or set `PYTHONUTF8=1`) so that Urdu text prints correctly in the console. If `mwparserfromhell` fails to build, set `WITH_EXTENSION=0` before installing.

## 1. Collecting the raw text

Sources, sizes and licences are in `source_manifest.csv` and summarised in `DATA_CARD.md`.

| Source | Method | Extracted size |
|---|---|---|
| Urdu Wikipedia (`data/raw/urwiki/`) | MediaWiki API, random articles | 55.01 MB |
| Urdu Wikisource (`data/raw/urwikisource/`) | MediaWiki API | 2.03 MB |
| UFAL Urdu monolingual corpus (`data/raw/ufal/`) | Published corpus | 717.41 MB |
| Urdu Wikipedia XML dump, 2026-10-01 (`data/raw/wikipedia_dump/`) | Official dump download | 904.61 MB extracted, 637.51 MB used |

The two API sources, 57.04 MB together, are the text we collected ourselves. Copy `.env.example` to `.env` and put a real contact address in it before using the API scripts, as Wikimedia asks. The scripts wait between requests, back off on 429 and maxlag responses, and never overwrite a saved page. Each saved page is logged with its URL, revision id, UTC time and size in `evidence/logs/`, which stays out of Git.

```powershell
python scripts/collect_wikimedia_long.py --project urwiki --target-mb 55 --min-wiki-bytes 6000 --batch-size 10 --max-pages 20 --max-attempts 10
python scripts/collect_wikimedia_long.py --project urwikisource --target-mb 2
```

`scripts/collect_wikimedia_api.py` is the earlier one-page-per-request version.

Wikipedia dump: download `urwiki-20261001-pages-articles.xml.bz2` (476.81 MB, SHA-1 `019f6b646544f326a5baf8d41daff294b74d59d3`) from https://dumps.wikimedia.org/urwiki/20261001/, then extract it, skipping pages already collected through the API, and set aside articles under 1,000 bytes. Those are 434,745 mostly bot-generated one-line stubs built from one template ("X is a residential area of ..."), which would spend vocabulary on the template.

```powershell
python scripts/collect_wikipedia_dump.py --file data\downloads\urwiki-20261001-pages-articles.xml.bz2 --out data\raw\wikipedia_dump --api-dir data\raw\urwiki
New-Item -ItemType Directory -Force data\raw_stubs\wikipedia_dump | Out-Null
Get-ChildItem data\raw\wikipedia_dump -File | Where-Object { $_.Length -lt 1000 } | Move-Item -Destination data\raw_stubs\wikipedia_dump
```

UFAL: download `urdu-plain-text-corpus.gz` (the plain text file, 223.83 MB, which the repository page shows as 213.46 MiB) from the LINDAT item at https://hdl.handle.net/11858/00-097C-0000-0023-65A9-5, extract it, and import it with the streaming script. The licence there is CC BY-NC-SA 3.0.

```powershell
python scripts/import_published.py --input ".\data\downloads\ufal\urdu-plain-text-corpus" --source ufal
python scripts/build_manifest.py
```

The import keeps the file as one `document_000000.txt` of about 717 MB, one sentence per line. The cleaning step cuts it into documents.

## 2. Cleaning the corpus

With the raw text in `data/raw/`:

```powershell
python -X utf8 -m unittest discover -s tests
python -X utf8 clean_corpus.py --sources ufal urwiki urwikisource wikipedia_dump
python -X utf8 corpus_stats.py
python -X utf8 build_data_card.py
```

`clean_corpus.py` reads every folder in `data/raw/` and runs these steps, logging the bytes each one removes:

1. Strip HTML, leftover wiki markup, entities and any literal `<|endoftext|>`.
2. Normalise with `normalize.py`.
3. Cut reference and link sections from Wikipedia articles.
4. Remove URLs, e-mail addresses, handles and phone or ID numbers.
5. Drop lines that are mostly not Urdu (Urdu letters below 50% of all letters).
6. Drop documents with almost no Urdu function words (Arabic or Persian text, and name-only list pages).
7. Drop exact duplicate documents.
8. Drop lines that occur in 10 or more different documents.
9. Drop documents where 80% or more of the lines were already seen.
10. Drop documents with fewer than 10 words.
11. Split 98% / 1% / 1% by document, with a fixed seed, separately inside each source so that every genre is in validation and test.

The UFAL file has no document markers, so it is cut at blank lines or every 40 lines. On a Windows laptop with 8 GB of RAM (Intel Core, 8 GB), 774 MB of input took about 45 minutes for `clean_corpus.py` (most of it writing the shuffled output from disk; the same run took 11 minutes when the disk was faster) with under 1 GB of memory, then a few minutes for `corpus_stats.py`. Useful options: `--seed`, `--chunk-lines`, `--limit-mb 20` (quick trial on a slice of each source), `--keep-work`. Run `python clean_corpus.py --help` for the rest.

Output in `data/clean/`:

- `train.txt`, `val.txt`, `test.txt`. Each document is followed by a line containing `<|endoftext|>`, so the file looks like `document`, newline, `<|endoftext|>`, newline, `document`, and so on. The newline after the marker belongs to the file layout. An encoder that splits on the marker should drop one leading newline from each piece.
- `doc_index.tsv`, one row per document in file order (split, position, source, bytes, lines).

`corpus_stats.py` exits with an error if a file is malformed, if any character that `normalize.py` removes is still present, or if a document is empty. `build_data_card.py` regenerates the one-page `DATA_CARD.md` (sources, totals, cleaning steps, gaps), the longer `docs/DATA_CARD_full.md` (adds per-source detail and the normalisation decisions), and fills the `cleaned_mb` column of `source_manifest.csv`.

### Normalisation

`normalize(text)` is a pure, idempotent function. The rules, and the number of characters each one touched in the raw corpus, are listed in `reports/cleaning_report.md`. `python normalization_cases.py` prints a before and after table for the usual spelling problems. The ZWNJ and digit decisions are explained in `docs/DATA_CARD_full.md`. Whoever writes the tokenizer pattern should note that U+200C stays inside some words.

The tokenizer must not call `normalize`; the corpus is normalised once, here, so that `decode(encode(text)) == text` holds for any string.

### Tests

```powershell
python -X utf8 -m unittest discover -s tests -v
```

`test_normalize.py` covers every rule and checks idempotence on random strings. `test_textclean.py` covers the cleaning rules. `test_clean_corpus.py` builds a small corpus, runs the whole pipeline and checks the split, determinism, byte accounting and the cleaning effects.

## 3. Tokenizer, encoding and analysis

`bpe.py` holds `BPETokenizer`, a byte-level BPE written from scratch (standard library and `regex` only): IDs 0 to 255 are bytes, 256 is `<|endoftext|>`, and 49,743 merges fill IDs 257 to 49,999. Ties between equally frequent pairs go to the greater pair compared as byte strings. The tokenizer never calls `normalize`; the corpus is normalised once in step 2.

The split files are not in Git. Every script finds them through `tools/datapaths.py`: set `URDU_CLEAN_DIR` to the folder holding `train.txt`, `val.txt` and `test.txt` (default `data/clean`). Derived files (the 1 MB sample, `train.bin`, `val.bin`, logs) go to `URDU_WORK_DIR`, by default a `bpe_work` folder next to the clean folder, so the corpus itself is never written to.

```powershell
$env:URDU_CLEAN_DIR = "C:\path\to\clean"          # bash: export URDU_CLEAN_DIR=/path/to/clean
python -m pip install -r requirements.txt
```

### Rebuild the tokenizer from train.txt

```powershell
python -X utf8 tools/make_sample.py                                   # 1 MB sample, sha256 3afa7e55...
python -X utf8 -m unittest tests.test_pretokenize tests.test_bpe_training tests.test_lossless -v
python -X utf8 -m unittest tests.test_fast_matches_reference -v       # fast == reference on the sample
python -X utf8 train_tokenizer.py                                     # writes tokenizer/urdu_bpe.json
python -X utf8 -m unittest tests.test_lossless -v                     # now also checks the 50k tokenizer
```

On the 1,186 MB train.txt this takes about 12 minutes and 1.7 GB of memory on an Intel i5-1145G7 laptop. `train_tokenizer.py` streams `train.txt` document by document into `train_fast`, saves `tokenizer/urdu_bpe.json` (all 49,743 merges in order), a readable `tokenizer/urdu_bpe.vocab.tsv`, and `tokenizer/urdu_bpe_train_log.json` with the wall-clock time, peak memory and machine. Options: `--vocab-size`, `--limit-mb` for a quick trial, `--method reference`.

### Encode the corpus

```powershell
python -X utf8 encode_corpus.py --workers 4      # train.bin and val.bin in the work folder
python -X utf8 tools/check_bins.py               # IDs < 50,000, one 256 per document, round trip
```

The `.bin` files are flat little-endian `uint16` arrays with no header: `numpy.memmap(path, dtype=numpy.uint16, mode="r")`. Each document is encoded as `encode(doc + "\n")` followed by ID 256, so the newline before each `<|endoftext|>` line is kept and the one after it is dropped (`--layout drop-after`; `drop-both` and `exact` are also available, and `check_bins.py` takes the same flag).

### Analysis (Part C) and report

```powershell
python -m pip install -r requirements-analysis.txt   # tiktoken, matplotlib, markdown: comparison only
python -X utf8 report/build_report.py                # runs analysis/*, writes report.pdf
```

| Script | Question | Output in `report/generated/` |
|---|---|---|
| `analysis/merges.py` | 1. What did the merges learn? | `q1_*.md`, `q1_length.png` |
| `analysis/compare.py` | 2. Tokens per word against GPT-2 and o200k_base | `q2_*.md`, `q2_tokens_per_word.png` |
| `analysis/bad_inputs.py` | 3. Inputs handled badly | `q3*.md` |
| `analysis/training_summary.py` | Part B evidence | `b_training.md`, `b_pattern.md` |
| `analysis/ablation_digits.py` | Cost of splitting every digit (trains a second tokenizer once, cached in the work folder) | `ab_digits.md` |
| `analysis/norm_tokens.py` | Tokens saved by normalising first, on the cases of `normalization_cases.py` | `norm_tokens.md` |

`tiktoken` is used only in `analysis/`; `bpe.py` imports no tokenizer library. `build_report.py` prints the page count (at most four) and any `TODO` left in `report/report.md`.

`tools/check_corpus_interface.py` checks, from the split files themselves, the facts the tokenizer relies on: the `<|endoftext|>` layout, that the text is already normalised, where ZWNJ occurs, and the share of each source.
