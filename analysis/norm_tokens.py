"""What normalisation is worth in tokens, on the typical spelling problems.

Usage (from the repository root):
    python -X utf8 -m analysis.norm_tokens

Encodes every case of normalization_cases.py (written with the normaliser)
raw and after normalize(), with our tokenizer and with o200k_base, and keeps
the cases where normalising changes our token count. Writes
report/generated/norm_tokens.md and norm_tokens.json.
"""
from analysis.common import OURS, all_tokenizers, md_table, save
from normalization_cases import CASES
from normalize import normalize

SHOWN = 8


def main():
    toks, ours = all_tokenizers()
    if not ours:
        raise SystemExit("train the tokenizer first")
    o200k = toks[-1]
    rows, data = [], []
    for name, raw in CASES:
        norm = normalize(raw)
        r = {"case": name, "ours_raw": len(ours[0].encode(raw)), "ours_norm": len(ours[0].encode(norm)),
             "o200k_raw": len(o200k.encode(raw)), "o200k_norm": len(o200k.encode(norm))}
        data.append(r)
    changed = sorted((r for r in data if r["ours_raw"] != r["ours_norm"]),
                     key=lambda r: r["ours_norm"] / r["ours_raw"])
    for r in changed[:SHOWN]:
        rows.append([r["case"], r["ours_raw"], r["ours_norm"],
                     f"{100 * (r['ours_norm'] - r['ours_raw']) / r['ours_raw']:+.0f}%",
                     r["o200k_raw"], r["o200k_norm"]])
    raw_total = sum(r["ours_raw"] for r in changed)
    norm_total = sum(r["ours_norm"] for r in changed)
    text = md_table(["Spelling problem", "Ours raw", "Ours normalised", "Change",
                     "o200k raw", "o200k normalised"], rows,
                    ["---", "---:", "---:", "---:", "---:", "---:"])
    best = changed[0]
    text += (f"\nThe {min(SHOWN, len(changed))} largest savings are shown. "
             f"On all {len(changed)} of {len(data)} cases where it matters, normalising first "
             f"cuts our tokens from {raw_total} to {norm_total} "
             f"({100 * (norm_total - raw_total) / raw_total:+.0f}%); the largest saving is "
             f"\"{best['case']}\" ({best['ours_raw']} to {best['ours_norm']} tokens). "
             "Because train.txt was normalised, the raw forms are all but absent from it and "
             "fall back to bytes or rare pieces; this is why the next assignment calls "
             "normalize() before encode() instead of building normalisation into the lossless "
             "tokenizer.\n")
    save("norm_tokens.md", text)
    save("norm_tokens.json", {"tokenizer": OURS, "cases": data})
    print(text)


if __name__ == "__main__":
    main()
