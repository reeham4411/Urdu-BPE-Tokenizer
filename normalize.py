"""Unicode normalisation for Urdu text.

normalize(text) is a pure function: the same input always gives the same
output, and normalize(normalize(x)) == normalize(x). It is applied to the
corpus before training and is deliberately kept outside the tokenizer, so
that decode(encode(text)) == text holds for whatever string is passed in.

Only the standard library is used. Every rule is listed in RULES together with
the characters it touches, so the cleaning script can count how often each
rule fired (see rule_counts).

The file is ASCII only. Code points are written as escapes and named in
comments.
"""
import re
import unicodedata

ZWNJ = "\u200c"
_ZWNJ_KEEP = "\ue000"  # private-use placeholder, removed from input first

# ---------------------------------------------------------------------------
# Letter variants (one-to-one maps)
# ---------------------------------------------------------------------------
LETTER_MAP = {
    "\u064a": "\u06cc",  # Arabic yeh -> Farsi (Urdu) yeh
    "\u0649": "\u06cc",  # alef maksura -> Farsi yeh
    "\u0678": "\u0626",  # high hamza yeh -> yeh with hamza above
    "\u0643": "\u06a9",  # Arabic kaf -> keheh (Urdu kaf)
    "\u06aa": "\u06a9",  # swash kaf -> keheh
    "\u0647": "\u06c1",  # Arabic heh -> heh goal
    "\u06d5": "\u06c1",  # ae (Kurdish/Uyghur heh) -> heh goal
    "\u06c0": "\u06c2",  # heh with yeh above -> heh goal with hamza above
    "\u0629": "\u06c3",  # teh marbuta -> teh marbuta goal
    "\u0671": "\u0627",  # alef wasla -> alef
}
# U+06C1 (heh goal) and U+06BE (do-chashmi heh) are different letters and are
# never merged, so there is no entry for U+06BE.

# ---------------------------------------------------------------------------
# Digits: one convention, ASCII 0-9
# ---------------------------------------------------------------------------
DIGIT_MAP = {}
for _i in range(10):
    DIGIT_MAP[chr(0x0660 + _i)] = str(_i)  # Arabic-Indic
    DIGIT_MAP[chr(0x06F0 + _i)] = str(_i)  # Extended Arabic-Indic (Urdu)
NUMBER_PUNCT_MAP = {
    "\u066a": "%",  # Arabic percent sign
    "\u066b": ".",  # Arabic decimal separator
    "\u066c": ",",  # Arabic thousands separator
}

# ---------------------------------------------------------------------------
# Punctuation that only differs in typography
# ---------------------------------------------------------------------------
PUNCT_MAP = {
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u00ab": '"', "\u00bb": '"',
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u2039": "'", "\u203a": "'",
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
    "\u2014": "-", "\u2015": "-", "\u2212": "-",
    "\u2026": "...",
}

# ---------------------------------------------------------------------------
# Characters removed outright
# ---------------------------------------------------------------------------
TATWEEL = {"\u0640"}
INVISIBLE = {
    "\u200b",  # zero width space
    "\u200d",  # zero width joiner
    "\u200e",  # left-to-right mark
    "\u200f",  # right-to-left mark
    "\u061c",  # arabic letter mark
    "\u2060",  # word joiner
    "\u00ad",  # soft hyphen
    "\ufeff",  # byte order mark / zero width no-break space
    "\u180e",  # mongolian vowel separator
    "\ufffc",  # object replacement character
    "\ufffd",  # replacement character (a decoding failure upstream)
}
INVISIBLE.update(chr(c) for c in range(0x202A, 0x202F))   # embeddings, overrides
INVISIBLE.update(chr(c) for c in range(0x2066, 0x206A))   # isolates
INVISIBLE.update(chr(c) for c in range(0xFE00, 0xFE10))   # variation selectors
# Honorific and Quranic annotation signs. They are decorative, they sit on top
# of a word and make "the same word" appear in two spellings.
ANNOTATIONS = {chr(c) for c in range(0x0610, 0x061B)}
ANNOTATIONS.update(chr(c) for c in range(0x06D6, 0x06EE))
CONTROLS = {chr(c) for c in range(0x00, 0x20)} - {"\t", "\n", "\r", "\x0b", "\x0c"}
CONTROLS.update(chr(c) for c in range(0x7F, 0xA0))
CONTROLS.discard("\x85")
PRIVATE_USE = {chr(c) for c in range(0xE000, 0xF900)}
SURROGATES = {chr(c) for c in range(0xD800, 0xE000)}

# ---------------------------------------------------------------------------
# Whitespace
# ---------------------------------------------------------------------------
SPACE_CHARS = {"\t", "\u00a0", "\u1680", "\u202f", "\u205f", "\u3000"}
SPACE_CHARS.update(chr(c) for c in range(0x2000, 0x200B))
NEWLINE_CHARS = {"\r", "\x0b", "\x0c", "\x85", "\u2028", "\u2029"}

# Which characters each rule touches. Used for statistics only.
RULES = {
    "arabic_yeh_to_urdu_yeh": {"\u064a", "\u0649", "\u0678"},
    "arabic_kaf_to_urdu_kaf": {"\u0643", "\u06aa"},
    "arabic_heh_to_heh_goal": {"\u0647", "\u06d5"},
    "heh_yeh_above_to_heh_goal_hamza": {"\u06c0"},
    "teh_marbuta_to_teh_marbuta_goal": {"\u0629"},
    "alef_wasla_to_alef": {"\u0671"},
    "tatweel_removed": TATWEEL,
    "invisible_removed": INVISIBLE,
    "annotation_signs_removed": ANNOTATIONS,
    "arabic_indic_digits_to_ascii": {c for c in DIGIT_MAP if ord(c) < 0x06F0},
    "extended_indic_digits_to_ascii": {c for c in DIGIT_MAP if ord(c) >= 0x06F0},
    "number_punctuation_to_ascii": set(NUMBER_PUNCT_MAP),
    "typographic_punctuation_to_ascii": set(PUNCT_MAP),
    "unicode_spaces_to_space": SPACE_CHARS - {"\t"},
    "tabs_to_space": {"\t"},
    "line_separators_to_newline": NEWLINE_CHARS,
    "zwnj_seen": {ZWNJ},
    "control_chars_removed": CONTROLS,
}


def _build_table():
    table = {}
    table.update(LETTER_MAP)
    table.update(DIGIT_MAP)
    table.update(NUMBER_PUNCT_MAP)
    table.update(PUNCT_MAP)
    for ch in SPACE_CHARS:
        table[ch] = " "
    for ch in NEWLINE_CHARS:
        table[ch] = "\n"
    for group in (TATWEEL, INVISIBLE, ANNOTATIONS, CONTROLS, PRIVATE_USE, SURROGATES):
        for ch in group:
            table[ch] = None
    return {ord(k): v for k, v in table.items()}


_TABLE = _build_table()

# Presentation forms and full-width forms are folded with NFKC, one character
# at a time. Whole-string NFKC would also rewrite ligatures and superscripts in
# the English parts of a document, which is not wanted.
_FOLD_RE = re.compile("[\ufb50-\ufdff\ufe70-\ufefc\uff01-\uff5e]")

# ZWNJ is used on purpose in Urdu compounds (for example the word for
# "international"). It only changes rendering when the letter before it would
# join to the letter after it, so it is kept in that position and dropped
# everywhere else (word edges, repeated, after a non-joining letter).
_DUAL_JOINING = "".join(chr(c) for c in (
    0x0628, 0x067e, 0x062a, 0x0679, 0x062b, 0x062c, 0x0686, 0x062d, 0x062e,
    0x0633, 0x0634, 0x0635, 0x0636, 0x0637, 0x0638, 0x0639, 0x063a, 0x0641,
    0x0642, 0x06a9, 0x06af, 0x0644, 0x0645, 0x0646, 0x06c1, 0x06be, 0x06cc,
    0x0626,
))
_JOINABLE_NEXT = "\u0622-\u063f\u0641-\u064a\u066e-\u06d3\u06d5"
_ZWNJ_KEEP_RE = re.compile(
    "(?<=[%s])%s+(?=[%s])" % (_DUAL_JOINING, ZWNJ, _JOINABLE_NEXT)
)

_MARKS = "\u064b-\u065f\u0670"
_REPEATED_MARK_RE = re.compile("([%s])\\1+" % _MARKS)
_ORPHAN_MARK_RE = re.compile("(?<![^\\s])[%s]+" % _MARKS)
_YEH_HAMZA_RE = re.compile("\u06cc\u0654")  # yeh + combining hamza -> U+0626

# Some corpora (UFAL) are word-tokenised and put a space before every full stop
# and comma, and inside brackets: "x \u06d4", "( 1 )". Written Urdu does not do
# this, and the other sources do not, so the spaces are closed.
_SPACE_BEFORE_URDU_PUNCT_RE = re.compile(" +(?=[\u06d4\u060c\u061f\u061b])")
_SPACE_BEFORE_ASCII_PUNCT_RE = re.compile(" +(?=[,.!?:;](?:[ \n)\]}]|$))")
_SPACE_AFTER_OPEN_RE = re.compile("(?<=[(\\[{]) +")
_SPACE_BEFORE_CLOSE_RE = re.compile(" +(?=[)\\]}])")
_SPACES_RE = re.compile(" {2,}")
_LINE_EDGE_RE = re.compile(" *\n *")
_NEWLINES_RE = re.compile("\n{2,}")


def normalize(text):
    """Return the normalised form of text (see the module docstring)."""
    if not text:
        return ""
    if not text.isascii():
        # "alef + ligature Allah" is how most Urdu text spells the word; the
        # ligature already contains the alef, so folding would double it.
        if "\ufdf2" in text:
            text = text.replace("\u0627\ufdf2", "\ufdf2")
        text = _FOLD_RE.sub(_fold_char, text)
        # NFC first: it joins yeh + hamza, alef + madda and so on, before the
        # letter maps below would stop the sequences from composing.
        if not unicodedata.is_normalized("NFC", text):
            text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").translate(_TABLE)
    if not text.isascii():
        # Order matters here. Dropping a ZWNJ (or any character deleted by the
        # table) can make two marks adjacent, or put a mark next to a space.
        # So ZWNJ goes first, then the text is recomposed, and only then are
        # marks collapsed. This keeps normalize idempotent.
        if ZWNJ in text:
            text = _ZWNJ_KEEP_RE.sub(_ZWNJ_KEEP, text)
            text = text.replace(ZWNJ, "").replace(_ZWNJ_KEEP, ZWNJ)
        text = _YEH_HAMZA_RE.sub("\u0626", text)
        if not unicodedata.is_normalized("NFC", text):
            text = unicodedata.normalize("NFC", text)
        text = _REPEATED_MARK_RE.sub("\\1", text)
        text = _ORPHAN_MARK_RE.sub("", text)
        text = _SPACE_BEFORE_URDU_PUNCT_RE.sub("", text)
    text = _tighten(text)
    text = _SPACES_RE.sub(" ", text)
    text = _LINE_EDGE_RE.sub("\n", text)
    text = _NEWLINES_RE.sub("\n", text)
    return text.strip()


def _tighten(text):
    """Close spaces before , . ! ? : ; and inside brackets. The rules can
    expose each other ("( , )"), so they repeat until nothing changes."""
    for _ in range(4):
        before = text
        text = _SPACE_BEFORE_ASCII_PUNCT_RE.sub("", text)
        text = _SPACE_AFTER_OPEN_RE.sub("", text)
        text = _SPACE_BEFORE_CLOSE_RE.sub("", text)
        if text == before:
            break
    return text


def _fold_char(match):
    folded = unicodedata.normalize("NFKC", match.group())
    # A few ligatures stand for whole phrases (U+FDFA is four words). They must
    # not be glued to the word in front of them.
    return " %s " % folded if " " in folded else folded


def rule_counts(char_counter):
    """Map rule name -> number of characters in char_counter that the rule
    touches. char_counter is a collections.Counter over raw characters."""
    return {name: sum(char_counter.get(ch, 0) for ch in chars)
            for name, chars in RULES.items()}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(normalize(sys.stdin.buffer.read().decode("utf-8")) + "\n")
