# Data Card: Urdu BPE Corpus

Generated 2026-10-13 by build_data_card.py. Sizes are decimal MB. Files: train.txt, val.txt, test.txt (UTF-8, `<|endoftext|>` on its own line after every document, 98/1/1 split by document, seed 1337, split drawn separately inside each source).

## Sources

| Source | Genre | Licence or terms | Collected | Raw MB | Cleaned MB |
|---|---|---|---|---:|---:|
| [UFAL UrMonoCorp](https://ufal.mff.cuni.cz/node/998) | mixed web text | CC BY-NC-SA 3.0 (LINDAT item 11858/00-097C-0000-0023-65A9-5) | 2026-10-11 | 717.41 | 712.46 |
| [Urdu Wikipedia API](https://ur.wikipedia.org/w/api.php) | encyclopedia | CC BY-SA 4.0 (Wikimedia Terms of Use); attribution required | 2026-10-11 | 55.02 | 43.67 |
| [Urdu Wikisource API](https://ur.wikisource.org/w/api.php) | literature | Source texts mostly public domain; wiki text CC BY-SA 4.0; status is per work | 2026-10-11 | 2.03 | 1.77 |
| [Urdu Wikipedia XML dump 2026-10-01 (API overlaps excluded)](https://dumps.wikimedia.org/urwiki/20261001/) | encyclopedia | Wikipedia page text: usually CC BY-SA 4.0; verify exceptions | 2026-10-12 | 637.51 | 452.24 |

Collected by us through the MediaWiki API: 57.05 MB (every page, with its link and checksum, in evidence/api_collected_files.csv). Downloaded by us from the official Urdu Wikipedia XML dump of 2026-10-01: 637.51 MB of article text, after skipping pages already collected through the API and setting aside articles under 1,000 bytes, which are mostly bot-generated stubs built from one template. The rest is the published UFAL corpus.

## Corpus totals

| Split | MB | Documents | Words | Unique words |
|---|---:|---:|---:|---:|
| train | 1,185.94 | 332,678 | 144,880,762 | 1,402,296 |
| val | 11.93 | 3,394 | 1,457,712 | 71,539 |
| test | 12.27 | 3,394 | 1,495,267 | 73,217 |
| **all** | **1,210.14** | **339,466** | **147,833,741** | **1,420,018** |

By source: ufal 58.9% (136,615 documents, 88,490,984 words, 569,762 unique); urwiki 3.6% (7,737 documents, 5,221,661 words, 192,998 unique); urwikisource 0.1% (492 documents, 231,144 words, 17,448 unique); wikipedia_dump 37.4% (194,622 documents, 53,889,952 words, 969,259 unique). A word is a run of letters, marks and digits. Median document 409 words (10th to 90th percentile 41 to 744). Words missing from train: 0.7% of val tokens, 0.7% of test tokens.

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

342,974 documents read, 339,466 kept. UFAL has no documents, so it is cut into groups of 40 lines.

## Normalisation decisions

- **Letters.** Arabic yeh and alef maksura to U+06CC (603,854 found), Arabic kaf to U+06A9 (113,402), Arabic heh to U+06C1 (133,637); also teh marbuta, heh with yeh above and alef wasla. U+06BE stays separate from U+06C1. Heh is not guessed to be do-chashmi from context, because kahani and khana differ by that one letter.
- **Digits are ASCII.** 99.9% of the raw digits were already ASCII (19,438 Arabic-Indic or Urdu digits against 16,530,895). One convention means the same number is never learned twice in two digit sets, and the tokenizer comparison uses ASCII numbers.
- **ZWNJ is kept only where it matters.** Urdu uses it inside compounds such as بین‌الاقوامی. It changes rendering only between a joining letter and a following letter, so it is kept there and dropped at word edges, in runs and after non-joining letters (3,963 kept of 7,271). The tokenizer pattern must treat U+200C as part of a word.
- **Removed.** Tatweel (14,534), ZWJ, direction marks, BOM, ZWSP (10,986 invisible characters), honorific and Quranic signs (56,246). Zabar, zer, pesh and shadda are kept, composed to NFC, repeats collapsed.
- **Spacing and typography.** In the raw text 3,217,622 of 5,692,141 Urdu full stops (56.5%) had a space before them, almost all from UFAL, which is word-tokenised. Spaces before Urdu and ASCII punctuation and inside brackets are closed so every source has one style. Curly quotes, dashes and the ellipsis go to ASCII, Arabic presentation forms are folded with NFKC one character at a time, and runs of spaces and blank lines are collapsed.

## Known gaps and biases

- **Genre balance.** UFAL UrMonoCorp is 58.9% of the corpus, so the model mostly sees its register. Wikisource adds poetry and older literary prose, which is formal and archaic.
- **Age.** UFAL was released in 2014; the Wikipedia dump (October 2026) adds current topics and vocabulary, but only in encyclopedic register. Recent news, social media language and conversational Urdu are still thin. Roman Urdu is absent by design.
- **Topics.** Wikipedia collection over-samples geography, biographies, lists and dates. An early sequential run gave near-templated asteroid articles; random sampling, repeated-line removal and near-duplicate removal reduce them but not entirely.
- **No document structure in UFAL.** It is one sentence per line, in shuffled order, so each of its documents is a group of 40 unrelated sentences: plenty of Urdu, no long-range context. Only the other sources (41.1% of the bytes) are real articles. Because order is random, val and test do not share neighbouring text with train.
- **Language filter.** It separates Urdu from Persian, Arabic and Pashto but not from Shahmukhi Punjabi or Sindhi. The function-word check also drops name-only list and table pages (the 'list of ...' articles), which are Urdu but carry little prose.
- **Script mix and personal data.** 98.3% of letters are Urdu script, 1.7% Latin (code-mixing, names). Removed: 21 e-mails, 296 phone or ID numbers, 118 handles, 5,641 links.
- **Rights.** UFAL is CC BY-NC-SA 3.0 and Wikipedia is CC BY-SA 4.0, so the text stays inside the course and is not redistributed. Each Wikisource work needs its own rights check.
