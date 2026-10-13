r"""train_fast must learn exactly the merges train_reference learns.

Run from the repository root:
    python -X utf8 -m unittest tests.test_fast_matches_reference -v

Two parts:
  * many small random corpora (seconds), which find most bugs in the
    incremental pair updates: overlapping pairs ("aaaa"), a pair whose two
    halves are the same token, words where one merge occurs twice, and
    markers between documents;
  * the 1 MB sample of train.txt (tools/make_sample.py), as the handout asks.
    The reference trainer is slow, so the number of merges is set by
    BPE_SAMPLE_MERGES (default 500; use 0 to skip this part). The result,
    with both timings, is saved to <work>/fast_vs_reference.json for the
    report.
"""
import json
import os
import random
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # finds bpe_testlib
from bpe_testlib import (FIRST_MERGE_ID, SEED, SPECIAL_TOKEN, ZWNJ, datapaths,  # noqa: E402,F401
                         env_int, merged_tokens, train)

SAMPLE_MERGES = env_int("BPE_SAMPLE_MERGES", 500)
ALPHABETS = ["ab", "abc", "aab ", "ab \n", "اب ", "ا\u064fب" + ZWNJ + " ", "😀a "]


def random_corpus(rng):
    alphabet = rng.choice(ALPHABETS)
    words = ["".join(rng.choice(alphabet) for _ in range(rng.randrange(1, 9)))
             for _ in range(rng.randrange(3, 30))]
    docs = [" ".join(rng.choice(words) for _ in range(rng.randrange(1, 40)))
            for _ in range(rng.randrange(1, 4))]
    return SPECIAL_TOKEN.join(docs)


def first_difference(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return None if len(a) == len(b) else min(len(a), len(b))


class FastMatchesReference(unittest.TestCase):
    def compare(self, text, n_merges, label):
        ref = train("train_reference", text, n_merges)
        fast = train("train_fast", text, n_merges)
        i = first_difference(ref.merges, fast.merges)
        if i is not None:
            r, f = merged_tokens(ref), merged_tokens(fast)
            self.fail(f"{label}: merge {i + 1} differs: reference "
                      f"{r[i] if i < len(r) else 'none'!r}, fast "
                      f"{f[i] if i < len(f) else 'none'!r} "
                      f"(lengths {len(r)} and {len(f)})")
        return ref, fast

    def test_random_small_corpora(self):
        rng = random.Random(SEED)
        for k in range(200):
            text = random_corpus(rng)
            with self.subTest(corpus=k):
                self.compare(text, rng.randrange(1, 60), f"corpus {k} {text[:40]!r}")

    def test_repeated_letters(self):
        for text in ("aaaa aaaaa aaa", "abab ababab", "aaab aab ab", "a a a a"):
            with self.subTest(text=text):
                self.compare(text, 20, repr(text))

    @unittest.skipIf(SAMPLE_MERGES <= 0, "BPE_SAMPLE_MERGES=0")
    @unittest.skipUnless(datapaths.sample_path().exists(),
                         "no 1 MB sample; run tools/make_sample.py")
    def test_one_megabyte_sample(self):
        path = datapaths.sample_path()
        text = path.read_text(encoding="utf-8")
        t0 = time.perf_counter()
        ref = train("train_reference", text, SAMPLE_MERGES)
        t1 = time.perf_counter()
        fast = train("train_fast", text, SAMPLE_MERGES)
        t2 = time.perf_counter()
        i = first_difference(ref.merges, fast.merges)
        result = {
            "sample": str(path),
            "sample_bytes": path.stat().st_size,
            "merges_requested": SAMPLE_MERGES,
            "merges_reference": len(ref.merges),
            "merges_fast": len(fast.merges),
            "identical": i is None,
            "first_difference": i,
            "seconds_reference": round(t1 - t0, 2),
            "seconds_fast": round(t2 - t1, 2),
            "first_20_merges": [t.decode("utf-8", "replace") for t in merged_tokens(fast)[:20]],
        }
        out = datapaths.work_dir(create=True) / "fast_vs_reference.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n{json.dumps(result, ensure_ascii=False)}")
        self.assertEqual(len(fast.merges), SAMPLE_MERGES)
        self.assertIsNone(i, f"first difference at merge {i}; see {out}")


if __name__ == "__main__":
    unittest.main()
