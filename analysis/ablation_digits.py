"""Measure what splitting every digit costs (section 2 of the report).

Usage (from the repository root, URDU_CLEAN_DIR pointing at the corpus the
final tokenizer was trained on):
    python -X utf8 -m analysis.ablation_digits

Trains a second tokenizer with BPETokenizer.train_fast on the same
train.txt, changing only the number branch of the pattern from one digit
(the final tokenizer) to one to three digits (our first version), and
compares both on test.txt: all tokens, and the tokens spent on numbers.
The variant is saved to <work>/ablation_digits_1to3.json so it is not
retrained by accident. Writes report/generated/ab_digits.md and
ab_digits.json. Training takes about as long as train_tokenizer.py.
"""
import json
import time

import bpe
from analysis.common import OURS_PATH, iter_docs, md_table, save, split_path
from tools.datapaths import work_dir

ONE_DIGIT = r"| ?\p{N}"
UP_TO_THREE = r"| ?\p{N}{1,3}"


def number_tokens(tok, docs):
    """Tokens spent on number pre-tokens, counted word by word."""
    rx = tok._regex if hasattr(tok, "_regex") else None
    total = 0
    for doc in docs:
        for piece in (rx.findall(doc) if rx else tok.pretokenize(doc)):
            if piece.strip().isdigit():
                total += len(tok.encode(piece))
    return total


def main():
    final = bpe.BPETokenizer.load(OURS_PATH)
    if ONE_DIGIT not in final.pattern:
        raise SystemExit(f"the final pattern has no {ONE_DIGIT!r} branch: {final.pattern}")
    variant_path = work_dir(create=True) / "ablation_digits_1to3.json"
    seconds = None
    if variant_path.exists():
        variant = bpe.BPETokenizer.load(variant_path)
    else:
        variant = bpe.BPETokenizer(final.pattern.replace(ONE_DIGIT, UP_TO_THREE))
        started = time.perf_counter()
        variant.train_fast(iter_docs(split_path("train")), len(final.vocab))
        seconds = round(time.perf_counter() - started, 1)
        variant.save(variant_path)

    docs = list(iter_docs(split_path("test")))
    rows, out = [], {}
    for name, tok in (("one digit per piece (final)", final),
                      ("one to three digits (variant)", variant)):
        tokens = sum(len(tok.encode(d)) for d in docs)
        numbers = number_tokens(tok, docs)
        out[name] = {"tokens": tokens, "number_tokens": numbers,
                     "digit_tokens_in_vocab": sum(1 for b in tok.vocab.values()
                                                  if b.strip().isdigit() and len(b.strip()) > 1)}
        rows.append([name, f"{tokens:,}", f"{numbers:,}"])
    a, b = (out[k]["tokens"] for k in out)
    na, nb = (out[k]["number_tokens"] for k in out)
    text = md_table(["Number rule", "test.txt tokens", "Tokens on numbers"], rows,
                    ["---", "---:", "---:"])
    text += (f"\nSplitting every digit costs {100 * (a - b) / b:.2f}% more tokens on test.txt "
             f"({a - b:,} tokens; numbers take {na / nb:.2f} times as many tokens) and frees "
             f"{out['one to three digits (variant)']['digit_tokens_in_vocab']:,} vocabulary "
             "slots that the variant spends on multi-digit numbers.\n")
    save("ab_digits.md", text)
    save("ab_digits.json", {"variant_training_seconds": seconds, "results": out,
                            "extra_tokens_percent": round(100 * (a - b) / b, 3)})
    print(text)


if __name__ == "__main__":
    main()
