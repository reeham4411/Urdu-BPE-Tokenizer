"""Hand-picked inputs for Part C.

HAND_PICKED are the seven inputs Question 2 asks for. They are passed through
normalize() before tokenizing (see normalized_inputs), because the tokenizer
was trained on normalised text and the corpus pipeline would normalise them
too. All three tokenizers get the same normalised string.

BAD_CANDIDATES feed Question 3. These are NOT normalised on purpose: they are
what real users type. Each comes with the reason we expect it to go badly;
analysis/bad_inputs.py measures them and the report keeps the three worst.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from normalize import normalize  # noqa: E402

HAND_PICKED = {
    "News": (
        "وفاقی حکومت نے آئندہ مالی سال کے بجٹ میں تعلیم اور صحت کے شعبوں کے لیے "
        "اضافی فنڈز مختص کرنے کا اعلان کیا ہے۔ وزیر خزانہ کے مطابق یہ رقم صوبوں کے "
        "ساتھ مشاورت کے بعد تقسیم کی جائے گی۔"),
    "Poetry": (  # Mirza Ghalib (1797-1869), public domain
        "ہزاروں خواہشیں ایسی کہ ہر خواہش پہ دم نکلے\n"
        "بہت نکلے مرے ارمان لیکن پھر بھی کم نکلے"),
    "Urdu with English": (
        "کل کی meeting میں ہم نے نئے software update اور cloud storage کے بارے میں "
        "بات کی، لیکن final decision ابھی pending ہے۔"),
    "Roman Urdu": (
        "Aaj mausam bohat acha hai, chalo shaam ko chai peene chalte hain. "
        "Kal se office dobara shuru ho jaye ga."),
    "Numbers and dates": (
        "پاکستان 14 اگست 1947 کو آزاد ہوا۔ 2023 کی مردم شماری میں آبادی 241,499,431 "
        "تھی۔ اجلاس 03/10/2026 کو صبح 9:30 بجے ہوگا اور قیمت 1,250.50 روپے ہے۔"),
    "Diacritics": (
        "اُردُو زَبان کی خُوبصُورتی اِس کے اِعراب میں بھی ہے؛ تقریباً ہر بَچّہ "
        "اِسے شَوق سے پَڑھتا ہے۔"),
    "Personal names": (
        "محمد علی جناح، علامہ محمد اقبال، فیض احمد فیض، بے نظیر بھٹو، عبدالستار ایدھی "
        "اور ملالہ یوسفزئی پاکستان کی تاریخ کے اہم نام ہیں۔"),
}

# name -> (text, why we expect our tokenizer to struggle)
BAD_CANDIDATES = {
    "Roman Urdu": (
        "Yaar tum kal kahan thay? Main ne tumhein bohat dhoonda magar tum mile hi nahi.",
        "Urdu written in Latin letters is absent from the corpus by design (DATA_CARD.md), "
        "so the few Latin merges come from English code-mixing and do not cover Urdu "
        "spelt in Latin."),
    "Unnormalised Arabic letters": (
        "\u0643\u062a\u0627\u0628 \u0645\u064a\u06ba \u064a\u06c1 \u0644\u0643\u06be\u0627 "
        "\u06c1\u06d2 \u0643\u06c1 \u0647\u0645 \u0627\u064a\u0643 \u06c1\u064a\u06ba",
        "Typed with Arabic kaf, yeh and heh (U+0643, U+064A, U+0647). normalize() maps "
        "them to the Urdu letters, so they almost never occur in train.txt and the tokenizer "
        "falls back to two bytes per letter. Normalising the input first fixes it."),
    "Urdu digits": (
        "\u06f1\u06f4 \u0627\u06af\u0633\u062a \u06f1\u06f9\u06f4\u06f7 "
        "\u0627\u0648\u0631 \u06f2\u06f0\u06f2\u06f6 \u06a9\u06cc "
        "\u0642\u06cc\u0645\u062a \u06f1\u06f2\u06f5\u06f0 \u0631\u0648\u067e\u06d2",
        "Extended Arabic-Indic digits were converted to ASCII during cleaning, so every "
        "Urdu digit costs two byte tokens."),
    "Social media": (
        "زبردست!!! 😂😂🔥🔥 #پاکستان_زندہ_باد @ali_khan کیا بات ہے 👏👏",
        "Emoji, hashtags and handles were removed or never present in the cleaned corpus; "
        "each emoji is four bytes with no learned merges."),
    "Missing spaces": (
        "لیکنوہکہتاہےکہمیںکلآؤںگا",
        "Urdu writers often drop spaces after non-joining letters because the text still "
        "looks right; the pre-tokeniser then sees one long rare word."),
    "URL and code": (
        "https://www.example.com/news/2026/10/urdu?id=4471&lang=ur",
        "URLs were scrubbed from the corpus as personal data, so their pieces are rare."),
    "Hindi (Devanagari)": (
        "उर्दू और हिंदी बोलचाल में लगभग एक जैसी हैं।",
        "The same spoken language in another script: Devanagari never occurs in train.txt, "
        "so each character is three byte tokens."),
}


def normalized_inputs():
    return {name: normalize(text) for name, text in HAND_PICKED.items()}
