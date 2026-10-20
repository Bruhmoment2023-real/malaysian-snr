# Literature map (bibliometrics) - 02-malaysian-snr

Data-driven map of the literature around: *A multiple-testing-controlled test of a social-media support/resistance trading method (Malaysian SnR) in gold, silver and crypto*

- **Corpus size:** 1360 records (Technical analysis and trading-rule profitability: 1044; Support and resistance, price levels and order clustering: 191; Data snooping, multiple testing and backtest overfitting in finance: 121; seed: 4)
- **Date of pull:** 2026-10-13
- **Sources:** discovery in Crossref, Semantic Scholar, ERIC and arXiv; metadata from OpenAlex; forward citations from OpenCitations. No Scopus/WoS data (EMPTY - no Scopus/WoS export to merge; corpus is OpenAlex-only).
- **Made by:** an AI agent (Claude). It contains data, figures, tables and bullet-point analysis only - no manuscript prose.

## What is here

| Path | Contents |
|---|---|
| `search-protocol.md` | exact search strings, databases, inclusion/exclusion rules, PRISMA-style counts, coverage checks |
| `scopus-queries.md` | ready-to-paste Scopus and Web of Science advanced-search strings (not run: no login) |
| `gap-analysis.md` | what the map shows: dense and thin areas, where Sean's question sits, five papers to read first |
| `evidence-table.csv` | the most relevant papers with study type, setting, data, method, one-line finding (from the abstract), relation to this paper |
| `config.json` | every setting of the run: queries, rules, seeds, hand-screen exclusions |
| `data\raw\` | raw API responses per query (`crossref\`, `s2\`, `eric\`, `arxiv\`), all query hits (`all_hits.csv`), query log, raw OpenAlex records (`openalex\*.jsonl.gz`) |
| `data\clean\` | `master.csv` / `master.rds` (one row per corpus record), `bibliometrix_input.csv` / `bibliometrix_M.rds` (bibliometrix data frame), `citation_edges.csv`, `cited_references.csv`, screening logs, unresolved candidates |
| `figures\` | 48 figures (PNG at 220 dpi, SVG copies, interactive HTML) and `captions.md` |
| `tables\` | 57 CSV tables (every figure's numbers, PRISMA counts, clusters, logs) |
| `vosviewer\` | map + network files for VOSviewer (co-citation, co-authorship, keyword co-occurrence, bibliographic coupling, direct citation) and VOSviewer-computed layouts |
| `pdfs\` | 14 legally open-access PDFs of core papers and `download_log.csv` |
| `R\`, `python\` | the scripts that made everything |
| `scopus-drop\` | empty; put Scopus/WoS exports here |

## How to regenerate everything (PowerShell)

```powershell
$py = 'D:\Research-Publishing\_tools\biblio-venv\Scripts\python.exe'
$b  = 'D:\Research-Publishing\02-malaysian-snr\bibliometrics'
& $py "$b\python\pipeline.py" $b search enrich snowball refs master   # network; every response is cached in D:\Research-Publishing\_tools\biblio-cache
$env:R_LIBS_USER = 'D:\Research-Publishing\_tools\R-lib;C:\Users\seans\AppData\Local\R\win-library\4.5'   # this shell only
& 'C:\Program Files\R\R-4.5.3\bin\Rscript.exe' "$b\R\bibliometrix_analysis.R" $b                # tables + R figures + VOSviewer files
& $py "$b\python\figures.py" $b        # Python figures, VOSviewer layouts, captions.md
& $py "$b\python\pdfs.py" $b download  # open-access PDFs of the core papers
& $py "$b\python\pdfs.py" $b evidence  # rebuild evidence-table.csv from data\clean\evidence_notes.json
& $py "$b\python\docs.py" $b           # this README and search-protocol.md
```
Re-running `search` on a later date re-uses cached responses; delete the cache file to force a fresh pull. To hand-exclude a record, add its OpenAlex id and a reason under `manual_exclude` in `config.json` and re-run `master` onward.

## Analysis log

R / bibliometrix: 27 of 27 analyses completed.

Python figures:
- prisma: ok
- year_sub: ok
- timeline: ok
- db: ok
- geography: ok
- heatmap: ok
- citation_network: ok
- main_path: ok
- cocitation: ok
- vosviewer_cli: not run

## Limits (read before using any figure)

- Discovery ran through Crossref, Semantic Scholar, ERIC and arXiv, not through an OpenAlex or Scopus topic search (see search-protocol.md section 1). Recall is unknown; the corpus is a map of the indexed literature, not a census.
- OpenAlex is broader but noisier than Scopus: it includes low-quality and predatory outlets, working-paper duplicates and occasional wrong metadata. Screening was by rules plus one AI hand pass over titles.
- OpenAlex is weak on Indian journals and books (missing abstracts, affiliations and reference lists) and on law. Country and collaboration figures only describe the records that carry affiliation data.
- Keywords are OpenAlex's machine-assigned keywords, not author keywords. Thematic maps and co-occurrence networks inherit OpenAlex's vocabulary.
- Citation links exist only where the publisher deposited a reference list. Books, reports, working papers and most law reviews appear isolated even when they are heavily used.
- Citation counts are as of the pull date and favour older papers and English-language journals.
- Evidence-table findings are taken from abstracts unless a row says 'full text read'. Check the paper before citing it.
- Several papers named in 01-prior-work.md are 2026 SSRN working papers; the corpus includes them only where Crossref/OpenAlex index them.

## Paper-02-specific notes (read with the section above)
- Hand screen: the first screen left 1,697 records, many from other fields ("ICT" = information technology, genomics "false discovery rate", engineering "anomaly detection/data mining"); 337 were removed by rule (`python\handscreen_p02.py`; every id and reason in `tables\hand_screen_removed.csv`), with the White (2000), Romano-Wolf (2005) and Benjamini-Hochberg (1995) classics protected by id. The final corpus has 1,360 records.
- Refs: 33,158 distinct cited works, 22,000 attempted, 7,677 resolved (OpenAlex single-record lookups were slow). Co-citation figures are built on those.
- Not produced: VOSviewer command-line layouts (the program hung for about 30 minutes per run on a loaded laptop); the VOSviewer-ready map and network files are in `vosviewer\`. The R steps were run once end to end (27 of 27 completed; historiograph needed a patch for empty reference fields); `R\run_kit.log` is the log.
- PDFs: 12 downloaded through the kit plus 2 arXiv papers fetched by hand (`pdfs\download_note.txt`); Sullivan et al. (1999) saved but unreadable (image-based).
- Depth additions: Kleinberg bursts (`figures\py_burst_keywords.png`, `tables\py_burst_keywords.csv`), main path (`figures\py_06_main_path.png`, `tables\py_main_path_documents.csv`).
- Evidence rows: 45 "abstract read", 8 "metadata only" (`python\evidence_notes_p02.py`).
