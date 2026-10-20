"""Write search-protocol.md and README.md for one paper from the logged data (no hand-typed numbers).
Usage: python docs.py <bibliometrics_dir>
"""
import os, sys, json, collections
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

B = os.path.abspath(sys.argv[1])
cfg = C.jload(os.path.join(B, "config.json"))
T = lambda *a: os.path.join(B, *a)
rd = lambda p, **k: pd.read_csv(p, encoding="utf-8-sig", keep_default_na=False, **k) if os.path.exists(p) and os.path.getsize(p) > 5 else pd.DataFrame()
ql = rd(T("data", "raw", "query_log.csv"))
pr = rd(T("tables", "prisma_counts.csv"))
cov = rd(T("tables", "coverage_crosscheck.csv"))
M = rd(T("data", "clean", "master.csv"))
hs = rd(T("tables", "hand_screen_removed.csv"))
pw = rd(T("tables", "prior_work_coverage.csv"))
rlog = rd(T("tables", "R_analysis_log.csv"))
pylog = C.jload(T("tables", "py_figure_log.json"), {})
api = C.jload(T("data", "api_log.json"), [])
drop = rd(T("tables", "R_scopus_drop_status.csv"))
unres = rd(T("data", "clean", "unresolved_candidates.csv"))
p1 = C.jload(T("data", "clean", "prisma_search.json"), {})
p2 = C.jload(T("data", "clean", "prisma_snowball.json"), {})
rs = C.jload(T("data", "clean", "refs_stats.json"), {})
date = p1.get("date", "")
DBN = {"crossref": "Crossref REST API (api.crossref.org/works, query.bibliographic, relevance-ranked)", "s2": "Semantic Scholar Graph API (paper/search/bulk, boolean query on title+abstract, sorted by citation count)",
       "eric": "ERIC API (api.ies.ed.gov/eric)", "arxiv": "arXiv API (export.arxiv.org/api/query)", "openalex": "OpenAlex /works?search= (keyless)", "seed": "Seed titles (verified against Crossref)"}


def md_table(df):
    if df.empty:
        return "_none_\n"
    s = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    for r in df.itertuples(index=False):
        s += "| " + " | ".join(str(x).replace("|", "\\|").replace("\n", " ") for x in r) + " |\n"
    return s


o = []
o.append(f"# Search protocol - {cfg['paper_id']}\n")
o.append(f"- Paper question: {cfg['paper_title']}\n- Date of search and data pull: **{date}**\n- Years covered: {cfg['year_min']}-{cfg['year_max']}; language: English (OpenAlex language field `en` or missing)\n"
         f"- Built by an AI agent (Claude) with the scripts in `python\\` and `R\\`; all numbers below are read from the run logs.\n")
o.append("## 1. Databases\n")
o.append("| Role | Database | Access | Note |\n|---|---|---|---|\n"
         "| Discovery | Crossref REST API | free, no key, `mailto` polite pool | relevance-ranked keyword search; top N per query |\n"
         "| Discovery | Semantic Scholar Graph API (bulk search) | free, no key | boolean search on title/abstract; top N by citations per query |\n"
         "| Discovery | ERIC API | free, no key | education topics only |\n"
         "| Discovery | arXiv API | free, no key | preprints |\n"
         "| Enrichment (authors, institutions, countries, topics, keywords, abstracts, references, citation counts, OA links) | **OpenAlex** single-record lookups (`/works/doi:...`, `/works/mag:...`, `/works/W...`) | free, no key | see limit 1 below |\n"
         "| Forward citations for snowballing | OpenCitations Index API v2 | free, no key | DOI-to-DOI citations only |\n"
         "| Cross-check | Crossref (per-DOI), Semantic Scholar (batch) | free, no key | citation counts and reference-list coverage compared in `tables\\coverage_crosscheck.csv` |\n"
         "| Not used | Scopus, Web of Science, Lens, Dimensions | need accounts | equivalent strings are in `scopus-queries.md` |\n"
         "| Not usable | RePEc/IDEAS | its API needs a registered access code; the public search page returned no parseable result list to a script | economics working papers still enter via Crossref, Semantic Scholar and snowballing |\n")
o.append("**Why OpenAlex was not the search engine.** Since 2026 OpenAlex charges keyless list/search calls against a small daily budget shared by everyone on the same IP address ($0.10/day). "
         "On the day of the pull that budget was already exhausted by other work on this network, and an API key needs an account (ruled out). Single-record lookups remain free and unlimited, so records were "
         "*discovered* in Crossref / Semantic Scholar / ERIC / arXiv and then *enriched* one by one from OpenAlex. Consequence: a work that is in OpenAlex but not found by any of the four discovery databases is missed, except where snowballing caught it.\n")
o.append("## 2. Exact search strings\n")
for sk, sl in cfg["sublits"].items():
    o.append(f"### {sk}: {sl['label']}\n")
    q = ql[ql.sublit == sk] if len(ql) else pd.DataFrame()
    if len(q):
        o.append(md_table(q[["db", "query", "total_in_db", "retrieved", "status"]].rename(columns={"db": "database", "total_in_db": "hits in database", "retrieved": "records retrieved"})))
o.append("Per-query retrieval caps: " + ", ".join(f"{k} = {v}" for k, v in cfg.get("n_per_query", {}).items()) +
         ". Crossref totals are large because its search is an OR-type relevance ranking; only the top-ranked records were taken. Raw responses for every query are in `data\\raw\\<database>\\`.\n")
sd = ql[ql.db == "seed"] if len(ql) else pd.DataFrame()
if len(sd):
    o.append("### Seed papers (known key works, each verified to exist by a Crossref title match; they bypass the keyword rules)\n")
    o.append(md_table(sd[["query", "status"]].rename(columns={"query": "seed title", "status": "result"})))
if cfg.get("seed_arxiv"):
    o.append("Seed arXiv ids (from the PDFs the substance agent saved in the paper folder): " + ", ".join(cfg["seed_arxiv"]) + "\n")
o.append("## 3. Inclusion and exclusion rules (applied identically to search hits and snowballed records)\n")
o.append("A record is **included** if all of the following hold:\n"
         "1. It resolves to an OpenAlex work record (by DOI, MAG id, or a Crossref title match of at least 93% similarity).\n"
         "2. OpenAlex type is article, review, preprint, book chapter, book, dissertation, report or other (editorials, errata, paratext, datasets, peer reviews are dropped).\n"
         f"3. Publication year {cfg['year_min']}-{cfg['year_max']}; language English or unrecorded.\n"
         "4. It satisfies at least one sub-literature rule below: every `include` pattern must match in title + abstract, and every `title_must` pattern must match in the title.\n"
         "5. Its title does not match the exclusion pattern.\n"
         + (f"6. Citation floor: records older than {cfg['min_citations_if_older_than'][0]} years need at least {cfg['min_citations_if_older_than'][1]} citation(s).\n" if cfg.get("min_citations_if_older_than") else "")
         + "\nBook-series and proceedings trap: a record whose abstract is a series/proceedings blurb (detected by wording such as 'this volume constitutes the refereed proceedings', or the same abstract shared by 3+ records) "
         "is screened on its title alone; whole-volume records (titles starting 'Proceedings of', 'Front matter', etc.) are dropped.\n\n"
         "The patterns are case-insensitive regular expressions (`\\b` = word boundary, `\\w*` = any word ending, `.{0,80}` = within 80 characters).\n")
for sk, sl in cfg["sublits"].items():
    o.append(f"**{sk} - {sl['label']}**\n")
    for g in sl["include"]:
        o.append(f"- include (title+abstract): `{g}`")
    for g in sl.get("title_must", []):
        o.append(f"- title_must (title): `{g}`")
    o.append("")
o.append(f"**Exclusion pattern (title):** `{cfg.get('exclude', '')}`\n")
o.append("A record matching several rules is assigned to the first one in the order listed (its other matches are kept in `sublits_all`).\n")
o.append("## 4. Snowballing (one round)\n")
o.append(f"- Central papers: the {p2.get('central_papers')} corpus records ranked highest on local citations + topical relevance + log(global citations) - listed in `data\\clean\\snowball_central_papers.csv`.\n"
         f"- Backward: every OpenAlex `referenced_works` entry of those papers not already in the corpus ({p2.get('backward_candidates')} candidates).\n"
         f"- Forward: citing DOIs from OpenCitations, up to {cfg.get('snowball_max_forward')} per central paper ({p2.get('forward_candidates')} candidates). OpenCitations only knows DOI-to-DOI links, so citing preprints and books without DOIs are missed.\n"
         f"- All candidates were looked up in OpenAlex and screened with the rules in section 3: {p2.get('backward_included')} backward and {p2.get('forward_included')} forward records were added.\n")
o.append("## 5. PRISMA-style counts\n")
o.append(md_table(pr))
o.append("Figure: `figures\\py_01_prisma_flow.png`.\n")
o.append("## 6. Hand-screening\n")
o.append(f"After rule screening and snowballing, the agent read the titles (with source and year) of the whole corpus and removed {len(hs)} records as off-topic or mis-matched; every removal and its reason is in `tables\\hand_screen_removed.csv`. "
         "This is a single-screener pass by an AI agent on titles, not a two-person human screen; borderline records were kept.\n")
if len(hs):
    rc = collections.Counter(hs.reason)
    o.append("Removal reasons:\n" + "\n".join(f"- {k}: {v}" for k, v in rc.most_common()) + "\n")
o.append("## 7. Coverage and cross-checks\n")
o.append(md_table(cov))
if len(unres):
    o.append(f"\n- {len(unres)} title-screened candidates could not be matched to any OpenAlex record (no DOI or MAG id, or not indexed) and are **not** in the corpus. They are listed in `data\\clean\\unresolved_candidates.csv` "
             f"({', '.join(f'{k}: {v}' for k, v in collections.Counter(d for s in unres.dbs for d in s.split(';')).most_common())}). ERIC reports and theses and Indian or legal journal articles without DOIs dominate this list.\n")
o.append(f"- Cited references: {rs.get('distinct_cited_works')} distinct works are cited by the corpus ({rs.get('total_reference_links')} links); {rs.get('resolved')} of the {rs.get('attempted')} outside the corpus were resolved to metadata for the co-citation and RPYS analyses.\n")
if len(pw):
    o.append("\n### Named prior work (seed list / the substance agent's saved papers) - is it in the corpus?\n")
    o.append(md_table(pw))
else:
    o.append("\n- No `prior-work.md`-type file existed in the paper folder when this was built, so there was no named list to check against (other than the seeds above).\n")
fails = [a for a in api if a.get("status") not in (200,)]
o.append("## 8. API failures during the run\n")
if fails:
    fc = collections.Counter((a["host"], a["note"][:70]) for a in fails)
    o.append("\n".join(f"- {h}: {n} (x{c})" for (h, n), c in fc.most_common(15)) + "\n")
else:
    o.append("- None logged beyond normal 'not found' (404) lookups.\n")
if len(drop):
    o.append(f"\n## 9. Scopus / Web of Science exports\n- `scopus-drop\\`: {drop.status.iloc[0]}.\n- Ready-to-paste strings: `scopus-queries.md`.\n")
open(T("search-protocol.md"), "w", encoding="utf-8").write("\n".join(o))

# ------------------------------------------------------------------ README
figs = sorted(f for f in os.listdir(T("figures")) if f.lower().endswith((".png", ".html"))) if os.path.exists(T("figures")) else []
tabs = sorted(os.listdir(T("tables"))) if os.path.exists(T("tables")) else []
pdfs = [f for f in os.listdir(T("pdfs")) if f.lower().endswith(".pdf")] if os.path.exists(T("pdfs")) else []
r = []
r.append(f"# Literature map (bibliometrics) - {cfg['paper_id']}\n")
r.append(f"Data-driven map of the literature around: *{cfg['paper_title']}*\n")
r.append(f"- **Corpus size:** {len(M)} records" + (" (" + "; ".join(f"{cfg['sublits'].get(k, {}).get('label', k)}: {v}" for k, v in M.sublit.value_counts().items()) + ")" if len(M) else "") +
         f"\n- **Date of pull:** {date}\n- **Sources:** discovery in Crossref, Semantic Scholar, ERIC and arXiv; metadata from OpenAlex; forward citations from OpenCitations. No Scopus/WoS data ({drop.status.iloc[0] if len(drop) else 'scopus-drop not checked'}).\n"
         "- **Made by:** an AI agent (Claude). It contains data, figures, tables and bullet-point analysis only - no manuscript prose.\n")
r.append("## What is here\n")
r.append("| Path | Contents |\n|---|---|\n"
         "| `search-protocol.md` | exact search strings, databases, inclusion/exclusion rules, PRISMA-style counts, coverage checks |\n"
         "| `scopus-queries.md` | ready-to-paste Scopus and Web of Science advanced-search strings (not run: no login) |\n"
         "| `gap-analysis.md` | what the map shows: dense and thin areas, where Sean's question sits, five papers to read first |\n"
         f"| `evidence-table.csv` | the most relevant papers with study type, setting, data, method, one-line finding (from the abstract), relation to this paper |\n"
         "| `config.json` | every setting of the run: queries, rules, seeds, hand-screen exclusions |\n"
         "| `data\\raw\\` | raw API responses per query (`crossref\\`, `s2\\`, `eric\\`, `arxiv\\`), all query hits (`all_hits.csv`), query log, raw OpenAlex records (`openalex\\*.jsonl.gz`) |\n"
         "| `data\\clean\\` | `master.csv` / `master.rds` (one row per corpus record), `bibliometrix_input.csv` / `bibliometrix_M.rds` (bibliometrix data frame), `citation_edges.csv`, `cited_references.csv`, screening logs, unresolved candidates |\n"
         f"| `figures\\` | {len(figs)} figures (PNG at 220 dpi, SVG copies, interactive HTML) and `captions.md` |\n"
         f"| `tables\\` | {len(tabs)} CSV tables (every figure's numbers, PRISMA counts, clusters, logs) |\n"
         "| `vosviewer\\` | map + network files for VOSviewer (co-citation, co-authorship, keyword co-occurrence, bibliographic coupling, direct citation) and VOSviewer-computed layouts |\n"
         f"| `pdfs\\` | {len(pdfs)} legally open-access PDFs of core papers and `download_log.csv` |\n"
         "| `R\\`, `python\\` | the scripts that made everything |\n"
         "| `scopus-drop\\` | empty; put Scopus/WoS exports here |\n")
r.append("## How to regenerate everything (PowerShell)\n")
r.append("```powershell\n$py = 'D:\\Research-Publishing\\_tools\\biblio-venv\\Scripts\\python.exe'\n$b  = '" + B + "'\n"
         "& $py \"$b\\python\\pipeline.py\" $b search enrich snowball refs master   # network; every response is cached in D:\\Research-Publishing\\_tools\\biblio-cache\n"
         "$env:R_LIBS_USER = 'D:\\Research-Publishing\\_tools\\R-lib;C:\\Users\\seans\\AppData\\Local\\R\\win-library\\4.5'   # this shell only\n"
         "& 'C:\\Program Files\\R\\R-4.5.3\\bin\\Rscript.exe' \"$b\\R\\bibliometrix_analysis.R\" $b                # tables + R figures + VOSviewer files\n"
         "& $py \"$b\\python\\figures.py\" $b        # Python figures, VOSviewer layouts, captions.md\n"
         "& $py \"$b\\python\\pdfs.py\" $b download  # open-access PDFs of the core papers\n"
         "& $py \"$b\\python\\pdfs.py\" $b evidence  # rebuild evidence-table.csv from data\\clean\\evidence_notes.json\n"
         "& $py \"$b\\python\\docs.py\" $b           # this README and search-protocol.md\n```\n"
         "Re-running `search` on a later date re-uses cached responses; delete the cache file to force a fresh pull. To hand-exclude a record, add its OpenAlex id and a reason under `manual_exclude` in `config.json` and re-run `master` onward.\n")
r.append("## Analysis log\n")
if len(rlog):
    r.append(f"R / bibliometrix: {int((rlog.status == 'ok').sum())} of {len(rlog)} analyses completed.\n")
    bad = rlog[rlog.status != "ok"]
    if len(bad):
        r.append("Not produced:\n" + "\n".join(f"- {a.analysis}: {a.status}" for a in bad.itertuples()) + "\n")
if pylog:
    r.append("Python figures:\n" + "\n".join(f"- {k}: {v}" for k, v in pylog.items()) + "\n")
r.append("## Limits (read before using any figure)\n")
lim = [
    "Discovery ran through Crossref, Semantic Scholar, ERIC and arXiv, not through an OpenAlex or Scopus topic search (see search-protocol.md section 1). Recall is unknown; the corpus is a map of the indexed literature, not a census.",
    "OpenAlex is broader but noisier than Scopus: it includes low-quality and predatory outlets, working-paper duplicates and occasional wrong metadata. Screening was by rules plus one AI hand pass over titles.",
    "OpenAlex is weak on Indian journals and books (missing abstracts, affiliations and reference lists) and on law. Country and collaboration figures only describe the records that carry affiliation data.",
    "Keywords are OpenAlex's machine-assigned keywords, not author keywords. Thematic maps and co-occurrence networks inherit OpenAlex's vocabulary.",
    "Citation links exist only where the publisher deposited a reference list. Books, reports, working papers and most law reviews appear isolated even when they are heavily used.",
    "Citation counts are as of the pull date and favour older papers and English-language journals.",
    "Evidence-table findings are taken from abstracts unless a row says 'full text read'. Check the paper before citing it.",
]
r.append("\n".join(f"- {x}" for x in lim + cfg.get("readme_limits", [])) + "\n")
open(T("README.md"), "w", encoding="utf-8").write("\n".join(r))
print("docs written:", T("search-protocol.md"), T("README.md"))
