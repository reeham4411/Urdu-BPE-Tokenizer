r"""Training tests, run against BOTH train_reference and train_fast.

Run from the repository root:
    python -X utf8 -m unittest tests.test_bpe_training -v

About the "sanity check": the handout says "Test it on the sanity check
below", but the PDF we were given contains no example after that sentence
(checked in the text layer of all five pages). Until the course staff
supplies it, this file uses the classic corpus from Sennrich et al. (2016),
derived by hand below under OUR rules (count, then greater pair as bytes).
If the official example appears, add it as one more test here.

Words are put on separate lines so that each is one pre-token with no
leading space; this assumes your pattern, like GPT-2's, keeps a newline out
of the following word (only a space is attached).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # finds bpe_testlib
from bpe_testlib import (FIRST_MERGE_ID, SPECIAL_TOKEN, BPETokenizer, lines,  # noqa: E402,F401
                         merged_tokens, train)

SANITY_TEXT = lines(("low", 5), ("lower", 2), ("widest", 3), ("newest", 6))

# Derivation (counts of all adjacent pairs, weighted by word frequency):
#  1. es=9, st=9 tie -> (s,t) > (e,s)                         -> "st"
#  2. (e,st)=9                                                -> "est"
#  3. lo=7, ow=7 tie -> (o,w) > (l,o)                         -> "ow"
#  4. (l,ow)=7                                                -> "low"
#  5. ne=6, ew=6, (w,est)=6 tie -> "w" is the greatest first  -> "west"
#  6. ne=6, (e,west)=6 tie -> (n,e) > (e,west)                -> "ne"
#  7. (ne,west)=6                                             -> "newest"
#  8. wi=3, id=3, (d,est)=3 tie -> (w,i)                      -> "wi"
#  9. (wi,d)=3 > (d,est)=3 because b"wi" > b"d"               -> "wid"
# 10. (wid,est)=3                                             -> "widest"
# 11. (low,e)=2, (e,r)=2 tie -> b"low" > b"e"                 -> "lowe"
# 12. (lowe,r)=2                                              -> "lower"
# After 12 merges every word is one token and no pair is left.
SANITY_MERGES = [b"st", b"est", b"ow", b"low", b"west", b"ne", b"newest",
                 b"wi", b"wid", b"widest", b"lowe", b"lower"]


class TrainingContract:
    """Tests shared by both trainers. Subclasses set METHOD."""
    METHOD = None

    def train(self, text, n_merges):
        return train(self.METHOD, text, n_merges)

    # -- the hand-derived examples -----------------------------------------
    def test_sanity_corpus(self):
        tok = self.train(SANITY_TEXT, len(SANITY_MERGES))
        self.assertEqual(merged_tokens(tok), SANITY_MERGES)

    def test_sanity_first_merge_ids(self):
        tok = self.train(SANITY_TEXT, 2)
        self.assertEqual(tok.merges[0], (ord("s"), ord("t")))      # new ID 257
        self.assertEqual(tok.merges[1], (ord("e"), FIRST_MERGE_ID))  # e + 257

    def test_stops_when_no_pair_is_left(self):
        tok = self.train(SANITY_TEXT, 40)
        self.assertEqual(merged_tokens(tok), SANITY_MERGES)

    def test_tie_break_compares_bytes_not_ids(self):
        """After "ab" becomes ID 257, (257, c) and (b, d) both occur 3 times.
        As bytes, (b"b", b"d") > (b"ab", b"c"); as IDs, (257, 99) > (98, 100).
        The spec says bytes, so "bd" must come before "abc"."""
        text = lines(("abc", 3), ("bd", 3), ("ab", 2))
        tok = self.train(text, 3)
        self.assertEqual(merged_tokens(tok), [b"ab", b"bd", b"abc"])

    def test_plain_tie_takes_greater_pair(self):
        tok = self.train(lines(("ab", 1), ("cd", 1)), 1)
        self.assertEqual(merged_tokens(tok), [b"cd"])

    def test_overlapping_pairs(self):
        """"aaa" holds (a,a) twice; merging left to right gives [aa, a]."""
        tok = self.train(lines(("aaa", 1)), 5)
        self.assertEqual(merged_tokens(tok), [b"aa", b"aaa"])
        tok = self.train(lines(("aaaa", 1)), 5)
        self.assertEqual(merged_tokens(tok), [b"aa", b"aaaa"])

    def test_frequent_overlap_beats_rare_pair(self):
        """In "aaaaa" x2 the pair (a,a) counts 4 per word = 8 > (b,c) = 5."""
        tok = self.train(lines(("aaaaa", 2), ("bc", 5)), 1)
        self.assertEqual(merged_tokens(tok), [b"aa"])

    # -- structure of what is learned ------------------------------------
    def test_vocab_layout(self):
        tok = self.train(SANITY_TEXT, 6)
        for i in range(256):
            self.assertEqual(tok.vocab[i], bytes([i]))
        self.assertEqual(tok.vocab[256], SPECIAL_TOKEN.encode())
        self.assertEqual(len(tok.merges), 6)
        self.assertEqual(len(tok.vocab), FIRST_MERGE_ID + 6)
        for i, (a, b) in enumerate(tok.merges):
            self.assertLess(a, FIRST_MERGE_ID + i)
            self.assertLess(b, FIRST_MERGE_ID + i)
            self.assertNotIn(256, (a, b))
            self.assertEqual(tok.vocab[FIRST_MERGE_ID + i], tok.vocab[a] + tok.vocab[b])

    def test_merges_never_cross_words(self):
        """" ab" is one pre-token; "b" and the following space never join."""
        tok = self.train("ab ab ab ab", 10)
        self.assertEqual(merged_tokens(tok), [b"ab", b" ab"])

    def test_special_token_never_merged(self):
        """The marker's bytes occur only inside markers, so no merge may
        contain any of them, and no pair spans a marker."""
        text = ("xy" + SPECIAL_TOKEN) * 50 + "xy"
        tok = self.train(text, 20)
        self.assertEqual(merged_tokens(tok), [b"xy"])

    def test_urdu_letters_rebuilt_first(self):
        """Each Urdu letter is two bytes; on Urdu text the first merges join
        those byte pairs into letters (or longer pieces of them)."""
        word = "پاکستان"
        tok = self.train(lines((word, 10)), 1)
        self.assertEqual(len(merged_tokens(tok)[0]), 2)


class ReferenceTrainer(TrainingContract, unittest.TestCase):
    METHOD = "train_reference"


class FastTrainer(TrainingContract, unittest.TestCase):
    METHOD = "train_fast"

    def test_accepts_iterable_of_documents(self):
        docs = ["low low low", "lower newest", "widest newest"]
        a = train("train_fast", iter(docs), 10)
        b = train("train_fast", SPECIAL_TOKEN.join(docs), 10)
        self.assertEqual(a.merges, b.merges)


if __name__ == "__main__":
    unittest.main()
