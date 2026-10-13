"""Clean the raw Urdu sources and write train.txt, val.txt and test.txt.

Usage (from the repository root):
    python clean_corpus.py
    python clean_corpus.py --raw data/raw --out data/clean --seed 1337

Input is data/raw/<source>/*.txt as left by the collection scripts. A source is
either a folder of one-document-per-file text (Wikipedia, Wikisource) or a
"line source" such as UFAL, which is one huge file of one sentence per line.
Line sources are cut into documents at blank lines, or every --chunk-lines
lines when there are no blank lines.

Steps, in order (each one logs the bytes it removed):
    1. markup        strip HTML, wiki markup, entities, <|endoftext|> strings
    2. normalize     normalize.normalize (Unicode, digits, whitespace)
    3. tail          cut reference and link sections of encyclopedia articles
    4. personal      remove URLs, e-mails, handles, phone and ID numbers
    5. language      drop lines that are mostly not Urdu
    6. non-Urdu doc  drop documents in Arabic script that are not Urdu
    7. exact dup     drop documents identical to an earlier one
    8. boilerplate   drop lines that occur in many different documents
    9. near dup      drop documents whose lines were mostly seen before
   10. short         drop documents with very few words
   11. split         98/1/1 by document with a fixed seed, per source

Everything runs in one process, because lines are compared through Python's
hash(), which is only stable inside a process.
"""
import argparse
import array
import collections
import json
import os
import platform
import random
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from tqdm import tqdm

import normalize as N
import textclean as T

ROOT = Path(__file__).resolve().parent
END = T.END_OF_TEXT
FULL_STOP = chr(0x06D4)  # Urdu full stop
RECORD_SEP = "\x1e"  # removed by normalize, so it never occurs inside a document

# Per-source behaviour. Unknown folders are treated as plain one-file documents.
SOURCES = {
    "urwiki": dict(genre="encyclopedia", wiki=True, tail=True),
    "wikipedia_dump": dict(genre="encyclopedia", wiki=True, tail=True),
    "urwikisource": dict(genre="literature", wiki=True, tail=False),
    "ufal": dict(genre="mixed web text", wiki=False, tail=False, lines=True),
}
DEFAULT_CFG = dict(genre="unknown", wiki=False, tail=False, lines=False)

STEPS = [
    ("markup", "HTML, wiki markup and entities"),
    ("normalize", "Unicode normalisation"),
    ("tail", "reference and link sections"),
    ("personal", "URLs, e-mails, phone and ID numbers"),
    ("language", "lines that are mostly not Urdu"),
    ("nonurdu_doc", "documents in Arabic script that are not Urdu"),
    ("exact_dup", "exact duplicate documents"),
    ("boilerplate", "boilerplate lines repeated across documents"),
    ("near_dup", "near-duplicate documents"),
    ("short", "documents with too few words"),
]


def nbytes(text):
    return len(text.encode("utf-8"))


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def iter_file_docs(folder, limit):
    """One document per file. Yields (doc_id, raw_bytes, text)."""
    used = 0
    for path in sorted(folder.rglob("*.txt")):
        raw = path.read_bytes()
        yield path.stem, len(raw), raw.decode("utf-8", errors="replace")
        used += len(raw)
        if limit and used >= limit:
            return


def iter_line_docs(folder, chunk_lines, limit):
    """Cut sentence-per-line files into documents. Yields like iter_file_docs."""
    used = 0
    count = 0
    for path in sorted(folder.rglob("*.txt")):
        block, block_bytes = [], 0
        with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            for line in fh:
                size = len(line.encode("utf-8"))
                used += size
                block_bytes += size
                if line.strip():
                    block.append(line)
                if (not line.strip() or len(block) >= chunk_lines) and block:
                    yield f"{path.stem}#{count}", block_bytes, "".join(block)
                    count += 1
                    block, block_bytes = [], 0
                if limit and used >= limit:
                    break
        if block:
            yield f"{path.stem}#{count}", block_bytes, "".join(block)
            count += 1
        if limit and used >= limit:
            return


# ---------------------------------------------------------------------------
# Stage 1: per-document cleaning
# ---------------------------------------------------------------------------
class SourceStats:
    def __init__(self, name, cfg):
        self.name = name
        self.genre = cfg["genre"]
        self.raw_bytes = 0
        self.docs_read = 0
        self.removed = collections.Counter()      # step -> bytes removed
        self.docs_removed = collections.Counter()  # step -> documents removed
        self.lines_removed = collections.Counter()  # step -> lines removed
        self.scrubbed = collections.Counter()      # kind -> count
        self.chars = collections.Counter()         # raw character counts
        self.spaced_full_stops = 0                 # raw full stops with a space before them
        self.lines_read = 0
        self.docs_kept = 0
        self.final_bytes = 0

    def as_dict(self):
        return {
            "genre": self.genre,
            "raw_bytes": self.raw_bytes,
            "docs_read": self.docs_read,
            "lines_read": self.lines_read,
            "bytes_removed": dict(self.removed),
            "docs_removed": dict(self.docs_removed),
            "lines_removed": dict(self.lines_removed),
            "scrubbed": dict(self.scrubbed),
            "full_stops": self.chars.get(FULL_STOP, 0),
            "spaced_full_stops": self.spaced_full_stops,
            "docs_kept": self.docs_kept,
            "final_bytes": self.final_bytes,
        }


def stage1(name, cfg, folder, args, work_dir, seen_docs, line_hashes, examples):
    """Clean every document of one source and write survivors to work_dir."""
    st = SourceStats(name, cfg)
    limit = int(args.limit_mb * 1e6) if args.limit_mb else 0
    if cfg["lines"]:
        docs = iter_line_docs(folder, args.chunk_lines, limit)
    else:
        docs = iter_file_docs(folder, limit)
    total = sum(p.stat().st_size for p in folder.rglob("*.txt"))
    if limit:
        total = min(total, limit)
    out_path = work_dir / f"{name}.stage1"
    bar = tqdm(total=total, unit="B", unit_scale=True, desc=name, leave=False, disable=args.quiet)
    with out_path.open("w", encoding="utf-8", newline="\n") as out:
        for doc_id, raw_bytes, text in docs:
            bar.update(raw_bytes)
            st.docs_read += 1
            st.raw_bytes += raw_bytes
            st.chars.update(text)
            st.spaced_full_stops += text.count(" " + FULL_STOP)

            t = T.strip_markup(text, wiki=cfg["wiki"])
            b_prev = nbytes(t)
            st.removed["markup"] += raw_bytes - b_prev

            t = N.normalize(t)
            b = nbytes(t)
            st.removed["normalize"] += b_prev - b
            b_prev = b

            if cfg["tail"]:
                t = T.cut_tail_sections(t)
                b = nbytes(t)
                st.removed["tail"] += b_prev - b
                b_prev = b

            t, counts = T.scrub_personal(t)
            st.scrubbed.update(counts)
            b = nbytes(t)
            st.removed["personal"] += b_prev - b
            b_prev = b

            t, lines_in, lines_dropped = T.filter_lines(
                t, args.min_ratio, args.min_urdu_letters)
            st.lines_read += lines_in
            st.lines_removed["language"] += lines_dropped
            t = t.strip()
            b = nbytes(t)
            st.removed["language"] += b_prev - b
            b_prev = b

            if not t:
                st.docs_removed["language"] += 1
                continue
            if not T.is_urdu_document(t, args.min_function_rate):
                st.docs_removed["nonurdu_doc"] += 1
                st.removed["nonurdu_doc"] += b_prev
                if len(examples["nonurdu_doc"]) < 15:
                    examples["nonurdu_doc"].append((name, doc_id, t[:300].replace("\n", " ")))
                continue
            digest = hash(t)
            if digest in seen_docs:
                st.docs_removed["exact_dup"] += 1
                st.removed["exact_dup"] += b_prev
                continue
            seen_docs.add(digest)

            out.write(t)
            out.write("\n" + RECORD_SEP + "\n")
            for line in set(t.split("\n")):
                line_hashes.append(hash(line))
    bar.close()
    return st, out_path


def read_records(path):
    """Yield the documents of a stage-1 file."""
    block = []
    with path.open("r", encoding="utf-8", newline="\n") as fh:
        for line in fh:
            if line == RECORD_SEP + "\n":
                yield "".join(block)[:-1] if block else ""
                block = []
            else:
                block.append(line)


# ---------------------------------------------------------------------------
# Stage 2: corpus-wide steps
# ---------------------------------------------------------------------------
def boilerplate_hashes(line_hashes, min_docs):
    arr = np.frombuffer(line_hashes, dtype=np.int64)
    if not len(arr):
        return set()
    values, counts = np.unique(arr, return_counts=True)
    return set(values[counts >= min_docs].tolist())


def stage2(name, path, st, boiler, seen_lines, args, work_dir, examples):
    """Boilerplate, near duplicates, short documents. Returns the index of
    surviving documents as (offset, length) pairs into <name>.final."""
    final_path = work_dir / f"{name}.final"
    index = []
    with final_path.open("wb") as out:
        for text in read_records(path):
            lines = text.split("\n")
            kept = []
            for line in lines:
                if hash(line) in boiler:
                    examples["boilerplate"][line] += 1
                else:
                    kept.append(line)
            new_text = "\n".join(kept)
            st.lines_removed["boilerplate"] += len(lines) - len(kept)
            st.removed["boilerplate"] += nbytes(text) - nbytes(new_text)
            if not kept:
                st.docs_removed["boilerplate"] += 1
                continue
            hashes = [hash(line) for line in kept]
            if len(kept) >= 4:
                seen = sum(h in seen_lines for h in hashes)
                if seen >= args.near_dup * len(kept):
                    st.docs_removed["near_dup"] += 1
                    st.removed["near_dup"] += nbytes(new_text)
                    continue
            if len(new_text.split()) < args.min_words:
                st.docs_removed["short"] += 1
                st.removed["short"] += nbytes(new_text)
                continue
            seen_lines.update(hashes)
            data = new_text.encode("utf-8")
            index.append((out.tell(), len(data), len(kept)))
            out.write(data)
            st.docs_kept += 1
            st.final_bytes += len(data)
    return final_path, index


# ---------------------------------------------------------------------------
# Split and write
# ---------------------------------------------------------------------------
def assign_splits(sizes, seed, val_frac, test_frac):
    """sizes: {source: n_docs}. Returns {source: (train_ids, val_ids, test_ids)}.
    Each source is shuffled on its own so every genre appears in all splits."""
    result = {}
    for name, n in sizes.items():
        rng = random.Random(f"{seed}:{name}")
        order = list(range(n))
        rng.shuffle(order)
        n_val = round(n * val_frac)
        n_test = round(n * test_frac)
        if n >= 5:
            n_val, n_test = max(n_val, 1), max(n_test, 1)
        result[name] = (order[n_val + n_test:], order[:n_val], order[n_val:n_val + n_test])
    return result


def write_splits(out_dir, finals, indexes, splits, seed):
    out_dir.mkdir(parents=True, exist_ok=True)
    handles = {name: finals[name].open("rb") for name in finals}
    rows = []
    summary = {}
    try:
        for split_no, split_name in enumerate(("train", "val", "test")):
            pairs = [(name, i) for name in splits for i in splits[name][split_no]]
            random.Random(f"{seed}:{split_name}").shuffle(pairs)
            total = 0
            with (out_dir / f"{split_name}.txt").open("wb") as out:
                for pos, (name, i) in enumerate(pairs):
                    offset, length, n_lines = indexes[name][i]
                    handles[name].seek(offset)
                    out.write(handles[name].read(length))
                    out.write(("\n" + END + "\n").encode("utf-8"))
                    total += length + len(END) + 2
                    rows.append((split_name, pos, name, length, n_lines))
            summary[split_name] = {"docs": len(pairs), "bytes": total}
    finally:
        for fh in handles.values():
            fh.close()
    with (out_dir / "doc_index.tsv").open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("split\tposition\tsource\tbytes\tlines\n")
        for row in rows:
            fh.write("\t".join(map(str, row)) + "\n")
    return summary


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def build_report(stats, summary, args, elapsed, boiler_count, examples):
    totals = collections.Counter()
    removed = collections.Counter()
    docs_removed = collections.Counter()
    lines_removed = collections.Counter()
    for st in stats.values():
        totals["raw_bytes"] += st.raw_bytes
        totals["docs_read"] += st.docs_read
        totals["lines_read"] += st.lines_read
        totals["docs_kept"] += st.docs_kept
        totals["final_bytes"] += st.final_bytes
        removed.update(st.removed)
        docs_removed.update(st.docs_removed)
        lines_removed.update(st.lines_removed)
    chars = collections.Counter()
    for st in stats.values():
        chars.update(st.chars)
    rules = N.rule_counts(chars)
    ascii_digits = sum(chars.get(d, 0) for d in "0123456789")
    return {
        "settings": {k: v for k, v in vars(args).items() if not isinstance(v, Path)},
        "machine": {"python": platform.python_version(), "platform": platform.platform(),
                    "processor": platform.processor()},
        "seconds": round(elapsed, 1),
        "totals": dict(totals),
        "bytes_removed": {k: removed.get(k, 0) for k, _ in STEPS},
        "docs_removed": {k: docs_removed.get(k, 0) for k, _ in STEPS},
        "lines_removed": dict(lines_removed),
        "boilerplate_distinct_lines": boiler_count,
        "normalization_rule_counts": rules,
        "ascii_digit_count": ascii_digits,
        "full_stops": sum(st.chars.get(FULL_STOP, 0) for st in stats.values()),
        "spaced_full_stops": sum(st.spaced_full_stops for st in stats.values()),
        "scrubbed": {k: sum(st.scrubbed.get(k, 0) for st in stats.values())
                     for k in ("url", "email", "handle", "phone")},
        "per_source": {name: st.as_dict() for name, st in stats.items()},
        "per_source_rule_counts": {name: N.rule_counts(st.chars) for name, st in stats.items()},
        "splits": summary,
        "examples": {
            "nonurdu_doc": examples["nonurdu_doc"],
            "boilerplate": examples["boilerplate"].most_common(40),
        },
    }


def write_markdown(report, path):
    lines = ["# Cleaning report", "",
             f"Run time: {report['seconds']} s on {report['machine']['platform']}, "
             f"Python {report['machine']['python']}.", "",
             "## Bytes removed by each step", "",
             "| Step | What | Bytes removed | MB | Documents removed |",
             "|---|---|---:|---:|---:|"]
    for key, label in STEPS:
        b = report["bytes_removed"][key]
        lines.append(f"| {key} | {label} | {b:,} | {b / 1e6:.2f} | "
                     f"{report['docs_removed'].get(key, 0):,} |")
    t = report["totals"]
    lines += ["", f"Raw: {t['raw_bytes']:,} bytes. Final: {t['final_bytes']:,} bytes "
              f"in {t['docs_kept']:,} documents.", "", "## Per source", "",
              "| Source | Raw MB | Final MB | Documents kept | Documents read |",
              "|---|---:|---:|---:|---:|"]
    for name, s in report["per_source"].items():
        lines.append(f"| {name} | {s['raw_bytes'] / 1e6:.2f} | {s['final_bytes'] / 1e6:.2f} | "
                     f"{s['docs_kept']:,} | {s['docs_read']:,} |")
    lines += ["", "## Normalisation rules, characters affected", "",
              "| Rule | Characters |", "|---|---:|"]
    for rule, n in report["normalization_rule_counts"].items():
        lines.append(f"| {rule} | {n:,} |")
    lines += ["", f"ASCII digits in the raw text: {report['ascii_digit_count']:,}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "clean")
    ap.add_argument("--work", type=Path, default=ROOT / "data" / "interim")
    ap.add_argument("--reports", type=Path, default=ROOT / "reports")
    ap.add_argument("--sources", nargs="*", help="folders of --raw to use (default: all)")
    ap.add_argument("--line-source", action="append", default=[],
                    help="treat this source as one sentence per line (repeatable)")
    ap.add_argument("--chunk-lines", type=int, default=40,
                    help="lines per document for line sources without blank lines")
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--val-frac", type=float, default=0.01)
    ap.add_argument("--test-frac", type=float, default=0.01)
    ap.add_argument("--min-ratio", type=float, default=0.5,
                    help="minimum share of Urdu letters among the letters of a line")
    ap.add_argument("--min-urdu-letters", type=int, default=2)
    ap.add_argument("--min-function-rate", type=float, default=0.05)
    ap.add_argument("--boilerplate-min-docs", type=int, default=10)
    ap.add_argument("--near-dup", type=float, default=0.8)
    ap.add_argument("--min-words", type=int, default=10)
    ap.add_argument("--limit-mb", type=float, default=0, help="read at most this much per source (testing)")
    ap.add_argument("--keep-work", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    started = time.time()
    names = args.sources or sorted(p.name for p in args.raw.iterdir()
                                   if p.is_dir() and any(p.rglob("*.txt")))
    if not names:
        sys.exit(f"No text found under {args.raw}")
    for extra in args.line_source:
        SOURCES.setdefault(extra, dict(DEFAULT_CFG))["lines"] = True
    args.work.mkdir(parents=True, exist_ok=True)
    args.reports.mkdir(parents=True, exist_ok=True)

    seen_docs, line_hashes = set(), array.array("q")
    examples = {"nonurdu_doc": [], "boilerplate": collections.Counter()}
    stats, stage1_files = {}, {}
    for name in names:
        cfg = dict(DEFAULT_CFG, **SOURCES.get(name, {}))
        print(f"[1/3] cleaning {name} ({cfg['genre']})", flush=True)
        stats[name], stage1_files[name] = stage1(
            name, cfg, args.raw / name, args, args.work, seen_docs, line_hashes, examples)
    del seen_docs

    boiler = boilerplate_hashes(line_hashes, args.boilerplate_min_docs)
    del line_hashes
    print(f"[2/3] {len(boiler):,} boilerplate lines; removing them, near duplicates and short documents", flush=True)
    seen_lines, finals, indexes = set(), {}, {}
    for name in names:
        finals[name], indexes[name] = stage2(
            name, stage1_files[name], stats[name], boiler, seen_lines, args, args.work, examples)
        stage1_files[name].unlink()
    del seen_lines

    print("[3/3] splitting and writing", flush=True)
    splits = assign_splits({n: len(indexes[n]) for n in names}, args.seed, args.val_frac, args.test_frac)
    summary = write_splits(args.out, finals, indexes, splits, args.seed)

    report = build_report(stats, summary, args, time.time() - started, len(boiler), examples)
    (args.reports / "cleaning_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    write_markdown(report, args.reports / "cleaning_report.md")
    if not args.keep_work:
        shutil.rmtree(args.work, ignore_errors=True)
    print(json.dumps({"seconds": report["seconds"], "totals": report["totals"],
                      "splits": summary}, indent=1))


if __name__ == "__main__":
    main()
