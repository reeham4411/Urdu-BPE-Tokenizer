"""Write DATA_CARD.md from the measured reports.

Usage (from the repository root, after clean_corpus.py and corpus_stats.py):
    python build_data_card.py

Reads source_manifest.csv (sources, licences, dates), reports/cleaning_report.json
and reports/corpus_stats.json. It also writes the cleaned size of every source
back into the cleaned_mb column of source_manifest.csv.

The tables are generated so that no number in the card is typed by hand. The
wording of the notes lives in this file; edit it here, not in DATA_CARD.md.
"""
import argparse
import csv
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Short labels for the one-page card; the full wording is in source_manifest.csv
# and docs/DATA_CARD_full.md.
SHORT_NAMES = {"ufal": "UFAL UrMonoCorp", "urwiki": "Wikipedia (API)",
               "urwikisource": "Wikisource (API)", "wikipedia_dump": "Wikipedia dump"}
SHORT_LICENCES = {"ufal": "CC BY-NC-SA 3.0", "urwiki": "CC BY-SA 4.0",
                  "urwikisource": "mostly public domain", "wikipedia_dump": "CC BY-SA 4.0"}

def step_labels(settings):
    return {
        "markup": "HTML, wiki markup, entities",
        "normalize": "Unicode normalisation (net)",
        "tail": "Reference and link sections",
        "personal": "URLs, e-mails, phone and ID numbers",
        "language": "Lines that are mostly not Urdu",
        "nonurdu_doc": "Documents with almost no Urdu function words",
        "exact_dup": "Exact duplicate documents",
        "boilerplate": f"Boilerplate lines (in {settings['boilerplate_min_docs']}+ documents)",
        "near_dup": f"Near-duplicate documents ({settings['near_dup']:.0%} of lines seen)",
        "short": f"Documents under {settings['min_words']} words",
    }


def mb(n):
    return f"{n / 1e6:,.2f}"


def pct(n, d):
    return f"{100 * n / d:.1f}%" if d else "0.0%"


def load_manifest(path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def save_manifest(path, rows, cleaned):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        fields = csv.DictReader(fh).fieldnames
    for row in rows:
        if row["source_id"] in cleaned:
            row["cleaned_mb"] = f"{cleaned[row['source_id']]:.3f}"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fields)
        writer.writeheader()
        writer.writerows(rows)


def build(manifest, report, stats, note="", full=True):
    """The card as Markdown. full=False gives the one-page card the handout asks for
    (sources, totals, cleaning steps, gaps); full=True adds the per-source detail and
    the normalisation decisions."""
    sources = report["per_source"]
    totals = report["totals"]
    removed = report["bytes_removed"]
    docs_removed = report["docs_removed"]
    rules = report["normalization_rule_counts"]
    n_docs = stats["total"]["documents"]
    sep_bytes = n_docs * 15  # "\n<|endoftext|>\n" is 15 bytes
    by_id = {r["source_id"]: r for r in manifest}
    active = [s for s in sources if sources[s]["docs_read"]]

    out = []
    add = out.append
    add("# Data Card: Urdu BPE Corpus")
    add("")
    if note:
        add(f"> {note}")
        add("")
    if full:
        add(f"Generated {time.strftime('%Y-%m-%d')} by build_data_card.py. Sizes are decimal MB. "
            f"Files: train.txt, val.txt, test.txt (UTF-8, `<|endoftext|>` on its own line after every document, "
            f"98/1/1 split by document, seed {report['settings']['seed']}, split drawn separately inside each source).")
    else:
        add(f"train.txt, val.txt, test.txt: UTF-8, `<|endoftext|>` line after every document, 98/1/1 by "
            f"document within each source, seed {report['settings']['seed']}. Decimal MB. Normalisation "
            "and per-source detail: docs/DATA_CARD_full.md.")
    add("")
    add("## Sources")
    add("")
    add("| Source | Genre | Licence or terms | Collected | Raw MB | Cleaned MB |")
    add("|---|---|---|---|---:|---:|")
    for s in active:
        m = by_id.get(s, {})
        name = m.get("source_name", s) if full else SHORT_NAMES.get(s, m.get("source_name", s))
        url = m.get("url", "")
        licence = (m.get("license_or_terms", "") if full
                   else SHORT_LICENCES.get(s, m.get("license_or_terms", "")))
        add(f"| [{name}]({url}) | {sources[s]['genre']} | {licence} | "
            f"{m.get('collection_date_utc', '')} | {mb(sources[s]['raw_bytes'])} | "
            f"{mb(stats['per_source'][s]['bytes']) if s in stats['per_source'] else '0.00'} |")
    api = sum(sources[s]["raw_bytes"] for s in active
              if by_id.get(s, {}).get("collection_method") == "official API")
    add("")
    dump = sources.get("wikipedia_dump", {}).get("raw_bytes", 0)
    if full:
        add(f"Collected by us through the MediaWiki API: {mb(api)} MB (every page, with its link and checksum, in evidence/api_collected_files.csv). "
            + (f"Downloaded by us from the official Urdu Wikipedia XML dump of "
               f"{by_id.get('wikipedia_dump', {}).get('dump_date', '2026-10-01')}: {mb(dump)} MB of article text, "
               f"after skipping pages already collected through the API and setting aside articles under "
               f"1,000 bytes, which are mostly bot-generated stubs built from one template. "
               if dump else "")
            + "The rest is the published UFAL corpus.")
    else:
        add(f"Collected by us through the MediaWiki API: {mb(api)} MB (evidence/api_collected_files.csv). "
            + ("The dump excludes API pages and stubs under 1,000 bytes." if dump else ""))
    add("")
    add("## Corpus totals")
    add("")
    add("| Split | MB | Documents | Words | Unique words |")
    add("|---|---:|---:|---:|---:|")
    for split in ("train", "val", "test"):
        s = stats["splits"][split]
        add(f"| {split} | {s['mb']:,.2f} | {s['documents']:,} | {s['words']:,} | {s['unique_words']:,} |")
    t = stats["total"]
    add(f"| **all** | **{t['mb']:,.2f}** | **{t['documents']:,}** | **{t['words']:,}** | **{t['unique_words']:,}** |")
    add("")
    parts = []
    for s in active:
        p = stats["per_source"].get(s)
        if p:
            parts.append(f"{s} {pct(p['bytes'], t['bytes'])} ({p['docs']:,} documents, {p['words']:,} words, "
                         f"{p['unique_words']:,} unique)")
    dw = stats["document_words"]
    if not full:
        parts = [f"{s} {pct(stats['per_source'][s]['bytes'], t['bytes'])}"
                 for s in active if s in stats["per_source"]]
        add("A word is a run of letters, marks and digits.")
    else:
        add("By source: " + "; ".join(parts) + ". "
        f"A word is a run of letters, marks and digits. Median document {dw['median']:,} words "
        f"(10th to 90th percentile {dw['p10']:,} to {dw['p90']:,}). Words missing from train: "
        f"{pct(stats['oov_against_train']['val']['token_rate'], 1)} of val tokens, "
        f"{pct(stats['oov_against_train']['test']['token_rate'], 1)} of test tokens.")
    add("")
    add("## Cleaning steps")
    add("")
    add("| Step (in order) | Removed MB | Share of raw | Documents removed |")
    add("|---|---:|---:|---:|")
    raw = totals["raw_bytes"]
    for key, label in step_labels(report["settings"]).items():
        add(f"| {label} | {mb(removed[key])} | {pct(removed[key], raw)} | {docs_removed.get(key, 0):,} |")
    add(f"| Document separators added | +{mb(sep_bytes)} | | |")
    add(f"| **Raw {mb(raw)} MB to cleaned {t['mb']:,.2f} MB** | **{mb(raw - t['bytes'])}** | "
        f"**{pct(raw - t['bytes'], raw)}** | **{totals['docs_read'] - totals['docs_kept']:,}** |")
    add("")
    if full:
        add(f"{totals['docs_read']:,} documents read, {totals['docs_kept']:,} kept. UFAL has no documents, so it is "
            f"cut into groups of {report['settings']['chunk_lines']} lines.")
        add("")
    if not full:
        out.extend(gaps_compact(active, by_id, stats, report, t))
        return "\n".join(out)
    add("## Normalisation decisions")
    add("")
    digits_other = rules["arabic_indic_digits_to_ascii"] + rules["extended_indic_digits_to_ascii"]
    ascii_digits = report["ascii_digit_count"]
    example = "بین" + chr(0x200C) + "الاقوامی"
    add(f"- **Letters.** Arabic yeh and alef maksura to U+06CC ({rules['arabic_yeh_to_urdu_yeh']:,} found), "
        f"Arabic kaf to U+06A9 ({rules['arabic_kaf_to_urdu_kaf']:,}), Arabic heh to U+06C1 "
        f"({rules['arabic_heh_to_heh_goal']:,}); also teh marbuta, heh with yeh above and alef wasla. "
        f"U+06BE stays separate from U+06C1. Heh is not guessed to be do-chashmi from context, because "
        f"kahani and khana differ by that one letter.")
    add(f"- **Digits are ASCII.** {pct(ascii_digits, ascii_digits + digits_other)} of the raw digits were already "
        f"ASCII ({digits_other:,} Arabic-Indic or Urdu digits against {ascii_digits:,}). One convention means "
        f"the same number is never learned twice in two digit sets, and the tokenizer comparison uses ASCII numbers.")
    add(f"- **ZWNJ is kept only where it matters.** Urdu uses it inside compounds such as {example}. It changes "
        f"rendering only between a joining letter and a following letter, so it is kept there and dropped at word "
        f"edges, in runs and after non-joining letters ({stats.get('zwnj_in_corpus', 0):,} kept of "
        f"{rules['zwnj_seen']:,}). The tokenizer pattern must treat U+200C as part of a word.")
    add(f"- **Removed.** Tatweel ({rules['tatweel_removed']:,}), ZWJ, direction marks, BOM, ZWSP "
        f"({rules['invisible_removed']:,} invisible characters), honorific and Quranic signs "
        f"({rules['annotation_signs_removed']:,}). Zabar, zer, pesh and shadda are kept, composed to NFC, "
        f"repeats collapsed.")
    add(f"- **Spacing and typography.** In the raw text {report['spaced_full_stops']:,} of "
        f"{report['full_stops']:,} Urdu full stops ({pct(report['spaced_full_stops'], report['full_stops'])}) had a "
        f"space before them, almost all from UFAL, which is word-tokenised. Spaces before Urdu and ASCII "
        f"punctuation and inside brackets are closed so every source has one style. Curly quotes, dashes and the "
        f"ellipsis go to ASCII, Arabic presentation forms are folded with NFKC one character at a time, and runs "
        f"of spaces and blank lines are collapsed.")
    add("")
    add("## Known gaps and biases")
    add("")
    names = {s: by_id.get(s, {}).get("source_name", s) for s in active}
    big = max(active, key=lambda s: stats["per_source"].get(s, {}).get("bytes", 0))
    share = stats["per_source"][big]["bytes"] / t["bytes"]
    add(f"- **Genre balance.** {names[big]} is {pct(share, 1)} of the corpus, so the model mostly sees its "
        f"register." + (" Wikisource adds poetry and older literary prose, which is formal and archaic."
                        if "urwikisource" in active else ""))
    if "wikipedia_dump" in active:
        add("- **Age.** UFAL was released in 2014; the Wikipedia dump (October 2026) adds current topics and "
            "vocabulary, but only in encyclopedic register. Recent news, social media language and "
            "conversational Urdu are still thin. Roman Urdu is absent by design.")
    else:
        add("- **Age.** UFAL was released in 2014, so its topics and vocabulary stop there. Recent events, "
            "social media language and conversational Urdu are thin. Roman Urdu is absent by design.")
    add("- **Topics.** Wikipedia collection over-samples geography, biographies, lists and dates. An early "
        "sequential run gave near-templated asteroid articles; random sampling, repeated-line removal and "
        "near-duplicate removal reduce them but not entirely.")
    if "ufal" in active:
        coherent = sum(stats["per_source"].get(x, {}).get("bytes", 0) for x in active if x != "ufal")
        add(f"- **No document structure in UFAL.** It is one sentence per line, in shuffled order, so each of its "
            f"documents is a group of {report['settings']['chunk_lines']} unrelated sentences: plenty of Urdu, no "
            f"long-range context. Only the other sources ({pct(coherent, t['bytes'])} of the bytes) are real "
            f"articles. Because order is random, val and test do not share neighbouring text with train.")
    add("- **Language filter.** It separates Urdu from Persian, Arabic and Pashto but not from Shahmukhi Punjabi "
        "or Sindhi. The function-word check also drops name-only list and table pages (the 'list of ...' articles), which are Urdu but carry little prose.")
    add(f"- **Script mix and personal data.** {pct(stats['letter_share'].get('urdu_script', 0), 1)} of letters are "
        f"Urdu script, {pct(stats['letter_share'].get('latin', 0), 1)} Latin (code-mixing, names). Removed: "
        f"{report['scrubbed']['email']:,} e-mails, {report['scrubbed']['phone']:,} phone or ID numbers, "
        f"{report['scrubbed']['handle']:,} handles, {report['scrubbed']['url']:,} links.")
    add("- **Rights.** UFAL is CC BY-NC-SA 3.0 and Wikipedia is CC BY-SA 4.0, so the text stays inside the "
        "course and is not redistributed. Each Wikisource work needs its own rights check.")
    add("")
    return "\n".join(out)


def gaps_compact(active, by_id, stats, report, t):
    """Known gaps and biases in one line each, for the one-page card."""
    big = max(active, key=lambda s: stats["per_source"].get(s, {}).get("bytes", 0))
    name = by_id.get(big, {}).get("source_name", big)
    share = stats["per_source"][big]["bytes"] / t["bytes"]
    coherent = sum(stats["per_source"].get(x, {}).get("bytes", 0) for x in active if x != "ufal")
    lines = ["## Known gaps and biases", "",
             f"- **Genre and age.** {name} (2014) is {pct(share, 1)} of the bytes and Wikipedia most of "
             "the rest, so news, social media and conversational Urdu are thin; Roman Urdu is absent by design."]
    if "ufal" in active:
        lines.append(f"- **No structure in UFAL.** Its sentences are shuffled, so its documents are groups of "
                     f"{report['settings']['chunk_lines']} unrelated sentences; only "
                     f"{pct(coherent, t['bytes'])} of the bytes are real articles.")
    lines += ["- **Filters.** Wikipedia over-samples geography and biographies; the language filter does "
              "not separate Urdu from Shahmukhi Punjabi or Sindhi.",
              f"- **Personal data and rights.** Removed {report['scrubbed']['email']:,} e-mails, "
              f"{report['scrubbed']['phone']:,} phone or ID numbers, {report['scrubbed']['handle']:,} handles "
              f"and {report['scrubbed']['url']:,} links. UFAL is CC BY-NC-SA 3.0 and Wikipedia CC BY-SA "
              "4.0, so the text stays inside the course.", ""]
    return lines


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=ROOT / "source_manifest.csv")
    ap.add_argument("--report", type=Path, default=ROOT / "reports" / "cleaning_report.json")
    ap.add_argument("--stats", type=Path, default=ROOT / "reports" / "corpus_stats.json")
    ap.add_argument("--out", type=Path, default=ROOT / "DATA_CARD.md")
    ap.add_argument("--full-out", type=Path, default=ROOT / "docs" / "DATA_CARD_full.md",
                    help="the longer card with per-source detail and normalisation decisions")
    ap.add_argument("--note", default="", help="one line printed under the title (for provisional cards)")
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)
    report = json.loads(args.report.read_text(encoding="utf-8"))
    stats = json.loads(args.stats.read_text(encoding="utf-8"))
    card = build(manifest, report, stats, args.note, full=False)
    args.out.write_text(card, encoding="utf-8", newline="\n")
    args.full_out.parent.mkdir(parents=True, exist_ok=True)
    args.full_out.write_text(build(manifest, report, stats, args.note, full=True),
                             encoding="utf-8", newline="\n")
    cleaned = {s: v["mb"] for s, v in stats["per_source"].items()}
    save_manifest(args.manifest, manifest, cleaned)
    print(f"Wrote {args.out} ({len(card.splitlines())} lines) and updated cleaned_mb in {args.manifest.name}")


if __name__ == "__main__":
    main()
