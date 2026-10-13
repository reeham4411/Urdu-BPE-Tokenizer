"""Question 3: inputs our tokenizer handles badly.

Usage (from the repository root):
    python -X utf8 -m analysis.bad_inputs

Encodes every candidate in analysis/inputs.py BAD_CANDIDATES (not
normalised, as a user would type them) with all three tokenizers, ranks them
by our bytes per token (fewer bytes per token = worse compression), and
writes the three worst, with how our tokenizer cuts them and why, to
report/generated/q3.md; all candidates go to q3_all.md and q3.json.
For comparison, test.txt averages the bytes per token in q2.json.
"""
import json

from analysis.common import GENERATED, OURS, all_tokenizers, md_code, md_piece, md_table, save
from analysis.inputs import BAD_CANDIDATES

SHOW = 14


def main():
    toks, ours = all_tokenizers()
    names = [t.name for t in toks]
    results = {}
    for name, (text, why) in BAD_CANDIDATES.items():
        nbytes = len(text.encode("utf-8"))
        r = {"text": text, "why": why, "bytes": nbytes, "chars": len(text)}
        for t in toks:
            ids = t.encode(text)
            r[t.name] = {"tokens": len(ids), "bytes_per_token": round(nbytes / len(ids), 2),
                         "pieces": t.pieces(text)[:SHOW]}
        results[name] = r
    key = OURS if ours else names[0]
    ranked = sorted(results, key=lambda k: results[k][key]["bytes_per_token"])

    save("q3_all.md", md_table(
        ["Input", "Characters"] + [f"{n} tokens" for n in names],
        [[k, results[k]["chars"]] + [results[k][n]["tokens"] for n in names] for k in ranked],
        ["---", "---:"] + ["---:"] * len(names)))

    test_bpt = None
    q2 = GENERATED / "q2.json"
    if q2.exists() and ours:
        test_bpt = json.loads(q2.read_text(encoding="utf-8"))["test"].get(OURS, {}).get(
            "bytes_per_token")
    lines = []
    if not ours:
        lines.append("Our tokenizer is not trained yet; the ranking below uses GPT-2 and is "
                     "replaced when this script is rerun after training.\n")
    for i, k in enumerate(ranked[:3], 1):
        r = results[k]
        lines.append(f"**{i}. {k}.** {md_code(r['text'][:80])}\n")
        lines.append(md_table(["Tokenizer", "Tokens", "Bytes per token"],
                              [[n, r[n]["tokens"], r[n]["bytes_per_token"]] for n in names],
                              ["---", "---:", "---:"]))
        pieces = " ".join(md_piece(p) for p in r[key]["pieces"])
        lines.append(f"\nFirst tokens of ours, in order (␣ is a space): {pieces}\n")
        compare = (f" (test.txt averages {test_bpt:.2f})" if test_bpt else "")
        lines.append(f"\n{r['why']} Our tokenizer gets {r[key]['bytes_per_token']:.2f} "
                     f"bytes per token here{compare}.\n")
    save("q3.md", "\n".join(lines))
    save("q3.json", {"ranking_by": key, "ranked": ranked, "results": results})


if __name__ == "__main__":
    main()
