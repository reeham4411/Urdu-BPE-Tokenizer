"""Unit tests for textclean.py.

Run from the repository root:
    python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import textclean as T  # noqa: E402

URDU_SENTENCE = "یہ ایک سادہ جملہ ہے اور اس میں کوئی خاص بات نہیں ہے۔"
PERSIAN_SENTENCE = "این یک متن فارسی است که در آن از کلمات فارسی استفاده شده است و برای آزمایش به کار می رود"
ARABIC_SENTENCE = "ذلك الكتاب لا ريب فيه هدى للمتقين الذين يؤمنون بالغيب ويقيمون الصلاة"


class StripMarkup(unittest.TestCase):
    def test_html_tags_removed(self):
        self.assertEqual(T.strip_markup("<b>اردو</b> <span class='x'>زبان</span>"), "اردو زبان")

    def test_block_tags_become_line_breaks(self):
        out = T.strip_markup("پہلی<br>دوسری<p>تیسری</p>")
        self.assertEqual([l for l in out.split("\n") if l], ["پہلی", "دوسری", "تیسری"])

    def test_table_cells_end_up_on_separate_lines(self):
        out = T.strip_markup("<table><tr><td>الف</td><td>ب</td></tr></table>")
        self.assertEqual([l for l in out.split("\n") if l], ["الف", "ب"])

    def test_script_style_and_comments_dropped_with_content(self):
        out = T.strip_markup("الف<script>var x = 1;</script>ب<!-- note -->ج<style>p{}</style>")
        self.assertEqual(out.split(), ["الف", "ب", "ج"])

    def test_ref_tags_dropped_with_content(self):
        self.assertEqual(T.strip_markup("جملہ<ref>Some source</ref> ختم<ref name=a/>").strip(), "جملہ  ختم")

    def test_entities_unescaped(self):
        self.assertEqual(T.strip_markup("a &amp; b &quot;c&quot; &#1575;"), 'a & b "c" ا')

    def test_plain_ampersand_and_less_than_survive(self):
        self.assertEqual(T.strip_markup("a & b and 3 < 5"), "a & b and 3 < 5")

    def test_endoftext_string_removed(self):
        self.assertNotIn(T.END_OF_TEXT, T.strip_markup("الف <|endoftext|> ب"))

    def test_edit_links_removed(self):
        self.assertEqual(T.strip_markup("عنوان[ترمیم]"), "عنوان")
        self.assertEqual(T.strip_markup("جملہ[1] اگلی[23]"), "جملہ اگلی")

    def test_wiki_markup_ignored_unless_requested(self):
        text = "الف | ب = ج"
        self.assertEqual(T.strip_markup(text), text)


class StripWikiMarkup(unittest.TestCase):
    def w(self, text):
        return T.strip_markup(text, wiki=True)

    def test_templates_removed_including_nested(self):
        self.assertEqual(self.w("الف {{سانچہ|x|{{y}}}} ب").split(), ["الف", "ب"])

    def test_links_keep_display_text(self):
        self.assertEqual(self.w("[[لاہور]] اور [[پاکستان|ملک]]"), "لاہور اور ملک")

    def test_file_and_category_links_dropped(self):
        out = self.w("متن\n[[File:a.jpg|thumb|caption]]\n[[زمرہ:شہر]]\nآخر")
        self.assertEqual([l for l in out.split("\n") if l.strip()], ["متن", "آخر"])

    def test_external_link_keeps_label(self):
        self.assertEqual(self.w("[http://example.com ویب گاہ]"), "ویب گاہ")

    def test_bold_and_italic_marks_removed(self):
        self.assertEqual(self.w("'''اردو''' ''زبان''"), "اردو زبان")

    def test_headings_lose_equals_signs(self):
        self.assertEqual(self.w("== تاریخ ==\nمتن"), "تاریخ\nمتن")

    def test_list_markers_removed(self):
        self.assertEqual(self.w("* الف\n# ب\n: ج"), "الف\nب\nج")

    def test_wiki_table_removed(self):
        out = self.w("پہلے\n{| class=wikitable\n|-\n| الف || ب\n|}\nبعد")
        self.assertEqual([l for l in out.split("\n") if l.strip()], ["پہلے", "بعد"])

    def test_structure_lines_dropped(self):
        out = self.w("متن\nزمرہ:لاہور\nتصویر:a.jpg\n| خانہ\nآخر")
        self.assertEqual([l for l in out.split("\n") if l.strip()], ["متن", "آخر"])

    def test_magic_words_removed(self):
        self.assertEqual(self.w("__NOTOC__ متن").strip(), "متن")


class TailSections(unittest.TestCase):
    def test_cut_at_references_heading(self):
        text = "پہلی سطر\nدوسری سطر\nحوالہ جات\nکتاب ایک\nکتاب دو"
        self.assertEqual(T.cut_tail_sections(text), "پہلی سطر\nدوسری سطر")

    def test_cut_at_first_of_several_headings(self):
        text = "الف\nمزید دیکھیے\nب\nحوالہ جات\nج"
        self.assertEqual(T.cut_tail_sections(text), "الف")

    def test_heading_with_trailing_colon(self):
        self.assertEqual(T.cut_tail_sections("الف\nحوالہ جات:\nب"), "الف")

    def test_heading_text_inside_a_sentence_is_not_a_heading(self):
        text = "الف\nیہ حوالہ جات کی فہرست ہے\nب"
        self.assertEqual(T.cut_tail_sections(text), text)

    def test_text_without_heading_untouched(self):
        self.assertEqual(T.cut_tail_sections("الف\nب"), "الف\nب")


class ScrubPersonal(unittest.TestCase):
    def scrub(self, text):
        return T.scrub_personal(text)

    def test_url_removed(self):
        out, counts = self.scrub("دیکھیں https://example.com/a?b=1 اور www.test.pk ختم")
        self.assertEqual(out, "دیکھیں اور ختم")
        self.assertEqual(counts["url"], 2)

    def test_bare_domain_removed(self):
        out, counts = self.scrub("ویب سائٹ dawn.com پر ہے")
        self.assertNotIn("dawn", out)
        self.assertEqual(counts["url"], 1)

    def test_email_removed(self):
        out, counts = self.scrub("رابطہ ali.khan@example.com پر کریں")
        self.assertEqual(out, "رابطہ پر کریں")
        self.assertEqual(counts["email"], 1)

    def test_handle_removed(self):
        out, counts = self.scrub("ٹویٹ @some_user_1 نے کی")
        self.assertEqual(out, "ٹویٹ نے کی")
        self.assertEqual(counts["handle"], 1)

    def test_phone_numbers_removed(self):
        for number in ("+92 300 1234567", "0300-1234567", "03001234567", "042-35761234",
                       "+92-42-35761234"):
            with self.subTest(number=number):
                out, counts = self.scrub("فون " + number + " پر")
                self.assertEqual(counts["phone"], 1, out)
                self.assertEqual(out, "فون پر")

    def test_national_id_removed(self):
        out, counts = self.scrub("شناختی کارڈ 35202-1234567-1 ہے")
        self.assertEqual(counts["phone"], 1)
        self.assertNotIn("35202", out)

    def test_ordinary_numbers_survive(self):
        for text in ("30000000000", "1073741824", "2019-2020", "12-05-2019", "3.14", "1,000,000",
                     "سال 1947 میں", "9789696023722"):
            with self.subTest(text=text):
                out, counts = self.scrub(text)
                self.assertEqual(out, text)
                self.assertEqual(sum(counts.values()), 0)

    def test_text_without_personal_data_is_unchanged(self):
        out, counts = self.scrub(URDU_SENTENCE)
        self.assertEqual(out, URDU_SENTENCE)
        self.assertEqual(sum(counts.values()), 0)


class LanguageFilter(unittest.TestCase):
    def test_urdu_line_kept(self):
        out, n_in, dropped = T.filter_lines(URDU_SENTENCE)
        self.assertEqual((out, n_in, dropped), (URDU_SENTENCE, 1, 0))

    def test_code_mixing_kept(self):
        line = "آج کل Machine Learning اور AI بہت مقبول ہیں۔"
        out, _, dropped = T.filter_lines(line)
        self.assertEqual((out, dropped), (line, 0))

    def test_english_line_dropped(self):
        out, n_in, dropped = T.filter_lines("This line is entirely English.\n" + URDU_SENTENCE)
        self.assertEqual(out, URDU_SENTENCE)
        self.assertEqual((n_in, dropped), (2, 1))

    def test_mostly_english_line_dropped(self):
        out, _, dropped = T.filter_lines("The quick brown fox jumps over the lazy dog اردو")
        self.assertEqual((out, dropped), ("", 1))

    def test_digits_and_symbols_only_lines_dropped(self):
        out, _, dropped = T.filter_lines("12345\n----\n!!!\n" + URDU_SENTENCE)
        self.assertEqual((out, dropped), (URDU_SENTENCE, 3))

    def test_single_stray_letter_dropped(self):
        out, _, dropped = T.filter_lines("ا\n" + URDU_SENTENCE)
        self.assertEqual((out, dropped), (URDU_SENTENCE, 1))

    def test_other_scripts_dropped(self):
        out, _, dropped = T.filter_lines("これは日本語の文章です\nयह हिंदी का वाक्य है\n" + URDU_SENTENCE)
        self.assertEqual((out, dropped), (URDU_SENTENCE, 2))

    def test_threshold_is_adjustable(self):
        line = "اردو ok fine good"
        self.assertEqual(T.filter_lines(line, min_ratio=0.5)[2], 1)
        self.assertEqual(T.filter_lines(line, min_ratio=0.2)[2], 0)


class UrduDocument(unittest.TestCase):
    def test_urdu_document_accepted(self):
        self.assertTrue(T.is_urdu_document((URDU_SENTENCE + " ") * 5))

    def test_persian_document_rejected(self):
        self.assertFalse(T.is_urdu_document((PERSIAN_SENTENCE + " ") * 4))

    def test_arabic_document_rejected(self):
        self.assertFalse(T.is_urdu_document((ARABIC_SENTENCE + " ") * 4))

    def test_short_documents_get_benefit_of_the_doubt(self):
        self.assertTrue(T.is_urdu_document(ARABIC_SENTENCE))

    def test_function_word_rate_ignores_edge_punctuation(self):
        self.assertEqual(T.function_word_rate("ہے۔ ہیں، (اور)"), 1.0)

    def test_empty_text(self):
        self.assertEqual(T.function_word_rate(""), 0.0)


if __name__ == "__main__":
    unittest.main()
