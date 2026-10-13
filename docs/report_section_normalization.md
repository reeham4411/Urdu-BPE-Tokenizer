# Report section: normalisation (for the assembled report.pdf)

Written for the report editor. About half a page plus one small table. Numbers come from `reports/normalization_effect.md` (100 MB of real UFAL text) and `reports/cleaning_report.md` (the final run on the full corpus).

## Text

**Why normalise.** Urdu words are often typed with different code points that look the same on screen: Arabic yeh (U+064A) and alef maksura (U+0649) for Urdu yeh (U+06CC), Arabic kaf (U+0643) for U+06A9, Arabic heh (U+0647) for heh goal (U+06C1), plus tatweel, invisible marks and several digit sets. A byte-level BPE tokenizer would treat each spelling as a different word and spend merges on all of them. In 100 MB of UFAL text, normalisation reduces the number of distinct words from 197,438 to 186,344 (5.6%), and 0.62% of all word tokens change spelling. The most frequent changes are the commonest function words: میں, ہیں, یہ, نہیں, ایک and کی, all typed with Arabic yeh in a noticeable share of sentences. The whole corpus is normalised once, before training. The tokenizer never calls `normalize`, so `decode(encode(x)) == x` still holds for every string.

**Decisions.**

| Problem | Rule | Occurrences |
|---|---|---:|
| Arabic yeh, alef maksura | to U+06CC | 362,789 |
| Arabic kaf | to U+06A9 | 58,840 |
| Arabic heh | to U+06C1 (U+06BE kept apart) | 60,286 |
| Tatweel | removed | 5,029 |
| ZWJ, direction marks, BOM, ZWSP | removed | 2,626 |
| Honorific and Quranic signs | removed | 32,438 |
| Arabic-Indic and Urdu digits | to ASCII | 3,036 |
| Space before punctuation or inside brackets | closed | 3,174,342 full stops alone |

- **Digits are ASCII.** 99.9% of the raw digits already were, the comparison tokenizers use them, and one convention stops 1947 from becoming two spellings.
- **ZWNJ is kept only between a joining letter and a letter that can join to it.** Urdu uses it on purpose in compounds such as بین‌الاقوامی, and it changes nothing on screen elsewhere (word edges, repeats, after alef or waw). 541 of 885 survive. The tokenizer pattern therefore has to keep U+200C inside a word.
- **Heh is not guessed.** Arabic heh always becomes heh goal. Choosing do-chashmi heh from context would turn کہانی into کھانی, so the rule is left simple.
- **Diacritics stay.** Zabar, zer, pesh and shadda are kept (NFC, repeats collapsed). Honorific and Quranic signs are removed because they appear inconsistently on the same names.
- **Word-tokenised text is closed up.** Every Urdu full stop in the UFAL sample had a space in front of it, which no other source has, so spaces before ۔ ، ؟ ؛ , . ! ? : ; and inside brackets are closed.
- Two bugs were found by testing against real text and fixed: the ﷺ ligature expanded to four words glued to the previous word, and the common spelling اﷲ (alef plus the Allah ligature) became اللہ with a doubled alef.

## Question 3 candidates that come from normalisation

Run once the tokenizer exists:

```
python normalization_cases.py --tokenizer <tokenizer file> --markdown reports/normalization_cases.md
```

It prints raw and normalised token counts for each case. These are the inputs most likely to look bad:

1. **Urdu or Arabic-Indic digits** (۱۹۴۷). The training text only contains ASCII digits, so each digit falls back to its two bytes. Expect about two tokens per digit against one for ASCII.
2. **Text typed with Arabic yeh or kaf** (ميں). Those code points never occur in the training text, so no merge covers them and the word costs close to one token per byte. This is not a tokenizer defect if the text is normalised first. The report should say so, and show the normalised count next to the raw one.
3. **Words with honorific or Quranic signs** (عمرؓ, ﷺ). The signs were removed from the training text, so they cost raw bytes. Zabar and zer inside a word are also rarer than the bare spelling, so a fully voweled line costs more tokens than the same line without marks.
4. **ZWNJ inside a compound.** Only some spellings survive cleaning, so the word may be split at the ZWNJ.

Item 1 and item 2 are the best choices if one input of the three has to be about normalisation: both are common in real Urdu text, and both are fixed by calling `normalize` before `encode`.
