| Case | Raw bytes | Normalised bytes | Tokens raw (our BPE) | Tokens normalised |
|---|---|---|---|---|
| Arabic yeh in place of Urdu yeh | 30 | 30 | 8 | 3 |
| Alef maksura at the end of a word | 24 | 24 | 7 | 3 |
| Arabic kaf in place of Urdu kaf | 24 | 24 | 7 | 3 |
| Arabic heh in place of heh goal | 20 | 20 | 8 | 3 |
| Do-chashmi heh is a different letter | 39 | 39 | 4 | 4 |
| Tatweel stretching | 21 | 17 | 7 | 2 |
| ZWNJ inside a compound is kept | 38 | 38 | 4 | 4 |
| Stray ZWNJ at word edges is dropped | 23 | 17 | 4 | 2 |
| ZWJ and direction marks | 26 | 17 | 8 | 2 |
| Urdu digits | 36 | 30 | 17 | 9 |
| Arabic-Indic digits and decimal mark | 30 | 24 | 14 | 8 |
| Non-breaking spaces and runs of spaces | 31 | 25 | 12 | 4 |
| Blank lines and stray line breaks | 39 | 33 | 11 | 5 |
| Space before the Urdu full stop | 57 | 55 | 12 | 10 |
| Diacritics are kept | 23 | 23 | 5 | 5 |
| Repeated diacritic | 16 | 12 | 4 | 3 |
| Honorific sign above a name | 19 | 17 | 4 | 2 |
| Arabic presentation forms | 23 | 24 | 16 | 4 |
| Curly quotes and dashes | 61 | 55 | 14 | 11 |
| Code-mixed text is untouched | 62 | 62 | 14 | 14 |
| Roman Urdu is untouched | 26 | 26 | 13 | 13 |
