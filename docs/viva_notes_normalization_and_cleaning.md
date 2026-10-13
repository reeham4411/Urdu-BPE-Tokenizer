# Viva notes: normalisation and cleaning

Questions that can be asked about `normalize.py`, `textclean.py` and `clean_corpus.py`, with short answers.

**Why normalise before training, and why outside the tokenizer?**
The same Urdu word can be typed with different code points that look identical. Each spelling would be a separate pre-token and would get its own merges. Normalising once, before counting pairs, gives one spelling per word. It stays outside the tokenizer because the tokenizer must be lossless: `decode(encode(x)) == x` for any string, which a normalising tokenizer cannot promise.

**Why does the order of steps inside `normalize` matter?**
NFC goes first so that sequences like yeh + hamza are composed before the letter maps run. After the character table runs, deleted characters (BOM, ZWJ) can leave marks adjacent or out of order, so ZWNJ is resolved, the text is recomposed if needed, and only then are repeated or orphan marks removed. The random-string test found two ordering bugs in the first version, both breaking idempotence.

**What does the table do, and why one `str.translate`?**
One dictionary maps or deletes characters in a single C-level pass, which is much faster than many `replace` calls. Letter variants, digits, typographic punctuation, spaces, newlines and all deletions are in it.

**U+0647 is mapped to U+06C1 but U+06BE is kept. Why?**
Arabic heh (U+0647) is what people type when they want a Urdu heh, so it maps to heh goal. Do-chashmi heh (U+06BE) is a different letter that marks aspiration (kh, bh), so it must not be merged. We do not turn U+0647 into U+06BE by context, because "kahani" and "khana" differ only by that choice and both occur.

**What is the ZWNJ policy?**
Keep U+200C only between a joining letter and a letter that can join to it, drop it elsewhere. Urdu uses it inside compounds such as the word for "international". Elsewhere (at word edges, repeated, after letters like alef, waw, reh that never join forward) it changes nothing on screen, so keeping it would only create duplicate spellings. The tokenizer pattern has to include U+200C in the word class so the kept ones do not split words.

**Why ASCII digits?**
In the raw text about 98% of digits were already ASCII, English words and dates in code-mixed text use them, and the tokenizer comparison with GPT-2 and o200k_base uses numbers. Mapping the rest to ASCII means 1947 is always one spelling.

**Why NFKC one character at a time?**
NFKC on a whole string would also rewrite ligatures and superscripts in the English parts. Folding only Arabic presentation forms and full-width forms fixes the cases that matter (the Allah and ﷺ ligatures, isolated and medial letter forms) and leaves everything else alone. Ligatures that expand to several words get spaces around them, otherwise the phrase is glued onto the previous word.

**Why remove the honorific and Quranic signs but keep zabar, zer, pesh?**
The signs sit on top of names and verses and are applied inconsistently, so the same name appears in two spellings. The vowel marks are part of the spelling in poetry and dictionaries, and Part C has a test input with diacritics, so they stay (composed to NFC, repeats collapsed).

**Why close the space before the Urdu full stop?**
UFAL is word-tokenised: every one of its Urdu full stops has a space before it, while Wikipedia is written normally. Without this step the tokenizer would learn both " ۔" and "۔".

**How is a line judged to be Urdu?**
Urdu letters divided by all letters in the line must be at least 0.5, and there must be at least two Urdu letters. English words inside a sentence lower the ratio a little but do not cause removal. Lines with no letters (numbers, symbols) are dropped.

**How are Persian and Arabic documents caught?**
They use the same script, so the line filter keeps them. A document-level check measures the share of tokens that are common Urdu function words (ہے, کے, میں, اور and so on). Urdu pages score a median of about 0.34, Persian stays below 0.07, Arabic below 0.04. The cut is 0.05. It cannot separate Urdu from Shahmukhi Punjabi.

**What is boilerplate removal and why 10 documents?**
Lines like "References" or "Wikidata short description" repeat across many pages. A line that appears in 10 or more different documents is removed everywhere. Counting is per document, so one document repeating a refrain (poetry) does not trigger it.

**How are duplicates handled?**
Exact duplicates by hash of the whole cleaned document. Near duplicates: a document is dropped if 80% or more of its lines (at least 4 lines) were already seen in earlier documents.

**How is the split made, and is it deterministic?**
By document, 98/1/1, with `random.Random(f"{seed}:{source}")` shuffling each source separately so every source appears in val and test. The same seed and input give byte-identical files, which a test checks.

**How do you know no text was lost without a record?**
Every step records the bytes it removes, and raw bytes minus all removed bytes equals the final bytes exactly. A test checks this identity.

**Complexity.**
Everything is linear in corpus size. Memory holds one 64-bit hash per distinct line (a few tens of MB) and a set of document hashes. Documents go through disk between the passes.
