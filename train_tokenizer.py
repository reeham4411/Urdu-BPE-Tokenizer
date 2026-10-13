"""Train the Urdu BPE tokenizer on train.txt and save it.

Usage (from the repository root):
    python -X utf8 train_tokenizer.py
    python -X utf8 train_tokenizer.py --input <clean>/train.txt --vocab-size 50000 --out tokenizer/urdu_bpe.json
    python -X utf8 train_tokenizer.py --limit-mb 5 --vocab-size 2000 --out tokenizer/trial.json   (quick trial)
    python -X utf8 train_tokenizer.py --method reference --input <work>/sample_1mb.txt --vocab-size 757

What it does:
    1. Streams train.txt one document at a time (each document is followed by
       a "<|endoftext|>" line), so the 743 MB file is never one Python string.
       The marker is only a boundary for training; documents go to the
       trainer separately, so no pair is counted across it.
    2. Calls BPETokenizer.train_fast (or train_reference) with --vocab-size.
    3. Checks the result (49,743 merges for 50,000), saves the tokenizer, and
       writes <out>.vocab.tsv, one readable line per token, for Part C.
    4. Writes the log the report needs (--log): wall-clock time, peak memory,
       sizes, and the machine.

The tokenizer itself (bpe.py) is not changed or extended here.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from bpe import FIRST_MERGE_ID, SPECIAL_ID, VOCAB_SIZE, BPETokenizer
from corpus_stats import iter_docs
from tools.datapaths import ROOT, split_path
from tools.machine import describe, peak_memory_mb


def iter_documents(path, limit_bytes=0):
    """Yield the documents of a split file, without the separator lines.
    With limit_bytes, stop after the document that passes that many bytes."""
    used = 0
    for doc in iter_docs(path):
        yield doc
        used += len(doc.encode("utf-8")) + 15
        if limit_bytes and used >= limit_bytes:
            return


def write_vocab(tok, path):
    """One line per token: id, byte length, bytes in hex, and the text (or a
    note when the bytes are not valid UTF-8 on their own)."""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("id\tbytes\thex\ttext\n")
        for i in sorted(tok.vocab):
            b = tok.vocab[i]
            try:
                text = b.decode("utf-8")
            except UnicodeDecodeError:
                text = "<partial UTF-8> " + b.decode("utf-8", "replace")
            fh.write(f"{i}\t{len(b)}\t{b.hex()}\t{text!r}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=split_path("train"))
    ap.add_argument("--vocab-size", type=int, default=VOCAB_SIZE)
    ap.add_argument("--out", type=Path, default=ROOT / "tokenizer" / "urdu_bpe.json")
    ap.add_argument("--method", choices=["fast", "reference"], default="fast")
    ap.add_argument("--limit-mb", type=float, default=0,
                    help="train on the first documents only (trial runs)")
    ap.add_argument("--log", type=Path, default=None,
                    help="default: <out without suffix>_train_log.json")
    args = ap.parse_args()
    if not args.input.exists():
        sys.exit(f"{args.input} not found; set URDU_CLEAN_DIR or pass --input")
    log_path = args.log or args.out.with_name(args.out.stem + "_train_log.json")

    tok = BPETokenizer()
    started = time.perf_counter()
    limit = int(args.limit_mb * 1e6)
    if args.method == "fast":
        tok.train_fast(iter_documents(args.input, limit), args.vocab_size, verbose=True)
    else:
        text = "<|endoftext|>".join(iter_documents(args.input, limit))
        tok.train_reference(text, args.vocab_size, verbose=True)
    seconds = time.perf_counter() - started

    wanted = args.vocab_size - FIRST_MERGE_ID
    if len(tok.merges) != wanted:
        print(f"warning: learned {len(tok.merges)} merges, asked for {wanted} "
              "(the corpus ran out of pairs?)", file=sys.stderr)
    assert tok.vocab[SPECIAL_ID] == b"<|endoftext|>"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tok.save(args.out)
    write_vocab(tok, args.out.with_suffix(".vocab.tsv"))

    log = {
        "input": str(args.input),
        "input_bytes": args.input.stat().st_size if not limit else limit,
        "method": args.method,
        "vocab_size": args.vocab_size,
        "merges": len(tok.merges),
        "seconds": round(seconds, 1),
        "hours": round(seconds / 3600, 2),
        "peak_memory_mb": peak_memory_mb(),
        "machine": describe(),
        "tokenizer_file": str(args.out),
        "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
