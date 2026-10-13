r"""Check train.bin and val.bin against the text they were encoded from.

Usage (from the repository root):
    python -X utf8 tools/check_bins.py
    python -X utf8 tools/check_bins.py --splits val --full
    python -X utf8 tools/check_bins.py --layout drop-both --sample 500

Checks, per split (exit code 1 if any fails):
  1. the file is a whole number of uint16 values and not empty;
  2. every ID is below 50,000 and below the tokenizer's vocabulary size;
  3. ID 256 occurs exactly once per document of the .txt file;
  4. round trip: the IDs between two 256s decode to the document they came
     from, for the first, the last and --sample random documents (all of
     them with --full; val is always checked in full);
  5. statistics: tokens, bytes per token, tokens per document.

--layout says how encode_corpus.py treated the newlines around the marker
(the file is  doc \n <|endoftext|> \n doc \n <|endoftext|> \n ...):
  drop-after  (default) each document gives encode(doc + "\n"), then 256
  drop-both   each document gives encode(doc), then 256
  exact       the IDs decode to the file byte for byte
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bpe import SPECIAL_ID, VOCAB_SIZE, BPETokenizer  # noqa: E402
from corpus_stats import iter_docs  # noqa: E402
from tools.datapaths import ROOT, split_path, work_dir  # noqa: E402


def expected_piece(doc, k, layout):
    """Text that the IDs before the (k+1)-th 256 must decode to."""
    if layout == "drop-after":
        return doc + "\n"
    if layout == "drop-both":
        return doc
    return ("\n" if k else "") + doc + "\n"  # exact


def check_split(tok, split, bin_path, layout, n_sample, full, seed):
    problems = []
    report = {"split": split, "bin": str(bin_path)}
    size = bin_path.stat().st_size
    if size == 0 or size % 2:
        return report, [f"{bin_path}: {size} bytes is not a non-empty uint16 array"]
    ids = np.memmap(bin_path, dtype=np.uint16, mode="r")
    report["tokens"] = int(ids.size)
    top = int(ids.max())
    report["max_id"] = top
    if top >= VOCAB_SIZE or top >= len(tok.vocab):
        problems.append(f"{split}: max ID {top} is outside the vocabulary")

    ends = np.flatnonzero(ids == SPECIAL_ID)
    docs = sum(1 for _ in iter_docs(split_path(split)))
    report["documents"] = docs
    report["special_ids"] = int(ends.size)
    if ends.size != docs:
        problems.append(f"{split}: {ends.size} IDs 256 for {docs} documents")
        return report, problems
    tail = ids[ends[-1] + 1:]
    want_tail = "\n" if layout == "exact" else ""
    if tok.decode(tail.tolist()) != want_tail:
        problems.append(f"{split}: unexpected IDs after the last 256 for layout {layout}")

    rng = random.Random(seed)
    chosen = set(range(docs)) if full else {0, docs - 1} | set(
        rng.sample(range(docs), min(n_sample, docs)))
    starts = np.concatenate(([0], ends[:-1] + 1))
    text_bytes = checked = 0
    for k, doc in enumerate(iter_docs(split_path(split))):
        text_bytes += len(doc.encode("utf-8")) + len("\n<|endoftext|>\n")
        if k not in chosen:
            continue
        got = tok.decode(ids[starts[k]:ends[k]].tolist())
        want = expected_piece(doc, k, layout)
        checked += 1
        if got != want:
            i = next((j for j, (a, b) in enumerate(zip(got, want)) if a != b),
                     min(len(got), len(want)))
            problems.append(f"{split}: document {k} differs at character {i}: "
                            f"decoded {got[max(0, i - 15):i + 15]!r}, "
                            f"expected {want[max(0, i - 15):i + 15]!r}")
            if len(problems) > 10:
                break
    report["documents_round_tripped"] = checked
    report["bytes_per_token"] = round(text_bytes / ids.size, 3)
    report["tokens_per_document"] = round(ids.size / docs, 1)
    return report, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", type=Path, default=ROOT / "tokenizer" / "urdu_bpe.json")
    ap.add_argument("--bin-dir", type=Path, default=work_dir())
    ap.add_argument("--splits", nargs="*", default=["train", "val"])
    ap.add_argument("--layout", choices=["drop-after", "drop-both", "exact"],
                    default="drop-after")
    ap.add_argument("--sample", type=int, default=200,
                    help="random documents to round-trip per split")
    ap.add_argument("--full", action="store_true", help="round-trip every document")
    ap.add_argument("--seed", type=int, default=417)
    args = ap.parse_args()

    tok = BPETokenizer.load(args.tokenizer)
    started = time.time()
    reports, problems = [], []
    for split in args.splits:
        bin_path = args.bin_dir / f"{split}.bin"
        if not bin_path.exists():
            problems.append(f"{bin_path} not found")
            continue
        full = args.full or split == "val"
        report, found = check_split(tok, split, bin_path, args.layout, args.sample, full, args.seed)
        reports.append(report)
        problems += found
        print(json.dumps(report, ensure_ascii=False), flush=True)
    summary = {"layout": args.layout, "seconds": round(time.time() - started, 1),
               "splits": reports, "problems": problems}
    out = work_dir(create=True) / "check_bins.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    for p in problems:
        print("PROBLEM:", p)
    print("OK" if not problems else f"{len(problems)} problem(s)", f"(saved {out})")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
