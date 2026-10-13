"""Measure and audit the cleaned corpus.

Usage (from the repository root):
    python corpus_stats.py
    python corpus_stats.py --clean data/clean --out reports/corpus_stats.json

Reads train.txt, val.txt, test.txt and doc_index.tsv written by clean_corpus.py
and reports, per split and per source: megabytes, documents, words and unique
words. A "word" is a run of letters, combining marks, digits or ZWNJ, so
punctuation never counts as a word and a diacritic never splits one.

It also audits the files, so the numbers can be trusted:
    * every document ends with <|endoftext|> and none is empty,
    * the files are valid UTF-8,
    * none of the characters that normalize.py removes or maps is left,
    * the out-of-vocabulary rate of val and test against train.
"""
import argparse
import collections
import json
import sys
import time
import unicodedata
from pathlib import Path

import regex

import normalize as N
from textclean import END_OF_TEXT

ROOT = Path(__file__).resolve().parent
SPLITS = ("train", "val", "test")
WORD_RE = regex.compile(r"[\p{L}\p{M}\p{N}\u200c]+")
SEP = "\n" + END_OF_TEXT + "\n"


def iter_docs(path):
    """Yield the documents of a split file, one at a time."""
    block = []
    with path.open("r", encoding="utf-8", newline="\n") as fh:
        for line in fh:
            if line == END_OF_TEXT + "\n":
                if not block:
                    raise ValueError(f"{path}: empty document")
                yield "".join(block)[:-1]  # drop the newline before the marker
                block = []
            else:
                block.append(line)
    if block:
        raise ValueError(f"{path}: text after the last {END_OF_TEXT}")


def forbidden_characters():
    """Characters that a normalised text must not contain."""
    banned = set(N.LETTER_MAP) | set(N.DIGIT_MAP) | set(N.NUMBER_PUNCT_MAP) | set(N.PUNCT_MAP)
    banned |= N.TATWEEL | N.INVISIBLE | N.ANNOTATIONS | N.CONTROLS | N.PRIVATE_USE
    banned |= N.SPACE_CHARS | (N.NEWLINE_CHARS - {"\n"})
    return banned - {"\n"}


def read_index(path):
    rows = {s: [] for s in SPLITS}
    with path.open(encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            split, _pos, source, nbytes, nlines = line.rstrip("\n").split("\t")
            rows[split].append((source, int(nbytes), int(nlines)))
    return rows


def percentile(sorted_values, q):
    if not sorted_values:
        return 0
    return sorted_values[min(len(sorted_values) - 1, int(q * len(sorted_values)))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clean", type=Path, default=ROOT / "data" / "clean")
    ap.add_argument("--out", type=Path, default=ROOT / "reports" / "corpus_stats.json")
    args = ap.parse_args()

    started = time.time()
    index = read_index(args.clean / "doc_index.tsv")
    banned = forbidden_characters()

    per_split = {}
    per_source = collections.defaultdict(lambda: {"docs": 0, "bytes": 0, "words": 0, "lines": 0})
    source_vocab = collections.defaultdict(set)
    train_vocab = collections.Counter()
    heldout_tokens = {"val": collections.Counter(), "test": collections.Counter()}
    all_vocab = set()
    char_counts = collections.Counter()
    doc_words = []
    problems = []

    for split in SPLITS:
        path = args.clean / f"{split}.txt"
        size = path.stat().st_size
        docs = words = lines = 0
        vocab = set()
        for pos, doc in enumerate(iter_docs(path)):
            if pos >= len(index[split]):
                problems.append(f"{split}: more documents than doc_index rows")
                break
            source = index[split][pos][0]
            tokens = WORD_RE.findall(doc)
            docs += 1
            words += len(tokens)
            lines += doc.count("\n") + 1
            vocab.update(tokens)
            source_vocab[source].update(tokens)
            doc_words.append(len(tokens))
            char_counts.update(doc)
            ps = per_source[(split, source)]
            ps["docs"] += 1
            ps["bytes"] += len(doc.encode("utf-8")) + len(SEP.encode("utf-8"))
            ps["words"] += len(tokens)
            ps["lines"] += doc.count("\n") + 1
            if split == "train":
                train_vocab.update(tokens)
            else:
                heldout_tokens[split].update(tokens)
            if doc != doc.strip() or "\n\n" in doc or END_OF_TEXT in doc:
                problems.append(f"{split}: badly formed document at position {pos}")
        if docs != len(index[split]):
            problems.append(f"{split}: {docs} documents but doc_index lists {len(index[split])}")
        all_vocab |= vocab
        per_split[split] = {"bytes": size, "mb": round(size / 1e6, 2), "documents": docs,
                            "words": words, "unique_words": len(vocab), "lines": lines}

    leftovers = {f"U+{ord(c):04X}": n for c, n in char_counts.items() if c in banned}
    if leftovers:
        problems.append(f"characters that normalize.py removes or maps are still present: {leftovers}")

    def oov(split):
        tokens = heldout_tokens[split]
        total = sum(tokens.values())
        miss = sum(n for w, n in tokens.items() if w not in train_vocab)
        types = len(tokens)
        miss_types = sum(1 for w in tokens if w not in train_vocab)
        return {"token_rate": round(miss / total, 5) if total else 0.0,
                "type_rate": round(miss_types / types, 5) if types else 0.0}

    letters = collections.Counter()
    for ch, n in char_counts.items():
        cat = unicodedata.category(ch)
        if cat[0] == "L":
            name = "urdu_script" if "؀" <= ch <= "ۿ" or "ݐ" <= ch <= "ݿ" else (
                "latin" if ch.isascii() or unicodedata.name(ch, "").startswith("LATIN") else "other")
            letters[name] += n
        elif cat == "Nd":
            letters["digits"] += n
    total_letters = sum(v for k, v in letters.items() if k != "digits") or 1

    total = {k: sum(p[k] for p in per_split.values()) for k in ("bytes", "documents", "words", "lines")}
    total["mb"] = round(total["bytes"] / 1e6, 2)
    total["unique_words"] = len(all_vocab)
    sources = {}
    for (split, source), v in per_source.items():
        s = sources.setdefault(source, {"docs": 0, "bytes": 0, "words": 0, "lines": 0})
        for k in s:
            s[k] += v[k]
    for source, s in sources.items():
        s["mb"] = round(s["bytes"] / 1e6, 2)
        s["unique_words"] = len(source_vocab[source])
        s["share_of_bytes"] = round(s["bytes"] / total["bytes"], 4)
    doc_words.sort()
    top = train_vocab.most_common(30)
    report = {
        "seconds": round(time.time() - started, 1),
        "splits": per_split,
        "total": total,
        "per_source": sources,
        "per_source_split": {f"{k[0]}/{k[1]}": v for k, v in per_source.items()},
        "oov_against_train": {"val": oov("val"), "test": oov("test")},
        "document_words": {"median": percentile(doc_words, 0.5), "p10": percentile(doc_words, 0.1),
                           "p90": percentile(doc_words, 0.9), "max": doc_words[-1] if doc_words else 0},
        "letter_share": {k: round(v / total_letters, 4) for k, v in letters.items() if k != "digits"},
        "digits": letters.get("digits", 0),
        "zwnj_in_corpus": char_counts.get("\u200c", 0),
        "top_words": top,
        "problems": problems,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("splits", "total", "oov_against_train", "problems")},
                     ensure_ascii=False, indent=1))
    if problems:
        sys.exit("Audit found problems, see above.")


if __name__ == "__main__":
    main()
