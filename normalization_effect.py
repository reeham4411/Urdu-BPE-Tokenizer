"""Measure how much normalisation shrinks the vocabulary.

Usage (from the repository root):
    python normalization_effect.py --input data/raw/ufal/document_000000.txt --mb 100
    python normalization_effect.py --input data/raw --mb 50 --markdown reports/normalization_effect.md

Reads about --mb megabytes of raw text (a file, or every .txt under a folder),
counts the distinct words before and after normalize(), and lists the most
frequent words whose spelling changes. Without normalisation a tokenizer sees
each spelling variant as a different word and spends merges on all of them.
"""
import argparse
import collections
import sys
from pathlib import Path

import regex

from normalize import normalize

STOP = chr(0x06D4)  # Urdu full stop
WORD_RE = regex.compile(r"[\p{L}\p{M}\p{N}\u200c]+")


def chunks(paths, limit_bytes, lines_per_chunk=200):
    used = 0
    for path in paths:
        block = []
        with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            for line in fh:
                block.append(line)
                used += len(line.encode("utf-8"))
                if len(block) >= lines_per_chunk:
                    yield "".join(block)
                    block = []
                if used >= limit_bytes:
                    break
        if block:
            yield "".join(block)
        if used >= limit_bytes:
            return


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--mb", type=float, default=50)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--markdown", type=Path)
    args = ap.parse_args()

    paths = [args.input] if args.input.is_file() else sorted(args.input.rglob("*.txt"))
    raw_counts, norm_counts = collections.Counter(), collections.Counter()
    changed = collections.Counter()
    changed_tokens = total_tokens = 0
    full_stops = spaced_full_stops = 0
    for text in chunks(paths, int(args.mb * 1e6)):
        full_stops += text.count(STOP)
        spaced_full_stops += text.count(" " + STOP)
        raw_words = WORD_RE.findall(text)
        raw_counts.update(raw_words)
        norm_counts.update(WORD_RE.findall(normalize(text)))
        total_tokens += len(raw_words)

    # A word is "changed" if normalising it alone gives a different spelling.
    for word, n in raw_counts.items():
        new = normalize(word)
        if new != word:
            changed[(word, new)] += n
            changed_tokens += n

    lines = [
        "| Measure | Raw | Normalised |",
        "|---|---:|---:|",
        f"| Word tokens | {total_tokens:,} | {sum(norm_counts.values()):,} |",
        f"| Distinct words | {len(raw_counts):,} | {len(norm_counts):,} |",
    ]
    drop = 1 - len(norm_counts) / len(raw_counts) if raw_counts else 0
    lines += ["", f"Normalisation removes {drop:.1%} of the distinct words. "
              f"{changed_tokens / total_tokens:.2%} of word tokens change spelling "
              f"({len(changed):,} distinct words).", "",
              f"Urdu full stops with a space before them: {spaced_full_stops:,} of {full_stops:,} "
              f"({spaced_full_stops / max(full_stops, 1):.1%}).", "",
              "Most frequent words that change:", "", "| Raw (code points) | Normalised | Count |", "|---|---|---:|"]
    for (old, new), n in changed.most_common(args.top):
        cps = " ".join("%04X" % ord(c) for c in old)
        lines.append(f"| {old} ({cps}) | {new} | {n:,} |")
    out = "\n".join(lines)
    print(out)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
