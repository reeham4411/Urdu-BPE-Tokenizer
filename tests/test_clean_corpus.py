"""End-to-end test of clean_corpus.py on a tiny synthetic corpus.

Run from the repository root:
    python -m unittest discover -s tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
END = "<|endoftext|>"


def sentence(i):
    topics = ["لاہور", "کراچی", "پشاور", "کوئٹہ", "ملتان", "فیصل آباد", "راولپنڈی", "حیدرآباد"]
    verbs = ["بہت بڑا شہر ہے", "ایک تاریخی شہر ہے", "کا موسم اچھا ہے", "میں کئی باغات ہیں"]
    return f"{topics[i % len(topics)]} {verbs[(i // len(topics)) % len(verbs)]} اور نمبر {i} بھی ہے۔"


def make_raw(raw):
    (raw / "urwiki").mkdir(parents=True)
    (raw / "lines").mkdir()
    for d in range(60):
        body = "\n".join(sentence(d * 7 + k) for k in range(6))
        # Arabic yeh and kaf variants, HTML, a URL and a trailing references section
        text = f"<p>{body}</p>\nاس میں \u0643 اور \u064a کا استعمال ہے۔ http://example.com/{d}\nحوالہ جات\nکتاب {d}\n"
        (raw / "urwiki" / f"{d}.txt").write_text(text, encoding="utf-8")
    (raw / "urwiki" / "dup.txt").write_text(
        (raw / "urwiki" / "3.txt").read_text(encoding="utf-8"), encoding="utf-8")
    boiler = "یہ سطر ہر صفحے پر دہرائی جاتی ہے۔"
    lines = []
    for i in range(1200):
        lines.append(sentence(i * 3) + f" {i}")
        if i % 20 == 0:
            lines.append(boiler)
        if i % 50 == 0:
            lines.append("This is an English line that must be filtered out.")
    (raw / "lines" / "all.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(raw, out, extra=()):
    work = Path(out).parent / "work"
    reports = Path(out).parent / "reports"
    cmd = [sys.executable, "-X", "utf8", str(ROOT / "clean_corpus.py"),
           "--raw", str(raw), "--out", str(out), "--work", str(work), "--reports", str(reports),
           "--line-source", "lines", "--quiet", "--boilerplate-min-docs", "5",
           "--min-words", "5", "--chunk-lines", "30", *extra]
    subprocess.run(cmd, check=True, capture_output=True)
    return json.loads((reports / "cleaning_report.json").read_text(encoding="utf-8"))


def read_docs(path):
    text = Path(path).read_text(encoding="utf-8")
    sep = "\n" + END + "\n"
    assert text.endswith(sep)
    return text[: -len(sep)].split(sep)


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.raw = base / "raw"
        make_raw(cls.raw)
        cls.out = base / "run1" / "clean"
        cls.report = run(cls.raw, cls.out)
        cls.docs = {s: read_docs(cls.out / f"{s}.txt") for s in ("train", "val", "test")}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_three_files_written_with_end_marker_after_each_document(self):
        for split, docs in self.docs.items():
            self.assertGreater(len(docs), 0, split)
        raw_text = (self.out / "train.txt").read_text(encoding="utf-8")
        self.assertEqual(raw_text.count(END), len(self.docs["train"]))

    def test_split_is_by_document_and_disjoint(self):
        sets = {k: set(v) for k, v in self.docs.items()}
        self.assertFalse(sets["train"] & sets["val"])
        self.assertFalse(sets["train"] & sets["test"])
        self.assertFalse(sets["val"] & sets["test"])

    def test_split_proportions_are_roughly_98_1_1(self):
        n = sum(len(v) for v in self.docs.values())
        self.assertGreaterEqual(len(self.docs["train"]) / n, 0.9)
        self.assertGreaterEqual(len(self.docs["val"]), 1)
        self.assertGreaterEqual(len(self.docs["test"]), 1)

    def test_every_source_appears_in_val_and_test(self):
        rows = (self.out / "doc_index.tsv").read_text(encoding="utf-8").splitlines()[1:]
        seen = {(r.split("\t")[0], r.split("\t")[2]) for r in rows}
        for split in ("train", "val", "test"):
            for source in ("urwiki", "lines"):
                self.assertIn((split, source), seen)

    def test_cleaning_effects(self):
        everything = "\n".join(d for docs in self.docs.values() for d in docs)
        self.assertNotIn("\u064a", everything)             # Arabic yeh
        self.assertNotIn("\u0643", everything)             # Arabic kaf
        self.assertNotIn("<p>", everything)
        self.assertNotIn("http", everything)
        self.assertNotIn("This is an English line", everything)
        self.assertNotIn("حوالہ جات", everything)           # references section cut
        self.assertNotIn("ہر صفحے پر دہرائی", everything)    # boilerplate line
        self.assertNotIn(END, everything)
        for doc in everything.split("\n"):
            self.assertEqual(doc, doc.strip())
        self.assertNotIn("\n\n", everything)

    def test_exact_duplicate_document_removed(self):
        self.assertEqual(self.report["docs_removed"]["exact_dup"], 1)

    def test_bytes_add_up(self):
        t = self.report["totals"]
        removed = sum(self.report["bytes_removed"].values())
        self.assertEqual(t["raw_bytes"] - removed, t["final_bytes"])

    def test_final_size_matches_files(self):
        written = sum((self.out / f"{s}.txt").stat().st_size for s in ("train", "val", "test"))
        n_docs = sum(len(v) for v in self.docs.values())
        self.assertEqual(written, self.report["totals"]["final_bytes"] + n_docs * (len(END) + 2))

    def test_same_seed_gives_identical_files(self):
        out2 = Path(self.tmp.name) / "run2" / "clean"
        run(self.raw, out2)
        for name in ("train.txt", "val.txt", "test.txt", "doc_index.tsv"):
            self.assertEqual((self.out / name).read_bytes(), (out2 / name).read_bytes(), name)

    def stats(self, clean_dir, out_name):
        out = Path(self.tmp.name) / out_name
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "corpus_stats.py"),
             "--clean", str(clean_dir), "--out", str(out)],
            capture_output=True, text=True, encoding="utf-8")
        return proc, out

    def test_stats_audit_passes_on_clean_output(self):
        proc, out = self.stats(self.out, "stats_ok.json")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = json.loads(out.read_text(encoding="utf-8"))
        n_docs = sum(len(v) for v in self.docs.values())
        self.assertEqual(data["total"]["documents"], n_docs)
        self.assertGreater(data["total"]["words"], 0)
        self.assertGreater(data["total"]["unique_words"], 0)
        self.assertEqual(data["problems"], [])
        self.assertEqual(set(data["per_source"]), {"urwiki", "lines"})

    def test_stats_audit_detects_unnormalised_text(self):
        bad = Path(self.tmp.name) / "tampered"
        bad.mkdir()
        for name in ("train.txt", "val.txt", "test.txt", "doc_index.tsv"):
            (bad / name).write_bytes((self.out / name).read_bytes())
        with (bad / "train.txt").open("a", encoding="utf-8", newline="") as fh:
            fh.write(chr(0x0643) + "tab\n" + END + "\n")  # Arabic kaf, which normalize removes
        proc, _ = self.stats(bad, "stats_bad.json")
        self.assertNotEqual(proc.returncode, 0)

    def test_stats_audit_detects_missing_end_marker(self):
        bad = Path(self.tmp.name) / "truncated"
        bad.mkdir()
        for name in ("train.txt", "val.txt", "test.txt", "doc_index.tsv"):
            (bad / name).write_bytes((self.out / name).read_bytes())
        with (bad / "val.txt").open("a", encoding="utf-8", newline="") as fh:
            fh.write("text without a marker")
        proc, _ = self.stats(bad, "stats_bad2.json")
        self.assertNotEqual(proc.returncode, 0)

    def test_different_seed_changes_the_split(self):
        out3 = Path(self.tmp.name) / "run3" / "clean"
        run(self.raw, out3, ["--seed", "99"])
        self.assertNotEqual((self.out / "val.txt").read_bytes(), (out3 / "val.txt").read_bytes())


if __name__ == "__main__":
    unittest.main()
