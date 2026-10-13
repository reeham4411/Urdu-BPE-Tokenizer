"""Text-level cleaning rules used by clean_corpus.py.

Each function works on one document (a str) and has no side effects, so the
rules can be tested on their own (tests/test_textclean.py).

Order used by the pipeline:
    strip_markup -> normalize.normalize -> cut_tail_sections -> scrub_personal
    -> filter_lines -> is_urdu_document
"""
import html
import re

from normalize import normalize

END_OF_TEXT = "<|endoftext|>"

# ---------------------------------------------------------------------------
# 1. Markup extraction
# ---------------------------------------------------------------------------
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_SCRIPT_RE = re.compile(r"<(script|style)\b.*?</\1\s*>", re.S | re.I)
_REF_RE = re.compile(r"<ref\b[^>]*?/>|<ref\b[^>]*>.*?</ref\s*>", re.S | re.I)
_BLOCK_TAG_RE = re.compile(
    r"</?(?:br|p|div|li|ul|ol|tr|td|th|table|tbody|thead|h[1-6]|hr|blockquote"
    r"|section|article|center|dd|dt|dl)\b[^>]{0,300}>",
    re.I,
)
_TAG_RE = re.compile(r"</?[A-Za-z][^>]{0,300}>|<>")
_ENTITY_RE = re.compile(r"&(?:#\d{1,7}|#x[0-9a-fA-F]{1,6}|[A-Za-z]{2,10});")

_TEMPLATE_RE = re.compile(r"\{\{[^{}]*\}\}")
_TABLE_RE = re.compile(r"\{\|.*?\|\}", re.S)
_FILE_LINK_RE = re.compile(
    r"\[\[\s*(?:File|Image|Category|\u062a\u0635\u0648\u06cc\u0631|\u0641\u0627\u0626\u0644"
    r"|\u0632\u0645\u0631\u06c1)\s*:[^\[\]]*(?:\[\[[^\]]*\]\][^\[\]]*)*\]\]",
    re.I,
)
_WIKILINK_RE = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]")
_EXTLINK_RE = re.compile(r"\[(?:https?:)?//\S+\s*([^\]]*)\]")
_QUOTES_RE = re.compile(r"'{2,5}")
_HEADING_RE = re.compile(r"^=+[ \t]*(.*?)[ \t]*=+[ \t]*$", re.M)
_MAGIC_WORD_RE = re.compile(r"__[A-Z_]+__")
_LIST_MARKER_RE = re.compile(r"^[*#:;]+[ \t]*", re.M)
_EDIT_LINK_RE = re.compile(
    r"\[(?:\u062a\u0631\u0645\u06cc\u0645|edit|\d{1,3}|\u062d\u0648\u0627\u0644\u06c1 \u062f\u0631\u06a9\u0627\u0631)\]"
)
# A line that starts like one of these is wiki structure, not prose.
_STRUCTURE_LINE_RE = re.compile(
    r"^(?:[|!]|\{\||\|\}|\|-"
    r"|(?:\u0632\u0645\u0631\u06c1|Category|\u062a\u0635\u0648\u06cc\u0631|\u0641\u0627\u0626\u0644|File|Image"
    r"|\u0633\u0627\u0646\u0686\u06c1|Template|\u062e\u0627\u0635|Special)[ \t]*:)",
    re.I | re.M,
)
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def strip_markup(text, wiki=False):
    """Remove HTML, and for wiki sources the wiki markup that is left over.

    The text is plain on return except for line structure. Literal
    <|endoftext|> strings are removed so they cannot be mistaken for the
    document separator later.
    """
    if END_OF_TEXT in text:
        text = text.replace(END_OF_TEXT, " ")
    if "&" in text and _ENTITY_RE.search(text):
        text = html.unescape(text)
    if "<" in text:
        text = _COMMENT_RE.sub(" ", text)
        text = _SCRIPT_RE.sub(" ", text)
        text = _REF_RE.sub(" ", text)
        text = _BLOCK_TAG_RE.sub("\n", text)
        text = _TAG_RE.sub("", text)
    if wiki:
        text = _strip_wiki(text)
    if "[" in text:
        text = _EDIT_LINK_RE.sub("", text)
    return text


def _strip_wiki(text):
    if "{|" in text:
        text = _TABLE_RE.sub("\n", text)
    if "{{" in text:
        for _ in range(4):  # nested templates
            text, n = _TEMPLATE_RE.subn(" ", text)
            if not n:
                break
    if "[[" in text:
        text = _FILE_LINK_RE.sub("\n", text)
        text = _WIKILINK_RE.sub(r"\1", text)
    if "[" in text:
        text = _EXTLINK_RE.sub(r"\1", text)
    if "'''" in text or "''" in text:
        text = _QUOTES_RE.sub("", text)
    if "=" in text:
        text = _HEADING_RE.sub(r"\1", text)
    if "__" in text:
        text = _MAGIC_WORD_RE.sub("", text)
    text = _LIST_MARKER_RE.sub("", text)
    text = _STRUCTURE_LINE_RE.sub("\x00", text)
    # Lines marked above are removed whole.
    if "\x00" in text:
        text = "\n".join(l for l in text.split("\n") if not l.startswith("\x00"))
    return _BLANK_LINES_RE.sub("\n\n", text)


# ---------------------------------------------------------------------------
# 3. Trailing sections of encyclopedia articles
# ---------------------------------------------------------------------------
# These headings introduce references, link lists and navigation, which are not
# running Urdu prose. Everything from the first such heading onwards is cut.
_TAIL_HEADINGS = {
    normalize(h) for h in (
        "\u062d\u0648\u0627\u0644\u06c1 \u062c\u0627\u062a",
        "\u0628\u06cc\u0631\u0648\u0646\u06cc \u0631\u0648\u0627\u0628\u0637",
        "\u0628\u06cc\u0631\u0648\u0646\u06cc \u0631\u0628\u0637",
        "\u0628\u06cc\u0631\u0648\u0646\u06cc \u06a9\u0691\u06cc\u0627\u06ba",
        "\u0645\u0632\u06cc\u062f \u062f\u06cc\u06a9\u06be\u06cc\u06d2",
        "\u0645\u0632\u06cc\u062f \u062f\u06cc\u06a9\u06be\u06cc\u06ba",
        "\u0645\u0632\u06cc\u062f \u067e\u0691\u06be\u06cc\u06d2",
        "\u0645\u0632\u06cc\u062f \u0645\u0637\u0627\u0644\u0639\u06c1",
        "\u06c1\u0627\u06ba \u0628\u06be\u06cc \u062f\u06cc\u06a9\u06be\u06cc\u06ba",
        "\u06a9\u062a\u0627\u0628\u06cc\u0627\u062a",
        "\u0645\u0627\u062e\u0630",
        "\u0645\u0622\u062e\u0630",
        "\u062d\u0648\u0627\u0634\u06cc",
        "\u0630\u0631\u0627\u0626\u0639",
        "\u0646\u06af\u0627\u0631 \u062e\u0627\u0646\u06c1",
        "\u0628\u06cc\u0631\u0648\u0646\u06cc \u0648\u0633\u0627\u0626\u0644",
        "References",
        "External links",
        "See also",
    )
}


def cut_tail_sections(text):
    """Drop everything from the first reference/link heading onwards."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if i and line.strip(" :").rstrip(":") in _TAIL_HEADINGS:
            return "\n".join(lines[:i])
    return text


# ---------------------------------------------------------------------------
# 3b. Links and personal data
# ---------------------------------------------------------------------------
_URL_RE = re.compile(r"(?:https?://|ftp://|www\.)\S+", re.I)
_BARE_DOMAIN_RE = re.compile(
    r"(?<![\w.@])[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:com|net|org|pk|info|edu|gov|co|tv|me)\b(?:/\S*)?",
    re.I,
)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_HANDLE_RE = re.compile(r"(?<![\w@])@[A-Za-z0-9_]{2,}")
_PHONE_RE = re.compile(
    r"(?<![\w+])\+\d{1,3}[ -]?\(?\d{2,4}\)?[ -]?\d{3,4}[ -]?\d{3,4}(?!\d)"   # +92 300 1234567
    r"|(?<!\d)0[23]\d{2}[ -]?\d{7}(?!\d)"                                  # 0300-1234567
    r"|(?<!\d)0\d{2,3}[ -]\d{6,8}(?!\d)"                                   # 042-35761234
    r"|(?<!\d)\d{5}-\d{7}-\d(?!\d)"                                        # national id number
)
_SPACES_RE = re.compile(r"[ \t]{2,}")


def scrub_personal(text):
    """Remove URLs, e-mail addresses, @handles and phone or ID numbers.

    Returns (text, counts) where counts is a dict with the number of removals
    for each kind.
    """
    counts = {"url": 0, "email": 0, "handle": 0, "phone": 0}
    if "@" in text:
        text, counts["email"] = _EMAIL_RE.subn(" ", text)
        text, counts["handle"] = _HANDLE_RE.subn(" ", text)
    if "http" in text or "www." in text or "ftp" in text:
        text, counts["url"] = _URL_RE.subn(" ", text)
    if "." in text:
        text, n = _BARE_DOMAIN_RE.subn(" ", text)
        counts["url"] += n
    text, counts["phone"] = _PHONE_RE.subn(" ", text)
    if sum(counts.values()):
        text = "\n".join(_SPACES_RE.sub(" ", l).strip() for l in text.split("\n"))
    return text, counts


# ---------------------------------------------------------------------------
# 4. Language filtering
# ---------------------------------------------------------------------------
# Letters of the Arabic script as used for Urdu (no marks, digits or
# punctuation), plus Arabic Supplement.
_URDU_LETTER_RE = re.compile(
    "[\u0621-\u063f\u0641-\u064a\u066e-\u06d3\u06d5\u06ee\u06ef\u06fa-\u06ff\u0750-\u077f]"
)
_ANY_LETTER_RE = re.compile(r"[^\W\d_]")
# Any letter that is not an Urdu letter. A line without one is entirely Urdu
# script, which is the common case and needs only one counting pass.
_OTHER_LETTER_RE = re.compile(
    r"[^\W\d_\u0621-\u063f\u0641-\u064a\u066e-\u06d3\u06d5\u06ee\u06ef\u06fa-\u06ff\u0750-\u077f]"
)


def urdu_letter_ratio(line):
    """(urdu_letters, all_letters) for a line."""
    return len(_URDU_LETTER_RE.findall(line)), len(_ANY_LETTER_RE.findall(line))


def filter_lines(text, min_ratio=0.5, min_urdu_letters=2):
    """Keep lines that are mostly Urdu script.

    The ratio is Urdu letters over all letters, so English words inside an Urdu
    sentence only lower it a little. A line is dropped when fewer than
    min_ratio of its letters are Urdu, or when it has fewer than
    min_urdu_letters Urdu letters (numbers only, symbols only, one stray
    character). Returns (text, lines_in, lines_dropped).
    """
    kept = []
    dropped = 0
    lines = text.split("\n")
    for line in lines:
        if line.isascii():
            dropped += 1
            continue
        if _OTHER_LETTER_RE.search(line) is None:
            # only Urdu-script letters, so one counting pass is enough
            ok = len(_URDU_LETTER_RE.findall(line)) >= min_urdu_letters
        else:
            urdu, total = urdu_letter_ratio(line)
            ok = urdu >= min_urdu_letters and urdu >= min_ratio * total
        if ok:
            kept.append(line)
        else:
            dropped += 1
    return "\n".join(kept), len(lines), dropped


_PUNCT_EDGES = ".,;:!?()[]{}\"'-*/\\|\u06d4\u060c\u061f\u061b\u00ab\u00bb"

# Frequent Urdu function words. Persian, Arabic and Pashto text written in the
# same script almost never contains them at this density.
_URDU_FUNCTION_WORDS = {
    normalize(w) for w in (
        "\u06a9\u06d2 \u06a9\u06cc \u06a9\u0627 \u06a9\u0648 \u0645\u06cc\u06ba \u0633\u06d2 \u0646\u06d2 "
        "\u0627\u0648\u0631 \u06c1\u06d2 \u06c1\u06cc\u06ba \u062a\u06be\u0627 \u062a\u06be\u06cc \u062a\u06be\u06d2 "
        "\u067e\u0631 \u06cc\u06c1 \u0648\u06c1 \u0628\u06be\u06cc \u0646\u06c1\u06cc\u06ba \u0627\u06cc\u06a9 "
        "\u06a9\u06c1 \u06a9\u0631 \u062c\u0648 \u0627\u0633 \u0627\u0646 \u0644\u06cc\u06d2 \u06a9\u06cc\u0627 "
        "\u06af\u06cc\u0627 \u06af\u0626\u06cc \u06af\u0626\u06d2 \u06c1\u0648 \u06c1\u0648\u0627 \u06c1\u0648\u0626\u06cc "
        "\u06c1\u0648\u0626\u06d2 \u0631\u06c1\u0627 \u0631\u06c1\u06cc \u0631\u06c1\u06d2 \u06c1\u0648\u062a\u0627 "
        "\u06c1\u0648\u062a\u06cc \u06c1\u0648\u062a\u06d2 \u0633\u06a9\u062a\u0627 \u0633\u06a9\u062a\u06d2 "
        "\u06c1\u0645 \u0622\u067e \u062a\u0648 \u062a\u06a9 \u0644\u06cc\u06a9\u0646 \u0627\u06af\u0631 \u062c\u0628 "
        "\u06a9\u06c1\u0627 \u06a9\u0631\u0646\u06d2 \u0648\u0627\u0644\u06d2 \u0648\u0627\u0644\u06cc \u0648\u0627\u0644\u0627 "
        "\u0628\u0639\u062f \u0633\u0627\u062a\u06be \u06a9\u0633\u06cc \u06a9\u0648\u0626\u06cc \u06c1\u06cc "
        "\u0635\u0631\u0641 \u062c\u0633 \u062c\u0646 \u062f\u06cc\u0627 \u062f\u06cc \u06c1\u0648\u06ba"
    ).split()
}


def function_word_rate(text, max_tokens=3000):
    """Share of whitespace tokens that are common Urdu function words, over
    the first max_tokens tokens."""
    tokens = text.split(None, max_tokens)[:max_tokens]
    if not tokens:
        return 0.0
    hits = 0
    for tok in tokens:
        if tok in _URDU_FUNCTION_WORDS or tok.strip(_PUNCT_EDGES) in _URDU_FUNCTION_WORDS:
            hits += 1
    return hits / len(tokens)


def is_urdu_document(text, min_rate=0.05, min_tokens=30):
    """False for documents that are in Arabic script but not in Urdu.

    Short documents are given the benefit of the doubt, because the rate is
    unreliable below a few dozen tokens.
    """
    if len(text.split(None, min_tokens)) < min_tokens:
        return True
    return function_word_rate(text) >= min_rate
