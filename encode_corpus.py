r"""Encode train.txt and val.txt with the trained tokenizer into train.bin and val.bin.

Usage (from the repository root):
    python -X utf8 encode_corpus.py
    python -X utf8 encode_corpus.py --tokenizer tokenizer/urdu_bpe.json --splits train val --workers 4

Output format (read directly by Assignment 2):
    A flat array of token IDs, dtype numpy.uint16 (max 65,535, enough for
    50,000 IDs), little-endian, no header. Read it back with
    numpy.fromfile(path, dtype=numpy.uint16) or numpy.memmap.
    Default location: the work folder, tools.datapaths.work_dir(), so the
    cleaned corpus folder is never written to. The .bin files are shared by
    link, not committed (.gitignore has *.bin).

Layout (must match tools/check_bins.py --layout):
    The file is   doc1 \n <|endoftext|> \n doc2 \n <|endoftext|> \n ...
    drop-after (default, as M2's README says): split on the marker and drop
        the one newline after it, so each document gives encode(doc + "\n")
        followed by 256, and the stream ends with 256;
    drop-both: encode(doc) then 256;
    exact: the IDs decode back to the file byte for byte.

How:
    Documents are read one at a time and encoded with BPETokenizer.encode
    (which uses its per-word cache, the third optimisation). With --workers
    above 1 each worker process loads the tokenizer once and keeps its own
    cache; documents come back in order. IDs are buffered and appended to the
    .bin every --flush-every IDs, so memory stays flat; train has a few
    hundred million IDs, which as a Python list would need gigabytes. Every
    ID is checked to be below 50,000 before the cast to uint16. The output is
    written to <name>.bin.tmp and renamed only when complete.
"""
import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

from bpe import SPECIAL_ID, VOCAB_SIZE, BPETokenizer
from corpus_stats import WORD_RE, iter_docs
from tools.datapaths import ROOT, split_path, work_dir
from tools.machine import describe, peak_memory_mb

_TOK = None
_LAYOUT = None


def _init_worker(tokenizer_path, layout):
    global _TOK, _LAYOUT
    _TOK = BPETokenizer.load(tokenizer_path)
    _LAYOUT = layout


def encode_document(item):
    """item is (position, document). Returns the IDs for that document,
    ending with 256, and the number of words in it."""
    k, doc = item
    if _LAYOUT == "drop-both":
        text = doc
    elif _LAYOUT == "exact":
        text = ("\n" if k else "") + doc + "\n"
    else:
        text = doc + "\n"
    ids = _TOK.encode(text)
    ids.append(SPECIAL_ID)
    return ids, len(WORD_RE.findall(doc))


def encode_split(tokenizer_path, src, dst, layout="drop-after", workers=1,
                 flush_every=4_000_000):
    """Encode one split file src into dst (.bin). Returns a stats dict."""
    started = time.perf_counter()
    tmp = dst.with_name(dst.name + ".tmp")
    stats = {"split_file": str(src), "bin": str(dst), "layout": layout, "documents": 0,
             "tokens": 0, "words": 0, "text_bytes": src.stat().st_size, "max_id": 0}
    buf = []

    def flush(out):
        if not buf:
            return
        arr = np.asarray(buf, dtype=np.int64)
        top = int(arr.max())
        if top >= VOCAB_SIZE or arr.min() < 0:
            raise ValueError(f"ID {top} does not fit the 50,000 vocabulary")
        stats["max_id"] = max(stats["max_id"], top)
        out.write(arr.astype("<u2").tobytes())
        buf.clear()

    def progress():
        if stats["documents"] % 10_000 == 0:
            print(f"  {stats['documents']:,} documents, {stats['tokens']:,} tokens, "
                  f"{time.perf_counter() - started:.0f} s", flush=True)

    items = enumerate(iter_docs(src))
    with tmp.open("wb") as out:
        if workers > 1:
            ctx = mp.get_context("spawn")
            with ctx.Pool(workers, _init_worker, (str(tokenizer_path), layout)) as pool:
                results = pool.imap(encode_document, items, chunksize=32)
                for ids, words in results:
                    buf.extend(ids)
                    stats["documents"] += 1
                    stats["tokens"] += len(ids)
                    stats["words"] += words
                    if len(buf) >= flush_every:
                        flush(out)
                    progress()
        else:
            _init_worker(str(tokenizer_path), layout)
            for item in items:
                ids, words = encode_document(item)
                buf.extend(ids)
                stats["documents"] += 1
                stats["tokens"] += len(ids)
                stats["words"] += words
                if len(buf) >= flush_every:
                    flush(out)
                progress()
        if layout == "exact":
            # the file ends with a newline after the last marker
            buf.extend((_TOK or BPETokenizer.load(tokenizer_path)).encode("\n"))
        flush(out)
    tmp.replace(dst)
    seconds = time.perf_counter() - started
    stats.update({
        "seconds": round(seconds, 1),
        "bin_bytes": dst.stat().st_size,
        "bytes_per_token": round(stats["text_bytes"] / stats["tokens"], 3),
        "tokens_per_word": round((stats["tokens"] - stats["documents"]) / stats["words"], 3),
    })
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", type=Path, default=ROOT / "tokenizer" / "urdu_bpe.json")
    ap.add_argument("--splits", nargs="*", default=["train", "val"])
    ap.add_argument("--out-dir", type=Path, default=None, help="default: the work folder")
    ap.add_argument("--layout", choices=["drop-after", "drop-both", "exact"], default="drop-after")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()
    if not args.tokenizer.exists():
        sys.exit(f"{args.tokenizer} not found; run train_tokenizer.py first")
    out_dir = args.out_dir or work_dir(create=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_dir.resolve() == split_path("train").parent.resolve():
        sys.exit("refusing to write into the cleaned corpus folder")

    report = {"tokenizer": str(args.tokenizer), "machine": describe(), "splits": {}}
    for split in args.splits:
        print(f"encoding {split}", flush=True)
        stats = encode_split(args.tokenizer, split_path(split), out_dir / f"{split}.bin",
                             args.layout, args.workers)
        report["splits"][split] = stats
        print(json.dumps(stats), flush=True)
    report["peak_memory_mb_main_process"] = peak_memory_mb()
    path = out_dir / "encode_stats.json"
    path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"saved {path}; now run: python -X utf8 tools/check_bins.py --layout {args.layout}")


if __name__ == "__main__":
    main()
