r"""Tests for the pre-tokenisation pattern (BPETokenizer.pretokenize).

Run from the repository root:
    python -X utf8 -m unittest tests.test_pretokenize -v

These describe behaviour, not a particular regex. Two of them encode design
choices you may make differently (punctuation and digits); if you change
them, change the test and explain the choice in the report.
"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # finds bpe_testlib
from bpe_testlib import (INTERNATIONAL, SEED, URDU, URDU_MARKED, ZWNJ,  # noqa: E402,F401
                         BPETokenizer, random_text)


class Pretokenize(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok = BPETokenizer()
        cls.split = cls.tok.pretokenize

    def assertWhole(self, word):
        self.assertEqual(self.split(word), [word])
        self.assertEqual(self.split(" " + word), [" " + word])

    # -- Urdu words stay whole ---------------------------------------------
    def test_plain_urdu_word(self):
        self.assertWhole(URDU)

    def test_combining_marks_stay_in_word(self):
        """The handout's example: GPT-2 cuts this word at each pesh."""
        self.assertWhole(URDU_MARKED)
        for word in ("تعالیٰ", "تقریباً", "لہٰذا", "اِس", "مُحبّت"):
            self.assertWhole(word)

    def test_zwnj_stays_in_word(self):
        self.assertIn(ZWNJ, INTERNATIONAL)
        self.assertWhole(INTERNATIONAL)

    def test_leading_space_joins_next_word(self):
        self.assertEqual(self.split(URDU + " زبان"), [URDU, " زبان"])
        self.assertEqual(self.split("hello world"), ["hello", " world"])

    def test_code_mixing(self):
        self.assertEqual(self.split("آج AI کا دن"), ["آج", " AI", " کا", " دن"])

    # -- boundaries ----------------------------------------------------------
    def test_urdu_punctuation_is_separate(self):
        """Design choice: punctuation does not stick to the word before it,
        otherwise "ہے" and "ہے۔" would become different tokens."""
        self.assertEqual(self.split("ہے۔"), ["ہے", "۔"])
        self.assertEqual(self.split("کیا، کیوں؟"), ["کیا", "،", " کیوں", "؟"])

    def test_newline_is_not_part_of_a_word(self):
        pieces = self.split("ہے\nیہ")
        self.assertEqual(pieces[0], "ہے")
        self.assertEqual(pieces[-1], "یہ")

    def test_digits_are_separate_from_letters(self):
        """Design choice: a number is not glued to the Urdu word next to it."""
        pieces = self.split("سال1947")
        self.assertEqual(pieces[0], "سال")
        self.assertEqual("".join(pieces[1:]), "1947")

    # -- nothing is lost -----------------------------------------------------
    def test_pieces_join_back(self):
        rng = random.Random(SEED)
        cases = ["", " ", "\n\n", "  two spaces", "trailing  ", "\t\r\n", "😀👍🏽",
                 "a" + ZWNJ, ZWNJ + "a", ZWNJ, "\u064f", " \u064f" + URDU]
        cases += [random_text(rng, rng.randrange(1, 60)) for _ in range(500)]
        for text in cases:
            pieces = self.split(text)
            self.assertEqual("".join(pieces), text, repr(text))
            self.assertTrue(all(pieces), f"empty piece for {text!r}")


if __name__ == "__main__":
    unittest.main()
