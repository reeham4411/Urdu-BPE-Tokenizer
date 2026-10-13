# Evidence of the text we collected ourselves

`api_collected_files.csv` lists every page collected through the MediaWiki API: 8,469 pages, 57.04 MB (urwiki 7,959 pages, 55.01 MB; urwikisource 510 pages, 2.03 MB). Each row has the page ID, a link that opens the page on Wikipedia or Wikisource (`?curid=<page ID>`), the size, the SHA-256 of the saved text and the file time.

This list was rebuilt on 2026-10-13 from the saved page files, not written during collection. The collection scripts write the original per-request logs (URL, title, revision ID and UTC time of each request) to `evidence/logs/`; those stayed on the computer that ran the collection and should be copied here before submission.

Two files in the downloaded `urwiki` folder, `713002(1).txt` and `713326(1).txt`, are duplicate copies made by the Google Drive download. They are identical to the originals, are not listed here, and were removed by the exact-duplicate step of `clean_corpus.py`.
