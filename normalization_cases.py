"""Show what normalize() does to typical Urdu spelling problems.

Usage (from the repository root):
    python normalization_cases.py
    python normalization_cases.py --tokenizer path/to/tokenizer.json   # after Part B
    python normalization_cases.py --markdown reports/normalization_cases.md

For each case it prints the raw and normalised text, their sizes in UTF-8 bytes
and, when a tokenizer is available, the number of tokens before and after. A
case where raw text costs more tokens than normalised text is a place where
skipping normalisation would hurt the vocabulary. A case where the tokenizer
still needs many tokens after normalisation is a candidate for Part C,
question 3.

Tokenizer sources, tried in order: the file given with --tokenizer (loaded with
BPETokenizer from bpe.py), then tiktoken's o200k_base if it is installed.
"""
import argparse
import sys
from pathlib import Path

from normalize import normalize

ROOT = Path(__file__).resolve().parent

YEH_ARABIC = chr(0x064A)
ALEF_MAKSURA = chr(0x0649)
KAF_ARABIC = chr(0x0643)
HEH_ARABIC = chr(0x0647)
TATWEEL = chr(0x0640)
ZWNJ = chr(0x200C)
ZWJ = chr(0x200D)
RLM = chr(0x200F)
NBSP = chr(0x00A0)
HONORIFIC = chr(0x0611)

CASES = [
    ("Arabic yeh in place of Urdu yeh", "پاکستان %sی تار%sخ" % (YEH_ARABIC, YEH_ARABIC)),
    ("Alef maksura at the end of a word", "موس%s اور عیس%s" % (ALEF_MAKSURA, ALEF_MAKSURA)),
    ("Arabic kaf in place of Urdu kaf", "%sتاب اور %sرسی" % (KAF_ARABIC, KAF_ARABIC)),
    ("Arabic heh in place of heh goal", "ب%sت اچھا ہ%s" % (HEH_ARABIC, HEH_ARABIC)),
    ("Do-chashmi heh is a different letter", "کھانا کہانی بھائی بہت"),
    ("Tatweel stretching", "ارد%s%sو زبان" % (TATWEEL, TATWEEL)),
    ("ZWNJ inside a compound is kept", "بین%sالاقوامی تعلقات" % ZWNJ),
    ("Stray ZWNJ at word edges is dropped", "%sکتاب%s اچھی" % (ZWNJ, ZWNJ)),
    ("ZWJ and direction marks", "اردو%s زبان%s%s" % (ZWJ, RLM, ZWJ)),
    ("Urdu digits", "سال ۱۹۴۷ میں ۱۴ اگست"),
    ("Arabic-Indic digits and decimal mark", "قیمت ١٢٣٫٥٠ روپے"),
    ("Non-breaking spaces and runs of spaces", "یہ%sایک   جملہ%s%sہے" % (NBSP, NBSP, NBSP)),
    ("Blank lines and stray line breaks", "پہلی سطر\r\n\r\n\r\nدوسری سطر\r"),
    ("Space before the Urdu full stop", "یہ ایک جملہ ہے ۔ کیا یہ درست ہے ؟"),
    ("Diacritics are kept", "اُردُو زَبان"),
    ("Repeated diacritic", "زَبَََان"),
    ("Honorific sign above a name", "حضرت محمد%s" % HONORIFIC),
    ("Arabic presentation forms", "ﷲ اور ﻟﺤﻤﺪ"),
    ("Curly quotes and dashes", "اس نے کہا \u201cٹھیک ہے\u201d \u2014 اور چلا گیا"),
    ("Code-mixed text is untouched", "میرا laptop خراب ہے اور WiFi نہیں چل رہا"),
    ("Roman Urdu is untouched", "mujhe yeh kitab pasand hai"),
]


def load_tokenizer(path):
    """Return a function str -> list of ids, and a label, or (None, None)."""
    if path:
        sys.path.insert(0, str(ROOT))
        from bpe import BPETokenizer  # written in Part B
        tok = BPETokenizer.load(path) if hasattr(BPETokenizer, "load") else BPETokenizer(path)
        return tok.encode, "our BPE"
    try:
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
        return enc.encode, "o200k_base"
    except Exception:
        return None, None


def show(text):
    return text.replace("\n", "\\n").replace("\r", "\\r")


def codepoints(text, limit=14):
    points = " ".join("%04X" % ord(c) for c in text[:limit])
    return points + (" ..." if len(text) > limit else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokenizer", help="saved tokenizer file from Part B")
    ap.add_argument("--markdown", type=Path, help="also write the table to this file")
    args = ap.parse_args()

    encode, label = load_tokenizer(args.tokenizer)
    header = ["Case", "Raw bytes", "Normalised bytes"]
    if encode:
        header += ["Tokens raw (%s)" % label, "Tokens normalised"]
    rows = []
    for name, raw in CASES:
        norm = normalize(raw)
        row = [name, str(len(raw.encode("utf-8"))), str(len(norm.encode("utf-8")))]
        if encode:
            row += [str(len(encode(raw))), str(len(encode(norm)))]
        rows.append(row)
        print("%s\n  raw        %s\n  normalised %s" % (name, show(raw), show(norm)))
        print("  code points raw %s | normalised %s" % (codepoints(raw), codepoints(norm)))
        assert normalize(norm) == norm, "normalize is not idempotent on: " + name

    table = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    table += ["| " + " | ".join(r) + " |" for r in rows]
    print()
    print("\n".join(table))
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text("\n".join(table) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
