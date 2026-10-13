"""Shared helpers for the tokenizer tests (not a test module itself).

The tests are written against the interface documented in bpe.py:
BPETokenizer.train_reference / train_fast / encode / decode / save / load /
pretokenize, and the attributes merges (list of ID pairs) and vocab (ID ->
bytes).
"""
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bpe import FIRST_MERGE_ID, SPECIAL_ID, SPECIAL_TOKEN, BPETokenizer  # noqa: E402,F401
from tools import datapaths  # noqa: E402,F401

ZWNJ = "\u200c"
# Urdu test words, spelled with escapes where an invisible character matters.
URDU = "\u0627\u0631\u062f\u0648"                             # urdu, no marks
URDU_MARKED = "\u0627\u064f\u0631\u062f\u064f\u0648"            # with two pesh
INTERNATIONAL = "\u0628\u06cc\u0646" + ZWNJ + "\u0627\u0644\u0627\u0642\u0648\u0627\u0645\u06cc"

# A small mixed corpus for training throwaway tokenizers in the tests.
MIXED_CORPUS = "\n".join([
    "اردو پاکستان کی قومی زبان ہے۔ یہ زبان برصغیر میں بولی جاتی ہے۔",
    "کراچی پاکستان کا سب سے بڑا شہر ہے اور یہاں کی آبادی بہت زیادہ ہے۔",
    URDU_MARKED + " ادب میں غالب اور اقبال کا مقام بہت بلند ہے۔",
    INTERNATIONAL + " تعلقات پر " + "تعالیٰ" + " اور " + "تقریباً" + " 1947 میں",
    "آج AI کے بارے میں ایک meeting تھی، جو 3:30 PM پر ختم ہوئی۔",
    "The quick brown fox jumps over the lazy dog. It's 2026!",
    "emoji: 😀 👍🏽 🇵🇰 and 👨‍👩‍👧 family",
]) + "\n" + SPECIAL_TOKEN + "\n"
MIXED_CORPUS = MIXED_CORPUS * 8


def lines(*word_counts):
    """("low", 5), ("lower", 2) -> "low\nlow\n...". Words on their own lines
    have no leading space, so each one is a single pre-token."""
    return "\n".join(w for w, n in word_counts for _ in range(n))


def train(method, text, n_merges):
    """Train a fresh tokenizer with method 'train_reference' or 'train_fast'."""
    tok = BPETokenizer()
    getattr(tok, method)(text, FIRST_MERGE_ID + n_merges)
    return tok


def merged_tokens(tok):
    """The byte strings created by the merges, in order."""
    return [tok.vocab[FIRST_MERGE_ID + i] for i in range(len(tok.merges))]


def token_bytes(tok, ids):
    return [tok.vocab[i] for i in ids]


# Pools for random strings. Lone surrogates are left out: they are not
# Unicode scalar values and cannot be encoded as UTF-8 at all.
POOLS = [
    "abcxyz ABC 0123456789",
    "".join(chr(c) for c in range(0x0621, 0x064B)) + "ٹپچڈڑژکگںھہۂۃیےۓ۔،؟",
    "".join(chr(c) for c in range(0x064B, 0x0653)) + "\u0670" + ZWNJ,
    " \n\t\r\u00a0\u2028   \n\n",
    "😀👍🏽🇵🇰👨‍👩‍👧\u200d\ufe0f",
    ".,;:!?'\"()[]{}<>|/\\-_=+*&^%$#@~`",
    "<|endoftext",
]


def random_text(rng, length):
    """A random string mixing the pools above with arbitrary code points."""
    out = []
    for _ in range(length):
        if rng.random() < 0.15:
            c = rng.randrange(0x110000)
            while 0xD800 <= c <= 0xDFFF:
                c = rng.randrange(0x110000)
            out.append(chr(c))
        else:
            out.append(rng.choice(rng.choice(POOLS)))
    return "".join(out)


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


SEED = 417
