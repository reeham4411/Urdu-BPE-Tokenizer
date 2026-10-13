r"""Check, from the cleaned files themselves, the facts the tokenizer relies on.

Usage (from the repository root):
    python -X utf8 tools/check_corpus_interface.py
    python -X utf8 tools/check_corpus_interface.py --splits val test

The corpus is only read. The findings are printed and saved as
<work>/corpus_interface_<splits>.json (see tools/datapaths.py for <work>).

Facts checked:
  1. Layout. Every document is followed by "\n<|endoftext|>\n", the marker is
     always a whole line, never appears anywhere else, and the file ends with
     it. The document byte lengths match doc_index.tsv row by row.
  2. Already normalised. normalize(doc) == doc, so the tokenizer must not
     call normalize.
  3. ZWNJ. Which characters sit on either side of U+200C. \p{L} does not
     match it (its category is Cf), so a letters-only pattern cuts there.
  4. Sources. Share of bytes per source, measured by joining the documents
     with doc_index.tsv, and whether UFAL lines look shuffled (neighbouring
     lines share fewer words than in the article sources).
  5. GPT-2's pattern. How many Urdu words it cuts into pieces.
"""
import argparse
import collections
import json
import sys
import time
import unicodedata
from pathlib import Path

import regex

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import normalize as N  # noqa: E402
from corpus_stats import WORD_RE, iter_docs  # noqa: E402
from tools.datapaths import END_OF_TEXT, ROOT, clean_dir, work_dir  # noqa: E402

ZWNJ = "\u200c"
SPLITS = ("train", "val", "test")
# The pattern printed in the handout. Used here only to measure how it fails.
GPT2_PATTERN = regex.compile(
    r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+""")
ARABIC_SCRIPT = regex.compile(r"\p{Arabic}")
MARK = regex.compile(r"\p{M}")


def read_index():
    for path in (clean_dir() / "doc_index.tsv", ROOT / "data" / "doc_index.tsv"):
        if path.exists():
            rows = collections.defaultdict(list)
            with path.open(encoding="utf-8") as fh:
                next(fh)
                for line in fh:
                    split, _pos, source, nbytes, _lines = line.rstrip("\n").split("\t")
                    rows[split].append((source, int(nbytes)))
            return path, rows
    sys.exit("doc_index.tsv not found")


def layout(path):
    """Byte-level checks on the separator."""
    data = path.read_bytes()
    marker = END_OF_TEXT.encode()
    sep = b"\n" + marker + b"\n"
    first = data.find(sep)
    return {
        "bytes": len(data),
        "marker_anywhere": data.count(marker),
        "marker_as_separator": data.count(sep),
        "ends_with_separator": data.endswith(sep),
        "carriage_returns": data.count(b"\r"),
        "tabs": data.count(b"\t"),
        "blank_lines": data.count(b"\n\n"),
        "around_first_marker": repr(data[first - 6:first + len(sep) + 6].decode("utf-8", "replace")),
    }


def adjacent_overlap(doc):
    """Mean Jaccard overlap of the word sets of neighbouring lines."""
    lines = [set(WORD_RE.findall(line)) for line in doc.split("\n")]
    scores = [len(a & b) / len(a | b) for a, b in zip(lines, lines[1:]) if a and b]
    return sum(scores) / len(scores) if scores else None


def audit_split(split, index_rows, every):
    path = clean_dir() / f"{split}.txt"
    out = {"layout": layout(path)}
    docs = 0
    index_mismatch = []
    not_normalised = []
    not_normalised_count = 0
    sampled = 0
    bytes_by_source = collections.Counter()
    zwnj = collections.Counter()
    zwnj_examples = []
    marks = collections.Counter()
    words_with_marks = words_checked = gpt2_split = 0
    gpt2_examples = collections.Counter()
    overlap = collections.defaultdict(list)
    edge_space = 0

    for pos, doc in enumerate(iter_docs(path)):
        docs += 1
        source, nbytes = index_rows[pos] if pos < len(index_rows) else ("?", -1)
        size = len(doc.encode("utf-8"))
        if size != nbytes and len(index_mismatch) < 5:
            index_mismatch.append((pos, size, nbytes))
        bytes_by_source[source] += size + len(END_OF_TEXT) + 2
        if doc != doc.strip():
            edge_space += 1
        if ZWNJ in doc:
            for i, ch in enumerate(doc):
                if ch != ZWNJ:
                    continue
                before = unicodedata.category(doc[i - 1]) if i else "start"
                after = unicodedata.category(doc[i + 1]) if i + 1 < len(doc) else "end"
                zwnj[f"{before}|{after}"] += 1
                if len(zwnj_examples) < 6:
                    lo = doc.rfind(" ", 0, i) + 1
                    hi = doc.find(" ", i)
                    zwnj_examples.append(doc[lo:hi if hi > 0 else len(doc)])
        if pos % every:
            continue
        sampled += 1
        fixed = N.normalize(doc)
        if fixed != doc:
            not_normalised_count += 1
            if len(not_normalised) < 5:
                i = next((k for k, (a, b) in enumerate(zip(doc, fixed)) if a != b),
                         min(len(doc), len(fixed)))
                not_normalised.append({"position": pos, "source": source,
                                       "file": repr(doc[max(0, i - 15):i + 15]),
                                       "normalised": repr(fixed[max(0, i - 15):i + 15])})
        ov = adjacent_overlap(doc)
        if ov is not None:
            overlap[source].append(ov)
        for word in WORD_RE.findall(doc):
            if not ARABIC_SCRIPT.search(word):
                continue
            words_checked += 1
            found = MARK.findall(word)
            if found:
                words_with_marks += 1
                marks.update(found)
            if len(GPT2_PATTERN.findall(word)) > 1:
                gpt2_split += 1
                gpt2_examples[word] += 1

    out.update({
        "documents": docs,
        "doc_index_rows": len(index_rows),
        "doc_index_byte_mismatches": index_mismatch,
        "docs_with_edge_whitespace": edge_space,
        "docs_normalise_checked": sampled,
        "docs_not_normalised": not_normalised_count,
        "not_normalised_examples": not_normalised,
        "bytes_by_source": dict(bytes_by_source),
        "zwnj_total": sum(zwnj.values()),
        "zwnj_neighbours": dict(zwnj.most_common()),
        "zwnj_examples": zwnj_examples,
        "urdu_words_checked": words_checked,
        "urdu_words_with_marks": words_with_marks,
        "marks": {f"U+{ord(c):04X} {unicodedata.name(c, '?')}": n
                  for c, n in marks.most_common(10)},
        "urdu_words_gpt2_cuts": gpt2_split,
        "gpt2_cut_examples": [w for w, _ in gpt2_examples.most_common(8)],
        "adjacent_line_overlap": {s: round(sum(v) / len(v), 4) for s, v in overlap.items()},
    })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--splits", nargs="*", default=list(SPLITS))
    ap.add_argument("--every", type=int, default=1,
                    help="run the slower per-word checks on every n-th document only")
    args = ap.parse_args()
    started = time.time()
    index_path, index = read_index()
    report = {"clean_dir": str(clean_dir()), "doc_index": str(index_path), "splits": {}}
    for split in args.splits:
        t = time.time()
        report["splits"][split] = audit_split(split, index[split], args.every)
        print(f"{split}: {time.time() - t:.0f} s", flush=True)
    total = collections.Counter()
    for s in report["splits"].values():
        total.update(s["bytes_by_source"])
    report["share_of_bytes"] = {k: round(v / sum(total.values()), 4) for k, v in total.items()}
    report["seconds"] = round(time.time() - started, 1)
    out = work_dir(create=True) / f"corpus_interface_{'_'.join(args.splits)}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"saved {out}")


if __name__ == "__main__":
    main()
