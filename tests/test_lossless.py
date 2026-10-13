r"""decode(encode(x)) == x, the special token, the encode cache, save and load.

Run from the repository root:
    python -X utf8 -m unittest tests.test_lossless -v

Every check runs on three tokenizers:
  * bytes only   no merges at all, the base case;
  * small        train_fast on the small mixed corpus in bpe_testlib;
  * final        the trained 50k tokenizer, if the file exists
                 (BPE_TOKENIZER, default tokenizer/urdu_bpe.json).
"""
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # finds bpe_testlib
from bpe_testlib import (FIRST_MERGE_ID, INTERNATIONAL, MIXED_CORPUS, ROOT, SEED,  # noqa: E402,F401
                         SPECIAL_ID, SPECIAL_TOKEN, URDU_MARKED, BPETokenizer, lines,
                         random_text, token_bytes, train)
from test_bpe_training import SANITY_MERGES, SANITY_TEXT  # noqa: E402

FINAL = Path(os.environ.get("BPE_TOKENIZER", ROOT / "tokenizer" / "urdu_bpe.json"))

CASES = {
    "empty": "",
    "space": " ",
    "newlines": "\n\nline one\nline two\n\n\n",
    "crlf and tabs": "a\r\nb\tc\r",
    "english": "The quick brown fox jumps over the lazy dog. It's 2026!",
    "urdu": "اردو پاکستان کی قومی زبان ہے۔",
    "urdu with marks": URDU_MARKED + " اور " + "تعالیٰ",
    "zwnj": INTERNATIONAL,
    "mixed": "آج AI کے بارے میں ایک meeting تھی، جو 3:30 PM پر ختم ہوئی۔",
    "roman urdu": "aap kaise hain? main theek hoon.",
    "emoji": "😀 👍🏽 🇵🇰 👨‍👩‍👧 ❤️",
    "other scripts": "中文 Ελληνικά русский हिन्दी 한국어",
    "unnormalised": "\u064a\u0643\u0647 \u0640 \u06f1\u06f9 \u200f \ufeff",
    "spaces": "  leading, double  and trailing  ",
    "rare": "\x00\x7f\u0085\u2028\U0001F600\U0010FFFF",
}


class LosslessContract:
    """Subclasses provide cls.tok."""

    def roundtrip(self, text):
        ids = self.tok.encode(text)
        self.assertTrue(all(isinstance(i, int) and 0 <= i < len(self.tok.vocab) for i in ids))
        self.assertEqual(self.tok.decode(ids), text, repr(text))
        return ids

    def test_named_cases(self):
        for name, text in CASES.items():
            with self.subTest(name):
                self.roundtrip(text)

    def test_empty(self):
        self.assertEqual(self.tok.encode(""), [])
        self.assertEqual(self.tok.decode([]), "")

    def test_random_unicode(self):
        rng = random.Random(SEED)
        for _ in range(300):
            self.roundtrip(random_text(rng, rng.randrange(1, 80)))

    def test_training_text(self):
        self.roundtrip(MIXED_CORPUS)

    # -- special token -------------------------------------------------------
    def test_special_alone(self):
        self.assertEqual(self.tok.encode(SPECIAL_TOKEN), [SPECIAL_ID])
        self.assertEqual(self.tok.decode([SPECIAL_ID]), SPECIAL_TOKEN)

    def test_special_between_text(self):
        enc = self.tok.encode
        for a, b in (("x", "y"), ("ہے", "۔"), ("\n", "\n"), ("", "")):
            self.assertEqual(enc(a + SPECIAL_TOKEN + b), enc(a) + [SPECIAL_ID] + enc(b))
        self.assertEqual(enc(SPECIAL_TOKEN * 3), [SPECIAL_ID] * 3)
        self.assertEqual(enc(SPECIAL_TOKEN + ">"), [SPECIAL_ID] + enc(">"))

    def test_partial_special_is_plain_text(self):
        for text in ("<|endoftext|", "<|endoftext", "endoftext|>", "<||>", "<|ENDOFTEXT|>"):
            ids = self.roundtrip(text)
            self.assertNotIn(SPECIAL_ID, ids)

    def test_special_id_only_for_the_marker(self):
        rng = random.Random(SEED + 1)
        for _ in range(100):
            text = random_text(rng, 50).replace(SPECIAL_TOKEN, "")
            self.assertNotIn(SPECIAL_ID, self.tok.encode(text))

    # -- cache ---------------------------------------------------------------
    def test_cache_gives_same_answer(self):
        text = CASES["mixed"] + " " + CASES["urdu"]
        first = self.tok.encode(text)
        self.tok.encode(CASES["english"] + text)
        self.assertEqual(self.tok.encode(text), first)


class BytesOnly(LosslessContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok = BPETokenizer()

    def test_no_merges_means_one_id_per_byte(self):
        text = "a ہ😀"
        self.assertEqual(self.tok.encode(text), list(text.encode("utf-8")))


class Small(LosslessContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok = train("train_fast", MIXED_CORPUS, 300)

    def test_compresses(self):
        text = CASES["urdu"]
        self.assertLess(len(self.tok.encode(text)), len(text.encode("utf-8")) / 2)

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tok.json"
            self.tok.save(path)
            loaded = BPETokenizer.load(path)
        self.assertEqual(loaded.merges, self.tok.merges)
        self.assertEqual(loaded.vocab, self.tok.vocab)
        for text in CASES.values():
            self.assertEqual(loaded.encode(text), self.tok.encode(text))


class MergeOrder(unittest.TestCase):
    """encode applies merges in the order learned, not left to right."""

    @classmethod
    def setUpClass(cls):
        cls.tok = train("train_fast", SANITY_TEXT, len(SANITY_MERGES))

    def pieces(self, word):
        return token_bytes(self.tok, self.tok.encode(word))

    def test_training_words_are_single_tokens(self):
        for word in ("low", "lower", "newest", "widest", "west"):
            self.assertEqual(self.pieces(word), [word.encode()])

    def test_rank_order(self):
        """"lowest": st (rank 1) and est (2) come before ow (3) and low (4),
        so the answer is [low, est]. Merging the first mergeable pair from
        the left would give [lowe, st] instead."""
        self.assertEqual(self.pieces("lowest"), [b"low", b"est"])
        self.assertEqual(self.pieces("wider"), [b"wid", b"e", b"r"])


@unittest.skipUnless(FINAL.exists(), f"{FINAL} not trained yet")
class Final(LosslessContract, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok = BPETokenizer.load(FINAL)

    def test_size(self):
        self.assertEqual(len(self.tok.merges), 49_743)
        self.assertEqual(len(self.tok.vocab), 50_000)


if __name__ == "__main__":
    unittest.main()
