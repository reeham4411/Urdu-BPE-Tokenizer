# DATA CARD — Urdu BPE Corpus

## Sources

The Urdu corpus was collected from three sources covering encyclopedic, literary, and mixed-domain text.

| Source          | Genre        | Raw Size          | Cleaned Size |
| --------------- | ------------ | ----------------- | ------------ |
| Urdu Wikipedia  | Encyclopedia | 4.21 MB (interim) | Pending      |
| Urdu Wikisource | Literature   | 2.03 MB (interim) | Pending      |
| UFAL UrMonoCorp | Mixed-domain | 717.41 MB         | Pending      |

**Source details**

- **Urdu Wikipedia:** https://ur.wikipedia.org/ — Collected independently using the MediaWiki API. Verify the applicable CC BY-SA licensing and attribution requirements.
- **Urdu Wikisource:** https://ur.wikisource.org/ — Collected independently through the MediaWiki API. Individual works require copyright and licensing verification.
- **UFAL UrMonoCorp:** https://ufal.mff.cuni.cz/node/998 — Downloaded as a published Urdu corpus. Verify and record the repository's exact terms of use.

Collection dates and final size measurements will be recorded from `source_manifest.csv`.

## Known Gaps and Biases

The corpus combines encyclopedic articles, literary texts, and mixed-domain Urdu. However, the sources introduce several potential biases.

Urdu Wikipedia includes many short, similarly structured articles, particularly about astronomical objects, geographic locations, and biographies. Although random sampling was introduced to improve topic diversity, repeated article patterns may remain.

Urdu Wikisource contains literary prose and poetry, which may overrepresent formal or historical Urdu compared with everyday conversation. UFAL contains material from multiple domains, but its older collection may not fully reflect current vocabulary and language usage.

The corpus may underrepresent Roman Urdu, informal conversations, regional expressions, and modern Urdu-English code-mixing. Some collected texts also contain markup, repeated boilerplate, inconsistent spacing, or Unicode variations that require cleaning.

The final genre distribution and any remaining limitations will be reassessed after cleaning and deduplication.
