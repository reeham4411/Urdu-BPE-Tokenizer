# Data Card: Urdu BPE Corpus

train.txt, val.txt, test.txt: UTF-8, `<|endoftext|>` line after every document, 98/1/1 by document within each source, seed 1337. Decimal MB. Normalisation and per-source detail: docs/DATA_CARD_full.md.

## Sources

| Source | Genre | Licence or terms | Collected | Raw MB | Cleaned MB |
|---|---|---|---|---:|---:|
| [UFAL UrMonoCorp](https://ufal.mff.cuni.cz/node/998) | mixed web text | CC BY-NC-SA 3.0 | 2026-10-11 | 717.41 | 712.46 |
| [Wikipedia (API)](https://ur.wikipedia.org/w/api.php) | encyclopedia | CC BY-SA 4.0 | 2026-10-11 | 55.02 | 43.67 |
| [Wikisource (API)](https://ur.wikisource.org/w/api.php) | literature | mostly public domain | 2026-10-11 | 2.03 | 1.77 |
| [Wikipedia dump](https://dumps.wikimedia.org/urwiki/20261001/) | encyclopedia | CC BY-SA 4.0 | 2026-10-12 | 637.51 | 452.24 |

Collected by us through the MediaWiki API: 57.05 MB (evidence/api_collected_files.csv). The dump excludes API pages and stubs under 1,000 bytes.

## Corpus totals

| Split | MB | Documents | Words | Unique words |
|---|---:|---:|---:|---:|
| train | 1,185.94 | 332,678 | 144,880,762 | 1,402,296 |
| val | 11.93 | 3,394 | 1,457,712 | 71,539 |
| test | 12.27 | 3,394 | 1,495,267 | 73,217 |
| **all** | **1,210.14** | **339,466** | **147,833,741** | **1,420,018** |

A word is a run of letters, marks and digits.

## Cleaning steps

| Step (in order) | Removed MB | Share of raw | Documents removed |
|---|---:|---:|---:|
| HTML, wiki markup, entities | 104.91 | 7.4% | 0 |
| Unicode normalisation (net) | 17.80 | 1.3% | 0 |
| Reference and link sections | 26.98 | 1.9% | 0 |
| URLs, e-mails, phone and ID numbers | 0.19 | 0.0% | 0 |
| Lines that are mostly not Urdu | 17.43 | 1.2% | 382 |
| Documents with almost no Urdu function words | 20.09 | 1.4% | 1,931 |
| Exact duplicate documents | 0.07 | 0.0% | 87 |
| Boilerplate lines (in 10+ documents) | 18.52 | 1.3% | 16 |
| Near-duplicate documents (80% of lines seen) | 0.88 | 0.1% | 238 |
| Documents under 10 words | 0.06 | 0.0% | 854 |
| Document separators added | +5.09 | | |
| **Raw 1,411.97 MB to cleaned 1,210.14 MB** | **201.83** | **14.3%** | **3,508** |

## Known gaps and biases

- **Genre and age.** UFAL UrMonoCorp (2014) is 58.9% of the bytes and Wikipedia most of the rest, so news, social media and conversational Urdu are thin; Roman Urdu is absent by design.
- **No structure in UFAL.** Its sentences are shuffled, so its documents are groups of 40 unrelated sentences; only 41.1% of the bytes are real articles.
- **Filters.** Wikipedia over-samples geography and biographies; the language filter does not separate Urdu from Shahmukhi Punjabi or Sindhi.
- **Personal data and rights.** Removed 21 e-mails, 296 phone or ID numbers, 118 handles and 5,641 links. UFAL is CC BY-NC-SA 3.0 and Wikipedia CC BY-SA 4.0, so the text stays inside the course.
