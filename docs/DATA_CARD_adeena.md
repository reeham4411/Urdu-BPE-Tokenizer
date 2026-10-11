# DATA CARD — Urdu BPE Corpus

**Status (11 October 2026):** Raw/source-extracted collection complete; corpus cleaning, deduplication, final splits and cleaned-size verification are pending. Sizes below are decimal MB (1 MB = 1,000,000 bytes), based on the latest reported collection output, not newly remeasured files.

## Sources

| Source / URL | Genre and acquisition | Extracted text (MB) | Final cleaned (MB) | Licence / terms |
|---|---|---:|---|---|
| [Urdu Wikipedia](https://ur.wikipedia.org/w/api.php) | Encyclopedia; independently collected via MediaWiki API | **55.01** | Pending | Wikimedia page licences and attribution apply; verify exceptions |
| [Urdu Wikisource](https://ur.wikisource.org/w/api.php) | Literature; independently collected via MediaWiki API | **2.03** | Pending | Check individual work rights and applicable licensing |
| [UFAL UrMonoCorp](https://ufal.mff.cuni.cz/node/998) | Mixed-domain Urdu; published corpus download | **717.41** | Pending | Research-use conditions; verify exact LINDAT repository licence |

**Collection date:** 11 October 2026 (reported for all three sources). **Raw extracted total:** approximately **774.45 MB**. **Independent API text:** approximately **57.04 MB**, exceeding the 50 MB acquisition threshold *before cleaning*. UFAL's downloaded `urdu-plain-text-corpus.gz` was listed as approximately **213.46 MB compressed**; the extracted `urmono.txt` measured **717,409,467 bytes**. Source-level URLs, retrieval logs and exact measured values should be maintained in `source_manifest.csv` and `evidence/logs/`.

## Known gaps and biases

Early sequential Wikipedia collection was dominated by near-templated asteroid entries. Later random and longer-article collection broadened topics but may still overrepresent geography, biographies, encyclopedic style, lists and recurring templates. Wikisource samples contain poetry and literary prose that may overrepresent formal or historical language; individual-work rights require review. UFAL was released in 2014, so its language and topic mix may not reflect current Urdu. Roman Urdu, everyday conversation, regional varieties and contemporary code-mixing may be underrepresented. Extracted material can retain empty headings, Wikipedia categories, HTML tags, metadata, repeated boilerplate and spacing inconsistencies. Quantify these limitations after cleaning and deduplication.

## Cleaning steps, normalization and corpus totals — Member 2 to complete

Record extraction/HTML cleanup, Unicode mappings, Urdu-language filtering, exact document deduplication and repeated-line removal, with **bytes removed at each step**. Explain ZWNJ and digit conventions. Report final **cleaned MB, document count, word count, unique-word count**, and fixed-seed **98%/1%/1% document-level** train/validation/test split with `<|endoftext|>` after each document.
