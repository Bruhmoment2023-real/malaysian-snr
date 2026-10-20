# Does the Malaysian SnR method find better entries than chance? A codified test on crypto, gold and silver against matched random entries

**Sean Solano Paul**, Independent researcher, Bengaluru, India. Funding: none. Competing interests: none.

## Summary

Malaysian SnR (MSNR) is a support-and-resistance method taught on social media in which levels are drawn from candle closes and a level is said to work best while it is "fresh". This repository contains the written-down rule specification, the audit of the study, the scripts that reproduce the headline tables and figures from the study's saved outputs, robustness and look-ahead checks, the multiple-testing sensitivity analysis, and a bibliometric map of the literature. In the paper, out of sample the simple method lost 0.547 R per trade after costs over 50,108 trades and, before costs, did no better than random entries (-0.058 R against -0.060 R, z = 0.26); a fuller top-down version lost 0.511 R per trade over 8,125 walk-forward trades; and a search over 116,708 variants found no configuration with at least 100 trades that survived false-discovery control.

## Repository layout

| Path | Contents |
|---|---|
| `03-rule-spec.md` | The method written as machine-followable rules |
| `02-audit.md` | Referee-style audit of the study (what each phase is, headline checks) |
| `01-prior-work.md` | Prior-work review |
| `code/` | Six scripts that rebuild the headline tables and figures: `01_reproduce_headlines.py`, `02_intrabar_resolution_check.py`, `03_histdata_clock_check.py`, `04_figures_and_tables.py`, `05_dsr_sensitivity.py`, `06_truncation_lookahead_test.py` |
| `results/` | Tables 1-7, figures 1-8, robustness and sensitivity CSVs, reproduction check and logs, compact parquet files of configurations and canonical trades |
| `followup/lookahead/` | Truncation (look-ahead) tests, limit-entry leak analysis, code copies used, logs |
| `followup/rerun/` | Independent re-run of the six scripts with byte-for-byte comparison (`followup/rerun-report.md`, `compare_outputs.csv`) |
| `followup/sources/` | Scripts, URL table, rule-to-source map (`rules_map.md`), checksums and notes for the public pages the rules were drawn from (page copies not included) |
| `bibliometrics/` | Literature map: search protocol, corpus, tables, figures, VOSviewer files, R and Python scripts (see `bibliometrics/README.md`) |
| `depth/` | BibTeX/RIS, data dictionary, rerun script |
| `requirements.txt` | Pinned Python packages |

## How to reproduce

Python 3.12.10. Install:

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # Windows; use .venv/bin/python elsewhere
```

The six scripts in `code/` read the study's own backtest outputs and price data, which are large and not part of this repository (see below). They expect them in the folder set by the `SRC` constant near the top of each script (originally `D:/Malaysian-SNR`) and write to the folder set by `OUT` (originally `D:/Research-Publishing/02-malaysian-snr/results`). To rerun: obtain the inputs, edit `SRC` and `OUT`, then run in order:

```
python code/01_reproduce_headlines.py
python code/02_intrabar_resolution_check.py        # set NUMBA_CACHE_DIR to a local folder first
python code/03_histdata_clock_check.py
python code/04_figures_and_tables.py
python code/05_dsr_sensitivity.py
python code/06_truncation_lookahead_test.py
```

Total runtime was about 86 s on a laptop; `followup/rerun-report.md` reports all six scripts reproducing the stored tables byte for byte. The tables and figures already in `results/` are the verified outputs. `depth/appendix/rerun.ps1` shows the original PowerShell driver.

## Data sources and licences

| Data | Source | Terms |
|---|---|---|
| Crypto bars (BTC, ETH, SOL; 5m to 1d) | Public exchange data downloaded by the study's own backtest code | **Not included**; exchange terms apply |
| Gold and silver bars (and gold-token series) | HistData.com and public sources | **Not included**; vendor terms apply |
| MSNR rule descriptions | Public TradingView scripts, guides and videos listed in `followup/sources/url_table.md` | Page copies **not included**; only the URL table and short rule-to-source mapping |
| Literature metadata | OpenAlex (CC0), Crossref, arXiv, Semantic Scholar API | Open metadata |
| Derived results, tables, figures | This work | CC BY 4.0 (`LICENSE-DATA.md`) |
| Code | This work | MIT (`LICENSE`) |

Third-party email addresses that appeared in copied abstracts were replaced by `[email-redacted]`.

## Not included and why

- Abstract text of third-party papers (the `abstract`/`AB` columns and abstract-derived quote columns of the bibliographic tables, and abstract fields in the OpenAlex JSON). Identifiers, titles, years, venues, keywords and citation data are kept; re-fetch abstracts with the bibliometrics pipeline if needed.
- Per-paper reading notes on the literature (they contain quotations from copyrighted papers) and the literature gap-analysis note (scoping). The scripts that built the notes are kept; run them on your own copies of the papers.
- Raw price bars and the study's backtest/search outputs (phases 1-3 of the original study, including the 116,708-variant search tables): vendor-licensed data and very large; the scripts in `code/` read them from `SRC`. The compact derived parquet files in `results/` are included.
- `followup/sources/snapshots/`: saved copies of third-party web pages and transcripts (copyrighted). Re-create with `followup/sources/archive_sources.py` from `url_table.md`.
- `followup/raw/` and `followup/novelty*`: fetched search-result pages and literature-novelty search working files.
- `depth/raw/`, `bibliometrics/pdfs/`: full-text copies of third-party papers; obtain via the DOIs in `depth/citations/references.bib`.
- Numba caches and other generated caches, virtual environments, credentials (none present).

## Citation

Solano Paul, S. (2026). *Does the Malaysian SnR method find better entries than chance? A codified test on crypto, gold and silver against matched random entries* [Research code and data]. https://github.com/Bruhmoment2023-real/malaysian-snr (Zenodo DOI to be added).

A machine-readable record is in `CITATION.cff`.
