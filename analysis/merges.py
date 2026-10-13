"""Question 1: what did the merges learn?

Usage (from the repository root):
    python -X utf8 -m analysis.merges

Writes report/generated/q1_first50.md (merges 1 to 50), q1_every5000.md,
q1_longest.md (20 longest tokens), q1_length.png (token length by merge
number), q1_summary.md (the interpretation) and q1.json.

Definitions used in the tables:
    letter   the merge joins two raw bytes into one two-byte character, i.e.
             it rebuilds an Urdu (or other) letter, possibly after a space;
    space + letter  a leading space attached to an already rebuilt letter;
    N letters  a valid piece of N characters that is not a whole word;
    partial  the token is not valid UTF-8 on its own (it holds part of a
             character, such as a space plus the first byte of a letter);
    A leading space is shown as ␣.
    word     the token is a space followed by a whole word: a run of letters,
             marks and ZWNJ of at least two characters that occurs at least 50
             times as a word in val.txt and test.txt. The leading space is
             required, because a token like "یں" matches a word but is learned
             as the plural suffix inside longer words.
"""
import collections
import sys

from analysis.common import (WORD_RE, iter_docs, load_ours, md_code, md_table, save,
                             setup_matplotlib, split_path)

FIRST = 257


def show(text):
    """A token for a table cell, with a leading space made visible as ␣."""
    return md_code("␣" + text[1:] if text.startswith(" ") else text)


def text_of(b):
    try:
        return b.decode("utf-8"), True
    except UnicodeDecodeError:
        return "<" + b.hex(" ") + ">", False


def word_set():
    counts = collections.Counter()
    for split in ("val", "test"):
        for doc in iter_docs(split_path(split)):
            counts.update(WORD_RE.findall(doc))
    return {w for w, n in counts.items() if n >= 50 and len(w) >= 2 and not w.isdigit()}


def classify(tok, k, words):
    a, b = tok.merges[k]
    raw = tok.vocab[FIRST + k]
    text, valid = text_of(raw)
    notes = []
    if not valid:
        notes.append("partial")
    core = text[1:] if valid and text.startswith(" ") else text
    if valid and b < 256 and len(core) == 1 and len(core.encode("utf-8")) == 2:
        notes.append("letter")
    elif valid and text.startswith(" ") and len(core) == 1:
        notes.append("space + letter")
    if valid and text.startswith(" ") and core in words:
        notes.append("word")
    elif valid and len(core) > 1 and not notes:
        notes.append(f"{len(core)} letters")
    return text, valid, core, notes


def main():
    loaded = load_ours()
    if not loaded:
        sys.exit("tokenizer/urdu_bpe.json not found: train the tokenizer first")
    _, tok = loaded
    n = len(tok.merges)
    words = word_set()
    info = [classify(tok, k, words) for k in range(n)]

    def row(k):
        text, _, _, notes = info[k]
        return [k + 1, FIRST + k, show(text), len(tok.vocab[FIRST + k]), ", ".join(notes)]

    headers = ["Merge", "ID", "Token", "Bytes", "Note"]
    align = ["---:", "---:", "---", "---:", "---"]
    # merges 1 to 50 as a compact grid: three side-by-side groups of rows
    first = min(50, n)
    per = -(-first // 3)
    grid = []
    for r in range(per):
        cells = []
        for g in range(3):
            k = g * per + r
            if k < first:
                text, _, _, notes = info[k]
                cells += [k + 1, show(text), len(tok.vocab[FIRST + k]), ", ".join(notes)]
            else:
                cells += ["", "", "", ""]
        grid.append(cells)
    save("q1_first50.md", md_table(["Merge", "Token", "Bytes", "Note"] * 3, grid,
                                   ["---:", "---", "---:", "---"] * 3))
    picks = list(range(4999, n, 5000)) + ([n - 1] if (n - 1) % 5000 != 4999 else [])
    save("q1_every5000.md", md_table(headers, [row(k) for k in picks], align))

    longest = sorted(range(n), key=lambda k: (-len(tok.vocab[FIRST + k]), k))[:20]
    save("q1_longest.md", md_table(
        ["Merge", "Token", "Bytes", "Characters"],
        [[k + 1, show(info[k][0]), len(tok.vocab[FIRST + k]),
          len(info[k][0]) if info[k][1] else "partial"] for k in longest],
        ["---:", "---", "---:", "---:"]))

    first50 = info[:50]
    letters = [k + 1 for k, x in enumerate(first50) if "letter" in x[3]]
    spaced = [k + 1 for k, x in enumerate(first50) if "space + letter" in x[3]]
    partial = [k + 1 for k, x in enumerate(first50) if "partial" in x[3]]
    first_word = next((k for k, x in enumerate(info) if "word" in x[3]), None)
    partial_all = sum(1 for x in info if not x[1])
    summary = (
        f"Of the first 50 merges, {len(letters)} rebuild a two-byte letter (merges "
        f"{', '.join(map(str, letters[:12]))}{'...' if len(letters) > 12 else ''}) and "
        f"{len(partial)} produce a token that is not valid UTF-8 on its own (merges "
        f"{', '.join(map(str, partial[:12]))}{'...' if len(partial) > 12 else ''}), "
        "typically a space joined to the first byte of a letter"
        + (f"; {len(spaced)} attach a leading space to a letter" if spaced else "") + ". ")
    if first_word is not None:
        summary += (f"The first whole word is merge {first_word + 1}, "
                    f"{show(info[first_word][0])}. ")
    summary += (f"Over all {n:,} merges, {partial_all:,} tokens "
                f"({100 * partial_all / n:.2f}%) are not valid UTF-8 alone. The longest "
                f"token has {len(tok.vocab[FIRST + longest[0]])} bytes.\n")
    save("q1_summary.md", summary)

    plt = setup_matplotlib()
    bucket = 1000
    xs, ys = [], []
    for start in range(0, n, bucket):
        lens = [len(tok.vocab[FIRST + k]) for k in range(start, min(n, start + bucket))]
        xs.append(start + len(lens) / 2)
        ys.append(sum(lens) / len(lens))
    fig, ax = plt.subplots(figsize=(3.6, 1.7))
    ax.plot(xs, ys, color="#2a6f97")
    ax.set_xlabel("merge number")
    ax.set_ylabel("mean token bytes")
    fig.tight_layout()
    fig.savefig(save("q1_length.png", ""), bbox_inches="tight")
    save("q1.json", {"merges": n, "letters_in_first_50": letters,
                     "space_letter_in_first_50": spaced,
                     "partial_in_first_50": partial,
                     "first_whole_word": None if first_word is None else
                     {"merge": first_word + 1, "token": info[first_word][0]},
                     "partial_overall": partial_all,
                     "longest": [{"merge": k + 1, "token": info[k][0],
                                  "bytes": len(tok.vocab[FIRST + k])} for k in longest]})


if __name__ == "__main__":
    main()
