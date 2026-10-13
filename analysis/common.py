"""Shared code for the Part C analysis scripts.

tiktoken is used here for comparison only, as the handout allows; bpe.py
never imports it. Every script writes its tables (Markdown), plots (PNG) and
raw numbers (JSON) to report/generated/, which report/build_report.py
includes in report.pdf.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corpus_stats import WORD_RE, iter_docs  # noqa: E402,F401
from tools.datapaths import ROOT, split_path  # noqa: E402,F401

GENERATED = ROOT / "report" / "generated"
OURS_PATH = Path(os.environ.get("BPE_TOKENIZER", ROOT / "tokenizer" / "urdu_bpe.json"))
OURS = "Ours (Urdu BPE 50k)"


class Tok:
    """A common face for our tokenizer and tiktoken encodings."""

    def __init__(self, name, encode, piece_bytes, vocab_size):
        self.name = name
        self.encode = encode
        self.piece_bytes = piece_bytes
        self.vocab_size = vocab_size

    def pieces(self, text):
        """The tokens of text as readable strings; a token that is not valid
        UTF-8 on its own is shown as its hex bytes."""
        out = []
        for i in self.encode(text):
            b = self.piece_bytes(i)
            try:
                out.append(b.decode("utf-8"))
            except UnicodeDecodeError:
                out.append("<" + b.hex(" ") + ">")
        return out


def load_ours(path=OURS_PATH):
    """Our trained tokenizer, or None if it has not been trained yet."""
    if not Path(path).exists():
        return None
    from bpe import BPETokenizer
    tok = BPETokenizer.load(path)
    return Tok(OURS, tok.encode, lambda i: tok.vocab[i], len(tok.vocab)), tok


def load_tiktoken():
    import tiktoken
    out = []
    for name, label in (("gpt2", "GPT-2 (gpt2)"), ("o200k_base", "GPT-4o (o200k_base)")):
        enc = tiktoken.get_encoding(name)
        out.append(Tok(label, enc.encode_ordinary, enc.decode_single_token_bytes, enc.n_vocab))
    return out


def all_tokenizers():
    """[ours (if trained), gpt2, o200k_base]; ours is None when missing."""
    ours = load_ours()
    return ([ours[0]] if ours else []) + load_tiktoken(), ours


def count_words(text):
    """Words as in DATA_CARD.md: runs of letters, marks, digits and ZWNJ."""
    return len(WORD_RE.findall(text))


def md_table(headers, rows, align=None):
    align = align or ["---"] * len(headers)
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(align) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines) + "\n"


def md_piece(text):
    """md_code for one token, with a leading space made visible as ␣."""
    return md_code("␣" + text[1:] if text.startswith(" ") else text)


def md_code(text):
    """Inline code that survives | and backticks inside a table cell."""
    text = text.replace("|", "\\|").replace("\n", "↵")
    return "<code>" + text.replace("<", "&lt;").replace(">", "&gt;") + "</code>"


def save(name, content):
    GENERATED.mkdir(parents=True, exist_ok=True)
    path = GENERATED / name
    if isinstance(content, (dict, list)):
        path.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        path.write_text(content, encoding="utf-8")
    print("wrote", path.relative_to(ROOT))
    return path


def setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 150,
                         "font.family": ["Segoe UI", "DejaVu Sans"]})
    return plt
