"""Unit tests for normalize.py.

Run from the repository root with either of:
    python -m unittest discover -s tests -v
    python -m pytest tests

Code points are written as escapes because the variants being tested look the
same on screen.
"""
import collections
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from normalize import normalize, rule_counts, RULES  # noqa: E402

YEH_ARABIC = "\u064a"
ALEF_MAKSURA = "\u0649"
YEH_URDU = "\u06cc"
KAF_ARABIC = "\u0643"
KAF_URDU = "\u06a9"
HEH_ARABIC = "\u0647"
HEH_GOAL = "\u06c1"
HEH_DOACHASHMI = "\u06be"
ZWNJ = "\u200c"

# kitab, written with the Urdu letters kaf, te, alef, be
KITAB = KAF_URDU + "\u062a\u0627\u0628"
# bayn-al-aqwami: be, yeh, noon, ZWNJ, alef, lam, alef, qaf, waw, alef, mim, yeh
BAYN = "\u0628" + YEH_URDU + "\u0646"
ALAQWAMI = "\u0627\u0644\u0627\u0642\u0648\u0627\u0645" + YEH_URDU


class LetterVariants(unittest.TestCase):
    def test_arabic_yeh_becomes_urdu_yeh(self):
        self.assertEqual(normalize("\u0645" + YEH_ARABIC + "\u0631"),
                         "\u0645" + YEH_URDU + "\u0631")

    def test_alef_maksura_becomes_urdu_yeh(self):
        self.assertEqual(normalize("\u0645\u0648\u0633" + ALEF_MAKSURA),
                         "\u0645\u0648\u0633" + YEH_URDU)

    def test_urdu_yeh_unchanged(self):
        self.assertEqual(normalize(YEH_URDU), YEH_URDU)

    def test_arabic_kaf_becomes_urdu_kaf(self):
        self.assertEqual(normalize(KAF_ARABIC + "\u062a\u0627\u0628"), KITAB)

    def test_arabic_heh_becomes_heh_goal(self):
        self.assertEqual(normalize("\u0628" + HEH_ARABIC + "\u062a"),
                         "\u0628" + HEH_GOAL + "\u062a")

    def test_heh_goal_and_do_chashmi_stay_apart(self):
        self.assertEqual(normalize(HEH_GOAL), HEH_GOAL)
        self.assertEqual(normalize(HEH_DOACHASHMI), HEH_DOACHASHMI)
        self.assertNotEqual(normalize(HEH_GOAL), normalize(HEH_DOACHASHMI))

    def test_teh_marbuta_becomes_teh_marbuta_goal(self):
        self.assertEqual(normalize("\u0629"), "\u06c3")

    def test_heh_with_yeh_above_becomes_heh_goal_with_hamza(self):
        self.assertEqual(normalize("\u06c0"), "\u06c2")

    def test_alef_wasla_becomes_alef(self):
        self.assertEqual(normalize("\u0671"), "\u0627")

    def test_all_three_variants_collapse_to_one_spelling(self):
        typed_arabic = KAF_ARABIC + "\u062a\u0627\u0628 " + "\u0645" + YEH_ARABIC
        typed_urdu = KITAB + " \u0645" + YEH_URDU
        self.assertEqual(normalize(typed_arabic), normalize(typed_urdu))


class CombiningSequences(unittest.TestCase):
    def test_alef_plus_madda_composes(self):
        self.assertEqual(normalize("\u0627\u0653"), "\u0622")

    def test_yeh_plus_hamza_composes_to_yeh_with_hamza(self):
        self.assertEqual(normalize(YEH_ARABIC + "\u0654"), "\u0626")
        self.assertEqual(normalize(YEH_URDU + "\u0654"), "\u0626")
        self.assertEqual(normalize(ALEF_MAKSURA + "\u0654"), "\u0626")

    def test_arabic_heh_plus_hamza_becomes_heh_goal_with_hamza(self):
        self.assertEqual(normalize(HEH_ARABIC + "\u0654"), "\u06c2")
        self.assertEqual(normalize(HEH_GOAL + "\u0654"), "\u06c2")

    def test_repeated_diacritic_collapses(self):
        word = "\u0627\u0631\u062f\u0648"
        self.assertEqual(normalize(word + "\u064e\u064e\u064e"), word + "\u064e")

    def test_diacritics_are_kept(self):
        word = "\u0627\u064f\u0631\u062f\u064f\u0648"
        self.assertEqual(normalize(word), word)

    def test_mark_order_is_canonical(self):
        shadda, fatha = "\u0651", "\u064e"
        a = normalize("\u0628" + shadda + fatha)
        b = normalize("\u0628" + fatha + shadda)
        self.assertEqual(a, b)

    def test_orphan_mark_after_space_is_dropped(self):
        self.assertEqual(normalize("\u0627 \u064e\u0628"), "\u0627 \u0628")
        self.assertEqual(normalize("\u064e\u0628"), "\u0628")

    def test_annotation_signs_removed(self):
        name = "\u0645\u062d\u0645\u062f"
        self.assertEqual(normalize(name + "\u0610"), name)   # honorific sign
        self.assertEqual(normalize(name + "\u06d6"), name)   # quranic sign
        self.assertEqual(normalize(name + "\u06e1"), name)


class RemovedCharacters(unittest.TestCase):
    def test_tatweel_removed(self):
        self.assertEqual(normalize("\u0627\u0631\u062f\u0640\u0640\u0648"),
                         "\u0627\u0631\u062f\u0648")

    def test_invisible_characters_removed(self):
        for ch in ("\u200d", "\u200e", "\u200f", "\ufeff", "\u200b", "\u00ad",
                   "\u061c", "\u2060", "\u202a", "\u202c", "\u2066", "\u2069"):
            with self.subTest(code=hex(ord(ch))):
                self.assertEqual(normalize("\u0627" + ch + "\u0628"), "\u0627\u0628")

    def test_control_characters_removed(self):
        self.assertEqual(normalize("a\x00b\x07c\x7fd"), "abcd")

    def test_private_use_and_replacement_char_removed(self):
        self.assertEqual(normalize("a\ue001b\ufffdc"), "abc")

    def test_lone_surrogate_does_not_survive(self):
        out = normalize("a\ud800b")
        self.assertEqual(out, "ab")
        out.encode("utf-8")


class ZeroWidthNonJoiner(unittest.TestCase):
    def test_kept_between_joining_letters(self):
        word = BAYN + ZWNJ + ALAQWAMI
        self.assertEqual(normalize(word), word)

    def test_dropped_at_word_edges(self):
        self.assertEqual(normalize(ZWNJ + KITAB), KITAB)
        self.assertEqual(normalize(KITAB + ZWNJ), KITAB)
        self.assertEqual(normalize(KITAB + ZWNJ + " " + KITAB), KITAB + " " + KITAB)
        self.assertEqual(normalize(KITAB + " " + ZWNJ + KITAB), KITAB + " " + KITAB)

    def test_dropped_after_non_joining_letter(self):
        # alef never joins to the next letter, so ZWNJ changes nothing
        self.assertEqual(normalize("\u0627" + ZWNJ + "\u0628"), "\u0627\u0628")

    def test_dropped_before_non_letter(self):
        self.assertEqual(normalize("\u0628" + ZWNJ + "1"), "\u06281")

    def test_runs_collapse_to_one(self):
        self.assertEqual(normalize(BAYN + ZWNJ * 3 + ALAQWAMI),
                         BAYN + ZWNJ + ALAQWAMI)

    def test_zwj_is_not_zwnj(self):
        self.assertEqual(normalize("\u0628\u200d\u0628"), "\u0628\u0628")


class Digits(unittest.TestCase):
    def test_arabic_indic_to_ascii(self):
        self.assertEqual(normalize("\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669\u0660"),
                         "1234567890")

    def test_extended_arabic_indic_to_ascii(self):
        self.assertEqual(normalize("\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9\u06f0"),
                         "1234567890")

    def test_mixed_digits_one_convention(self):
        self.assertEqual(normalize("\u0661\u06f2" + "3"), "123")

    def test_number_punctuation(self):
        self.assertEqual(normalize("\u0663\u066b\u0661\u0664"), "3.14")
        self.assertEqual(normalize("\u0661\u066c\u0660\u0660\u0660"), "1,000")
        self.assertEqual(normalize("\u0665\u0660\u066a"), "50%")

    def test_fullwidth_digits(self):
        self.assertEqual(normalize("\uff11\uff12"), "12")


class PresentationForms(unittest.TestCase):
    def test_allah_ligature_expands(self):
        self.assertEqual(normalize("\ufdf2"), "\u0627\u0644\u0644\u06c1")

    def test_alef_before_allah_ligature_is_not_doubled(self):
        allah = "اللہ"
        self.assertEqual(normalize("ا" + chr(0xFDF2)), allah)
        self.assertEqual(normalize("ا" + chr(0xFDF2) + " کا"), allah + " کا")

    def test_lam_alef_ligature_expands(self):
        self.assertEqual(normalize("\ufefb"), "\u0644\u0627")

    def test_phrase_ligature_is_not_glued_to_neighbours(self):
        sallallahu = chr(0xFDFA)
        words = "صلی اللہ علیہ وسلم"
        self.assertEqual(normalize("آپ" + sallallahu), "آپ " + words)
        self.assertEqual(normalize("a" + sallallahu + "b"), "a " + words + " b")

    def test_isolated_form_folds_to_base_letter(self):
        self.assertEqual(normalize("\ufe8d"), "\u0627")  # isolated alef

    def test_english_ligatures_are_left_alone(self):
        self.assertEqual(normalize("of\ufb01ce"), "of\ufb01ce")


class Whitespace(unittest.TestCase):
    def test_non_breaking_and_other_spaces(self):
        self.assertEqual(normalize("a\u00a0b\u2003c\u202fd\u3000e"), "a b c d e")

    def test_runs_of_spaces(self):
        self.assertEqual(normalize("a     b"), "a b")

    def test_tab_becomes_space(self):
        self.assertEqual(normalize("a\t\tb"), "a b")

    def test_line_endings(self):
        self.assertEqual(normalize("a\r\nb\rc\u2028d\u2029e"), "a\nb\nc\nd\ne")

    def test_blank_lines_collapse(self):
        self.assertEqual(normalize("a\n\n\n\nb"), "a\nb")
        self.assertEqual(normalize("a \n \n b"), "a\nb")

    def test_edges_stripped(self):
        self.assertEqual(normalize("  \n a b \n  "), "a b")

    def test_zwsp_between_spaces_does_not_leave_double_space(self):
        self.assertEqual(normalize("a \u200b b"), "a b")


class Punctuation(unittest.TestCase):
    def test_space_before_urdu_punctuation_removed(self):
        self.assertEqual(normalize("\u0627\u0631\u062f\u0648 \u06d4"), "\u0627\u0631\u062f\u0648\u06d4")
        self.assertEqual(normalize("\u0627 \u060c \u0628"), "\u0627\u060c \u0628")
        self.assertEqual(normalize("\u0643\u064a\u0627 \u061f"), "\u06a9\u06cc\u0627\u061f")

    def test_urdu_punctuation_itself_is_kept(self):
        for ch in ("\u06d4", "\u060c", "\u061f", "\u061b"):
            self.assertEqual(normalize("\u0627" + ch), "\u0627" + ch)

    def test_word_tokenised_text_is_closed_up(self):
        # the style of the UFAL corpus: a space before every punctuation mark
        self.assertEqual(normalize("وہ گھر گیا ۔ پھر آپ ، ہم ؟"), "وہ گھر گیا۔ پھر آپ، ہم؟")

    def test_spaces_inside_brackets_removed(self):
        self.assertEqual(normalize("( 1 ) اور [ 2 ] اور { 3 }"), "(1) اور [2] اور {3}")

    def test_ascii_punctuation_after_a_space(self):
        self.assertEqual(normalize("Hello , world !"), "Hello, world!")
        self.assertEqual(normalize("وقت 10 : 30 ."), "وقت 10: 30.")

    def test_spaces_that_are_not_before_punctuation_survive(self):
        self.assertEqual(normalize("a ... b"), "a ... b")
        self.assertEqual(normalize("a - b"), "a - b")
        self.assertEqual(normalize("f (x) g"), "f (x) g")

    def test_nested_cases_settle_in_one_call(self):
        self.assertEqual(normalize("( , )"), "(,)")
        self.assertEqual(normalize("( ( x ) , )"), "((x),)")

    def test_curly_quotes(self):
        self.assertEqual(normalize("\u201cx\u201d \u2018y\u2019"), "\"x\" 'y'")

    def test_dashes_and_ellipsis(self):
        self.assertEqual(normalize("a\u2013b\u2014c"), "a-b-c")
        self.assertEqual(normalize("wait\u2026"), "wait...")


class NonUrduText(unittest.TestCase):
    def test_english_untouched(self):
        self.assertEqual(normalize("Hello, World 2024!"), "Hello, World 2024!")

    def test_emoji_untouched(self):
        self.assertEqual(normalize("ok \U0001f600 \U0001f1f5\U0001f1f0"),
                         "ok \U0001f600 \U0001f1f5\U0001f1f0")

    def test_code_mixed_sentence(self):
        s = "\u06cc\u06c1 ok \u06c1\u06d2"
        self.assertEqual(normalize(s), s)

    def test_accented_latin_is_composed(self):
        self.assertEqual(normalize("e\u0301"), "\u00e9")

    def test_empty_and_whitespace_only(self):
        self.assertEqual(normalize(""), "")
        self.assertEqual(normalize(" \n\t "), "")

    def test_endoftext_token_text_is_not_touched(self):
        self.assertEqual(normalize("a <|endoftext|> b"), "a <|endoftext|> b")


class Properties(unittest.TestCase):
    ALPHABET = list(
        "\u0627\u0628\u067e\u062a\u0679\u062c\u0686\u06a9\u06af\u0644\u0645\u0646\u06ba"
        "\u06c1\u06be\u06cc\u06d2\u0648\u0631\u0691"
        "\u064a\u0649\u0643\u0647\u0629\u06c0\u0671\u0678"
        "\u064e\u064f\u0650\u0651\u0652\u0653\u0654\u0670"
        "\u200c\u200d\u200e\u200f\u200b\ufeff\u0640\u00a0\u3000\t\r\n  "
        "\u0660\u0661\u06f2\u06f3 0123456789 \u06d4\u060c\u061f"
        "\u201c\u201d\u2019\u2014\u2026 \ufdf2\ufefb\ufe8d\uff11\u0610\u06d6"
        "abc ok \U0001f600"
    )

    def sample(self, rng, n):
        alphabet = self.ALPHABET + [chr(0xFDFA)] + list(",.!?:;()[]")
        return "".join(rng.choice(alphabet) for _ in range(n))

    def test_idempotent(self):
        rng = random.Random(7)
        for _ in range(20000):
            s = self.sample(rng, rng.randint(0, 40))
            once = normalize(s)
            self.assertEqual(normalize(once), once, repr(s))

    def test_output_is_clean(self):
        banned = (
            {"\u064a", "\u0649", "\u0643", "\u0647", "\u0640", "\u200d", "\u200e",
             "\u200f", "\u200b", "\ufeff", "\u00a0", "\u3000", "\t", "\r", "\u0629",
             "\u06c0", "\u0671", "\u0678", "\u0610", "\u06d6", "\ufdf2", "\ufefb"}
            | {chr(0x0660 + i) for i in range(10)}
            | {chr(0x06F0 + i) for i in range(10)}
        )
        rng = random.Random(11)
        for _ in range(20000):
            out = normalize(self.sample(rng, rng.randint(0, 40)))
            self.assertFalse(banned & set(out), repr(out))
            self.assertNotIn("  ", out)
            self.assertNotIn("\n\n", out)
            self.assertEqual(out, out.strip())
            out.encode("utf-8")

    def test_zwnj_only_between_letters(self):
        rng = random.Random(5)
        for _ in range(2000):
            out = normalize(self.sample(rng, rng.randint(0, 40)))
            for i, ch in enumerate(out):
                if ch == "\u200c":
                    self.assertTrue(0 < i < len(out) - 1, repr(out))
                    self.assertTrue(out[i - 1].isalpha() and out[i + 1].isalpha(), repr(out))
                    self.assertNotEqual(out[i + 1], "\u200c")

    def test_rule_counts(self):
        raw = KAF_ARABIC * 3 + YEH_ARABIC * 2 + "\u0661" + "\u06f1" + ZWNJ
        counts = rule_counts(collections.Counter(raw))
        self.assertEqual(counts["arabic_kaf_to_urdu_kaf"], 3)
        self.assertEqual(counts["arabic_yeh_to_urdu_yeh"], 2)
        self.assertEqual(counts["arabic_indic_digits_to_ascii"], 1)
        self.assertEqual(counts["extended_indic_digits_to_ascii"], 1)
        self.assertEqual(counts["zwnj_seen"], 1)
        self.assertEqual(set(counts), set(RULES))


if __name__ == "__main__":
    unittest.main()
