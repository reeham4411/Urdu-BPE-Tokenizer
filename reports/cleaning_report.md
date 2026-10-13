# Cleaning report

Run time: 2659.8 s on Windows-11-10.0.26200-SP0, Python 3.12.10.

## Bytes removed by each step

| Step | What | Bytes removed | MB | Documents removed |
|---|---|---:|---:|---:|
| markup | HTML, wiki markup and entities | 104,909,179 | 104.91 | 0 |
| normalize | Unicode normalisation | 17,795,701 | 17.80 | 0 |
| tail | reference and link sections | 26,975,446 | 26.98 | 0 |
| personal | URLs, e-mails, phone and ID numbers | 191,261 | 0.19 | 0 |
| language | lines that are mostly not Urdu | 17,426,014 | 17.43 | 382 |
| nonurdu_doc | documents in Arabic script that are not Urdu | 20,088,753 | 20.09 | 1,931 |
| exact_dup | exact duplicate documents | 73,907 | 0.07 | 87 |
| boilerplate | boilerplate lines repeated across documents | 18,519,787 | 18.52 | 16 |
| near_dup | near-duplicate documents | 882,988 | 0.88 | 238 |
| short | documents with too few words | 56,748 | 0.06 | 854 |

Raw: 1,411,969,573 bytes. Final: 1,205,049,789 bytes in 339,466 documents.

## Per source

| Source | Raw MB | Final MB | Documents kept | Documents read |
|---|---:|---:|---:|---:|
| ufal | 717.41 | 710.41 | 136,615 | 136,615 |
| urwiki | 55.02 | 43.56 | 7,737 | 7,961 |
| urwikisource | 2.03 | 1.77 | 492 | 510 |
| wikipedia_dump | 637.51 | 449.32 | 194,622 | 197,888 |

## Normalisation rules, characters affected

| Rule | Characters |
|---|---:|
| arabic_yeh_to_urdu_yeh | 603,854 |
| arabic_kaf_to_urdu_kaf | 113,402 |
| arabic_heh_to_heh_goal | 133,637 |
| heh_yeh_above_to_heh_goal_hamza | 185 |
| teh_marbuta_to_teh_marbuta_goal | 86,887 |
| alef_wasla_to_alef | 262 |
| tatweel_removed | 14,534 |
| invisible_removed | 10,986 |
| annotation_signs_removed | 56,246 |
| arabic_indic_digits_to_ascii | 16,445 |
| extended_indic_digits_to_ascii | 2,993 |
| number_punctuation_to_ascii | 5,975 |
| typographic_punctuation_to_ascii | 745,377 |
| unicode_spaces_to_space | 100,324 |
| tabs_to_space | 89,116 |
| line_separators_to_newline | 5,773,423 |
| zwnj_seen | 7,271 |
| control_chars_removed | 18 |

ASCII digits in the raw text: 16,530,895
