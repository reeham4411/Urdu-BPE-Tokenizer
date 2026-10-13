r"""Cut a reproducible 1 MB sample from train.txt for comparing the trainers.

Usage (from the repository root):
    python -X utf8 tools/make_sample.py
    python -X utf8 tools/make_sample.py --bytes 1000000 --out path/to/sample.txt

The sample is the first whole documents of train.txt, taken until it holds at
least --bytes bytes, with the "\n<|endoftext|>\n" separators kept exactly as in
the file. train.txt is already shuffled by clean_corpus.py (seed 1337), so the
first documents are a random draw that mixes the sources roughly in their
corpus proportions; the source mix is printed from doc_index.tsv.

Keeping the separators means the sample exercises the special-token path of
both trainers, not only the merge loop.

train.txt is only read. The sample and a small JSON description (size,
documents, sha256, source mix) are written to the work folder, see
tools/datapaths.py.
"""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.datapaths import END_OF_TEXT, ROOT, clean_dir, sample_path, split_path  # noqa: E402

MARKER_LINE = (END_OF_TEXT + "\n").encode("utf-8")


def first_documents(path, target):
    """Return the leading bytes of path up to the first document end at or
    after target bytes, and the number of documents they hold."""
    out = bytearray()
    docs = 0
    with path.open("rb") as fh:
        for line in fh:
            out += line
            if line == MARKER_LINE:
                docs += 1
                if len(out) >= target:
                    break
    if not out.endswith(MARKER_LINE):
        sys.exit(f"{path} ended before {target} bytes")
    return bytes(out), docs


def source_mix(docs):
    for index in (clean_dir() / "doc_index.tsv", ROOT / "data" / "doc_index.tsv"):
        if index.exists():
            mix = collections.Counter()
            with index.open(encoding="utf-8") as fh:
                next(fh)
                for line in fh:
                    split, pos, source = line.split("\t")[:3]
                    if split == "train" and int(pos) < docs:
                        mix[source] += 1
            return dict(mix)
    return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=split_path("train"))
    ap.add_argument("--bytes", type=int, default=1_000_000)
    ap.add_argument("--out", type=Path, default=sample_path())
    args = ap.parse_args()

    if args.out.resolve().parent == args.input.resolve().parent:
        sys.exit("refusing to write next to the cleaned corpus; choose another --out")
    data, docs = first_documents(args.input, args.bytes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    info = {
        "source": str(args.input),
        "bytes": len(data),
        "documents": docs,
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_mix": source_mix(docs),
    }
    args.out.with_suffix(".json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(json.dumps(info, indent=1))
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
