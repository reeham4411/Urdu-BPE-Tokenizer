"""Assemble report.pdf from report/report.md and the generated analysis files.

Usage (from the repository root):
    python -X utf8 report/build_report.py              (rerun the analysis, then build)
    python -X utf8 report/build_report.py --no-refresh (only rebuild the PDF)

Steps:
    1. unless --no-refresh, run the analysis scripts so every number is current:
       training_summary, compare (Q2), merges (Q1, needs the tokenizer),
       bad_inputs (Q3), norm_tokens and ablation_digits (the first run of
       ablation_digits trains a second tokenizer, as long as train_tokenizer.py);
    2. replace each {{include generated/<file>}} in report.md with that file,
       or with a "pending" note if it does not exist yet;
    3. convert to HTML (report/report.html) with a compact A4 style;
    4. print it to report.pdf in the repository root with headless Chrome or
       Edge, which also renders the Urdu text;
    5. report the page count (the handout allows at most four) and any TODO
       markers still left in the text.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "report"
INCLUDE = re.compile(r"\{\{include (generated/[^}]+)\}\}")
ANALYSES = ["analysis.training_summary", "analysis.compare", "analysis.merges",
            "analysis.bad_inputs", "analysis.norm_tokens", "analysis.ablation_digits"]
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium", "chromium-browser", "microsoft-edge",
]

CSS = """
@page { size: A4; margin: 13mm 14mm 13mm 14mm; }
body { font-family: "Segoe UI", "Noto Naskh Arabic", Arial, sans-serif; font-size: 8.6pt;
       line-height: 1.32; color: #111; }
h1 { font-size: 14pt; margin: 0 0 2pt 0; }
h2 { font-size: 10.5pt; margin: 8pt 0 3pt 0; border-bottom: 1px solid #bbb; }
p { margin: 3pt 0; text-align: justify; }
table { border-collapse: collapse; margin: 3pt 0; font-size: 7.3pt; }
th, td { border: 1px solid #ccc; padding: 1pt 4pt; vertical-align: top; }
th { background: #f0f0f0; }
code { font-family: Consolas, "Segoe UI", monospace; font-size: 7.6pt; background: #f4f4f4;
       padding: 0 2px; unicode-bidi: isolate; }
img { max-width: 100%; display: block; margin: 3pt auto; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; }
.pending { color: #a00; }
.cover { break-after: page; text-align: center; font-family: Arial, "Segoe UI", sans-serif;
         font-weight: bold; font-size: 14pt; padding-top: 6mm; }
.cover p { text-align: center; margin: 0 0 22pt 0; }
.cover-logo { width: 62%; margin: 0 auto 30pt auto; }
.cover-table { width: 100%; margin: 26pt 0 50pt 0; font-size: 13pt; border: 1.5px solid #000; }
.cover-table th { background: #000; color: #fff; border: 1.5px solid #000; padding: 5pt; }
.cover-table td { border: 1.5px solid #000; padding: 5pt; text-align: center; }
.cover p.cover-instructor { margin-top: 40pt; }
.cover-links { margin-top: 36pt; font-size: 10.5pt; }
.cover-links p { margin: 0 0 12pt 0; }
.cover-links a { color: #1a4fa0; white-space: nowrap; }
.todo { background: #fff3c4; }
"""


def refresh():
    for module in ANALYSES:
        print(f"== {module}", flush=True)
        done = subprocess.run([sys.executable, "-X", "utf8", "-m", module], cwd=ROOT)
        if done.returncode:
            print(f"   ({module} did not finish; its section will show as pending)")


def assemble(text):
    def include(match):
        path = REPORT / match.group(1)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f'<span class="pending">Pending: {match.group(1)} not generated yet.</span>'
    return INCLUDE.sub(include, text)


def to_html(md_text):
    import markdown
    body = markdown.markdown(md_text, extensions=["tables", "md_in_html"])
    body = re.sub(r"(TODO\([^)]*\)[^<]*)", r'<span class="todo">\1</span>', body)
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Urdu BPE Tokenizer"
            f"</title><style>{CSS}</style></head><body>{body}</body></html>")


def find_browser():
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    return None


def print_pdf(html_path, pdf_path):
    browser = find_browser()
    if not browser:
        sys.exit("no Chrome or Edge found; open report/report.html and print it to PDF")
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()],
                   check=True, capture_output=True, timeout=120)


def page_count(pdf_path):
    data = pdf_path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page(?!s)", data))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-refresh", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "report.pdf")
    args = ap.parse_args()
    if not args.no_refresh:
        refresh()
    md_text = assemble((REPORT / "report.md").read_text(encoding="utf-8"))
    html_path = REPORT / "report.html"
    html_path.write_text(to_html(md_text), encoding="utf-8")
    print_pdf(html_path, args.out)
    pages = page_count(args.out)
    cover = 1 if 'class="cover"' in md_text else 0
    body = pages - cover
    todos = sorted(set(re.findall(r"TODO\([^)]*\)", md_text)))
    pending = md_text.count('class="pending"') + md_text.count("*Pending:")
    print(f"\nwrote {args.out} ({body} pages{' plus the cover page' if cover else ''}"
          f"{', OVER THE 4-PAGE LIMIT' if body > 4 else ''})")
    if todos:
        print("TODO markers left:", ", ".join(todos))
    if pending:
        print(f"{pending} section(s) still pending (train the tokenizer, then rebuild)")


if __name__ == "__main__":
    main()
