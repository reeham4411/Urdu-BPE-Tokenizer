| Spelling problem | Ours raw | Ours normalised | Change | o200k raw | o200k normalised |
|---|---:|---:|---:|---:|---:|
| ZWJ and direction marks | 8 | 2 | -75% | 6 | 3 |
| Arabic presentation forms | 16 | 4 | -75% | 13 | 5 |
| Tatweel stretching | 7 | 2 | -71% | 4 | 3 |
| Non-breaking spaces and runs of spaces | 12 | 4 | -67% | 10 | 6 |
| Arabic yeh in place of Urdu yeh | 8 | 3 | -62% | 4 | 3 |
| Arabic heh in place of heh goal | 8 | 3 | -62% | 6 | 7 |
| Alef maksura at the end of a word | 7 | 3 | -57% | 7 | 6 |
| Arabic kaf in place of Urdu kaf | 7 | 3 | -57% | 4 | 5 |

The 8 largest savings are shown. On all 16 of 21 cases where it matters, normalising first cuts our tokens from 153 to 74 (-52%); the largest saving is "ZWJ and direction marks" (8 to 2 tokens). Because train.txt was normalised, the raw forms are all but absent from it and fall back to bytes or rare pieces; this is why the next assignment calls normalize() before encode() instead of building normalisation into the lossless tokenizer.
