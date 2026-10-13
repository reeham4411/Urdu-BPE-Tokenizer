"""Question 2: tokens per word for our tokenizer, GPT-2 and o200k_base.

Usage (from the repository root):
    python -X utf8 -m analysis.compare

Measures, for each tokenizer, on the whole of test.txt (document by document,
markers left out) and on the seven hand-picked inputs:
    tokens per word   (fertility; words as in DATA_CARD.md)
    bytes per token   (UTF-8 bytes of the text / tokens)
Writes report/generated/q2_test.md, q2_inputs.md, q2_tokens_per_word.png,
q2_splits.md (how each tokenizer cuts a few words) and q2.json.
If our tokenizer is not trained yet, only GPT-2 and o200k_base are measured.
"""
import time

from analysis.common import (OURS, all_tokenizers, count_words, iter_docs, md_piece, md_table,
                             save, setup_matplotlib, split_path)
from analysis.inputs import normalized_inputs

COLORS = {OURS: "#2a6f97", "GPT-2 (gpt2)": "#c44e52", "GPT-4o (o200k_base)": "#9a9a9a"}
SHOW_SPLITS = ["اُردُو", "پاکستان", "خواہشیں", "یوسفزئی", "1947"]


def measure(toks, texts):
    words = sum(count_words(t) for t in texts)
    nbytes = sum(len(t.encode("utf-8")) for t in texts)
    out = {"words": words, "bytes": nbytes}
    for tok in toks:
        n = sum(len(tok.encode(t)) for t in texts)
        out[tok.name] = {"tokens": n, "tokens_per_word": round(n / words, 3),
                         "bytes_per_token": round(nbytes / n, 2)}
    return out


def interpretation(test, inputs, names):
    """Two or three sentences that follow from the numbers, whatever they are."""
    gpt2, o200k = names[-2], names[-1]
    g, o = test[gpt2]["tokens_per_word"], test[o200k]["tokens_per_word"]
    if OURS not in test:
        return (f"On test.txt GPT-2 needs {g:.2f} tokens per Urdu word and o200k_base "
                f"{o:.2f}. Our tokenizer is not trained yet; rerun this script after "
                "train_tokenizer.py.\n")
    u = test[OURS]["tokens_per_word"]
    text = (f"On test.txt our tokenizer needs {u:.2f} tokens per word, against {g:.2f} for "
            f"GPT-2 ({g / u:.1f} times as many), which falls back to raw bytes for most "
            "Urdu letters. ")
    if u < o:
        text += (f"o200k_base needs {o:.2f} ({o / u:.2f} times ours): a 50k vocabulary spent "
                 "on one language beats a 200k vocabulary shared by many. ")
    else:
        text += (f"o200k_base needs {o:.2f}, fewer than ours ({u / o:.2f} times): its 200k "
                 "vocabulary is large enough to cover common Urdu words as well. ")
    worse = [k for k in inputs
             if inputs[k][OURS]["tokens_per_word"] > inputs[k][o200k]["tokens_per_word"]]
    if worse:
        def listing(items):
            items = [w if w.split()[0] in ("Urdu", "Roman", "English") else w[0].lower() + w[1:]
                     for w in items]
            return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
        digits = [w for w in worse if w.lower().startswith("numbers")]
        latin = [w for w in worse if w not in digits]
        if latin:
            text += ("Among the hand-picked inputs, o200k_base does better on " + listing(latin)
                     + ": text that our Urdu-only corpus rarely contains. ")
        if digits:
            text += ("It also does better on numbers and dates, because our pattern gives every "
                     "digit its own token (section 2).")
    else:
        text += "Ours needs the fewest tokens on every hand-picked input."
    return text + "\n"


def plot(names, test, inputs):
    plt = setup_matplotlib()
    groups = ["test.txt"] + list(inputs)
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    width = 0.8 / len(names)
    for k, n in enumerate(names):
        values = [test[n]["tokens_per_word"]] + [inputs[g][n]["tokens_per_word"] for g in inputs]
        xs = [i + (k - (len(names) - 1) / 2) * width for i in range(len(groups))]
        ax.bar(xs, values, width, label=n, color=COLORS.get(n, "#555555"))
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups, rotation=20, ha="right")
    ax.set_ylabel("tokens per word")
    ax.legend(frameon=False, ncol=len(names), loc="upper left")
    fig.tight_layout()
    fig.savefig(save("q2_tokens_per_word.png", ""), bbox_inches="tight")


def main():
    toks, _ = all_tokenizers()
    names = [t.name for t in toks]
    started = time.time()
    docs = list(iter_docs(split_path("test")))
    test = measure(toks, docs)
    test["documents"] = len(docs)
    print(f"test.txt measured in {time.time() - started:.0f} s")
    inputs = {name: measure(toks, [text]) for name, text in normalized_inputs().items()}

    save("q2_test.md", md_table(
        ["Tokenizer", "Vocabulary", "Tokens", "Tokens per word", "Bytes per token"],
        [[t.name, f"{t.vocab_size:,}", f"{test[t.name]['tokens']:,}",
          f"{test[t.name]['tokens_per_word']:.2f}", f"{test[t.name]['bytes_per_token']:.2f}"]
         for t in toks], ["---", "---:", "---:", "---:", "---:"])
        + f"\ntest.txt: {len(docs):,} documents, {test['words']:,} words, "
          f"{test['bytes'] / 1e6:.2f} MB.\n\n" + interpretation(test, inputs, names))
    rows = [[name, inputs[name]["words"]]
            + [f"{inputs[name][n]['tokens_per_word']:.2f}" for n in names] for name in inputs]
    save("q2_inputs.md", md_table(["Input", "Words"] + [f"{n}" for n in names],
                                  rows, ["---", "---:"] + ["---:"] * len(names)))
    save("q2_splits.md", md_table(
        ["Word"] + names,
        [[w] + [" ".join(md_piece(p) for p in t.pieces(w)) for t in toks] for w in SHOW_SPLITS]))
    plot(names, test, inputs)
    save("q2.json", {"test": test, "inputs": inputs})


if __name__ == "__main__":
    main()
