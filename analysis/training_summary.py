"""Part B evidence for the report: training time and machine, fast versus
reference, the encoded corpus, and the pre-tokenisation pattern.

Usage (from the repository root):
    python -X utf8 -m analysis.training_summary

Reads, when they exist:
    tokenizer/urdu_bpe_train_log.json      (train_tokenizer.py)
    <work>/fast_vs_reference.json          (tests/test_fast_matches_reference.py)
    <work>/encode_stats.json               (encode_corpus.py)
    <work>/check_bins.json                 (tools/check_bins.py)
and writes report/generated/b_training.md and b_pattern.md. Anything not yet
produced is listed as pending, so the report shows what is missing.
"""
import json

import bpe
from analysis.common import ROOT, md_code, md_table, save
from tools.datapaths import work_dir


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main():
    train = load(ROOT / "tokenizer" / "urdu_bpe_train_log.json")
    fvr = load(work_dir() / "fast_vs_reference.json")
    enc = load(work_dir() / "encode_stats.json")
    bins = load(work_dir() / "check_bins.json")
    rows, pending = [], []

    if train:
        m = train["machine"]
        rows += [
            [f"Training time ({train['method']}, {train['input_bytes'] / 1e6:,.0f} MB of train.txt)",
             f"{train['seconds'] / 3600:.2f} h ({train['seconds']:,.0f} s)"],
            ["Merges learned", f"{train['merges']:,}"],
            ["Peak memory", f"{train['peak_memory_mb']:,.0f} MB" if train["peak_memory_mb"] else "n/a"],
            ["Machine", f"{m['cpu']}, {m['logical_cpus']} logical CPUs, {m['ram_gb']} GB RAM, "
                        f"{m['os']}, Python {m['python']}"],
        ]
    else:
        pending.append("python -X utf8 train_tokenizer.py")
    if fvr:
        rows += [["Fast vs reference, 1 MB sample",
                  f"{fvr['merges_fast']} merges, identical: {'yes' if fvr['identical'] else 'NO'}; "
                  f"reference {fvr['seconds_reference']:.1f} s, fast {fvr['seconds_fast']:.1f} s "
                  f"({fvr['seconds_reference'] / max(fvr['seconds_fast'], 0.01):.0f}x)"]]
    else:
        pending.append("python -X utf8 -m unittest tests.test_fast_matches_reference")
    if enc:
        for split, s in enc["splits"].items():
            rows.append([f"{split}.bin", f"{s['tokens']:,} tokens ({s['bin_bytes'] / 1e6:.0f} MB), "
                         f"{s['tokens_per_word']:.2f} tokens/word, {s['bytes_per_token']:.2f} "
                         f"bytes/token, encoded in {s['seconds']:,.0f} s"])
    else:
        pending.append("python -X utf8 encode_corpus.py")
    if bins:
        ok = not bins["problems"]
        detail = "; ".join(f"{s['split']}: max ID {s['max_id']}, "
                           f"{s['documents_round_tripped']:,} documents round-tripped"
                           for s in bins["splits"])
        rows.append(["check_bins.py", ("passed. " if ok else "FAILED. ") + detail])
    else:
        pending.append("python -X utf8 tools/check_bins.py")

    text = md_table(["Measure", "Value"], rows) if rows else ""
    if pending:
        text += "\n*Pending: " + "; ".join(f"`{p}`" for p in pending) + ".*\n"
    save("b_training.md", text)
    pattern = bpe.PATTERN
    save("b_pattern.md", md_code(pattern) + "\n" if pattern else
         "*Pending: set PATTERN in bpe.py.*\n")


if __name__ == "__main__":
    main()
