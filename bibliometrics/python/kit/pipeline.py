"""Literature-map data pipeline (search -> enrich/screen -> snowball -> refs -> master).

Usage:  python pipeline.py <bibliometrics_dir> <stage> [<stage> ...]
        stages: search enrich snowball refs master   (or: all)

Reads <bibliometrics_dir>/config.json. Writes only inside <bibliometrics_dir>.
Discovery: Crossref, Semantic Scholar (bulk search), ERIC, arXiv (+ OpenAlex search if the keyless
daily budget allows). Enrichment: OpenAlex single-record lookups (free). Forward citations: OpenCitations.
"""
import csv, glob, json, math, os, re, sys, time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from urllib.parse import quote
import pandas as pd
from rapidfuzz import fuzz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

TODAY = time.strftime("%Y-%m-%d")
KEEP_TYPES = {"article", "review", "preprint", "book-chapter", "book", "dissertation", "report", "other"}
CONTAINER_RE = re.compile(r"^\s*(proceedings of|front ?matter|back ?matter|table of contents|contents|index|preface|foreword|"
                          r"editorial board|book reviews?\b|abstracts? of|lecture notes in|list of (contributors|reviewers)|"
                          r"title page|masthead|issue information|acknowledg|correction|erratum|corrigendum|retract)", re.I)
BLURB_RE = re.compile(r"(this (book|volume|proceedings?) (constitutes|presents|contains)|refereed (post-)?(conference )?proceedings|"
                      r"lecture notes in|papers presented at the|this book series|proceedings of the \d)", re.I)


# ----------------------------------------------------------------------------- helpers
def P(B, *a):
    return os.path.join(B, *a)


def load_cfg(B):
    cfg = C.jload(P(B, "config.json"))
    for sk, sl in cfg["sublits"].items():
        sl["_inc"] = [re.compile(g, re.I) for g in sl["include"]]
        sl["_tany"] = re.compile(sl.get("title_any") or "|".join(sl["include"]), re.I)
        sl["_tmust"] = [re.compile(g, re.I) for g in sl.get("title_must", [])]
    cfg["_exc"] = re.compile(cfg["exclude"], re.I) if cfg.get("exclude") else None
    cfg["_core"] = [(re.compile(k, re.I), w) for k, w in cfg.get("core_terms", {}).items()]
    return cfg


def match_sublits(text, cfg, title=None):
    """Sub-literatures whose rule is met: every 'include' pattern in title+abstract AND every 'title_must' pattern in the title."""
    return [sk for sk, sl in cfg["sublits"].items()
            if all(g.search(text) for g in sl["_inc"]) and (title is None or all(g.search(title) for g in sl["_tmust"]))]


def title_any(title, cfg):
    return [sk for sk, sl in cfg["sublits"].items() if sl["_tany"].search(title)]


def prior_work_ids(B):
    """DOIs / arXiv ids named in the other agent's prior-work notes in the paper folder."""
    paper_dir = os.path.dirname(os.path.abspath(B))
    out = {"doi": set(), "arxiv": set(), "files": []}
    files = [f for f in glob.glob(os.path.join(paper_dir, "**", "*.md"), recursive=True)
             if "bibliometrics" not in f.lower() and re.search(r"prior[-_ ]?work|related[-_ ]?work|literature", os.path.basename(f), re.I)]
    for f in files:
        try:
            tx = open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        out["files"].append(f)
        for d in re.findall(r"10\.\d{4,9}/[^\s\"<>\)\]]+", tx):
            d = d.rstrip(".,;:").lower()
            m = re.match(r"10\.48550/arxiv\.(.+)", d)
            if m:
                out["arxiv"].add(m.group(1))
            else:
                out["doi"].add(d)
        for a in re.findall(r"arxiv(?:\.org/abs/|:\s?)(\d{4}\.\d{4,5})", tx, re.I):
            out["arxiv"].add(a)
    return out


# ----------------------------------------------------------------------------- stage 1: search
def s_crossref(q, n, ymin):
    types = ",".join("type:" + t for t in ["journal-article", "book-chapter", "posted-content", "proceedings-article", "book",
                                            "monograph", "report", "dissertation", "edited-book"])
    hits, raw = [], []
    cursor = "*"
    while len(hits) < n:
        rows = min(500, n - len(hits))
        url = (f"https://api.crossref.org/works?query.bibliographic={quote(q)}&rows={rows}&cursor={quote(cursor)}"
               f"&filter=from-pub-date:{ymin},{types}"
               f"&select=DOI,title,container-title,issued,type,is-referenced-by-count,abstract,author,score&mailto={C.MAILTO}")
        d = C.fetch_json(url)
        if not d:
            break
        raw.append(d)
        items = d["message"].get("items", [])
        for it in items:
            y = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
            au = it.get("author") or []
            hits.append(dict(title=C.strip_tags((it.get("title") or [""])[0]), doi=C.norm_doi(it.get("DOI")), year=y,
                             abstract=C.strip_tags(it.get("abstract")), venue=(it.get("container-title") or [""])[0],
                             first_author=(au[0].get("family", "") if au else ""), cites=it.get("is-referenced-by-count"),
                             type=it.get("type")))
        cursor = d["message"].get("next-cursor")
        if not items or not cursor:
            break
    total = raw[0]["message"].get("total-results") if raw else None
    return hits, raw, total


def s_s2(q, n, ymin):
    hits, raw, token, total = [], [], None, None
    while len(hits) < n:
        url = (f"https://api.semanticscholar.org/graph/v1/paper/search/bulk?query={quote(q)}&year={ymin}-"
               f"&fields=title,year,externalIds,citationCount,venue,abstract,authors,publicationTypes&sort=citationCount:desc")
        if token:
            url += f"&token={quote(token)}"
        d = C.fetch_json(url, retries=7)
        if not d or "data" not in d:
            break
        raw.append(d)
        total = d.get("total", total)
        for it in d["data"]:
            ex = it.get("externalIds") or {}
            au = it.get("authors") or []
            hits.append(dict(title=it.get("title") or "", doi=C.norm_doi(ex.get("DOI")), year=it.get("year"),
                             abstract=it.get("abstract") or "", venue=it.get("venue") or "",
                             first_author=(au[0]["name"].split()[-1] if au and au[0].get("name") else ""),
                             cites=it.get("citationCount"), mag=str(ex.get("MAG") or ""), arxiv=str(ex.get("ArXiv") or ""),
                             s2id=it.get("paperId")))
        token = d.get("token")
        if not token:
            break
    return hits[:n], raw, total


def s_eric(q, n, ymin):
    hits, raw, start, total = [], [], 0, None
    while len(hits) < n:
        url = (f"https://api.ies.ed.gov/eric/?search={quote(q)}&rows=200&start={start}&format=json"
               f"&fields=id,title,author,source,publicationdateyear,description,subject,publicationtype,language,peerreviewed")
        d = C.fetch_json(url)
        if not d or "response" not in d:
            break
        raw.append(d)
        total = d["response"].get("numFound")
        docs = d["response"].get("docs", [])
        for it in docs:
            y = it.get("publicationdateyear")
            if y and y < ymin:
                continue
            au = it.get("author") or []
            hits.append(dict(title=(it.get("title") or "").rstrip("."), doi="", year=y, abstract=it.get("description") or "",
                             venue=it.get("source") or "", first_author=(au[0].split(",")[0] if au else ""), cites=None,
                             eric=it.get("id")))
        start += 200
        if not docs or start >= (total or 0):
            break
    return hits[:n], raw, total


def s_arxiv(q, n, ymin):
    url = f"https://export.arxiv.org/api/query?search_query={quote(q)}&max_results={min(n, 200)}&sortBy=relevance"
    st, tx = C.fetch(url)
    hits = []
    if st != 200:
        return hits, [], None
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom", "o": "http://a9.com/-/spec/opensearch/1.1/"}
    try:
        root = ET.fromstring(tx)
    except Exception:
        return hits, [tx[:2000]], None
    total = root.findtext("o:totalResults", namespaces=ns)
    for e in root.findall("a:entry", ns):
        aid = re.sub(r"v\d+$", "", (e.findtext("a:id", namespaces=ns) or "").rsplit("/abs/", 1)[-1])
        y = int((e.findtext("a:published", namespaces=ns) or "0000")[:4])
        if y < ymin:
            continue
        au = [a.findtext("a:name", namespaces=ns) for a in e.findall("a:author", ns)]
        hits.append(dict(title=re.sub(r"\s+", " ", e.findtext("a:title", namespaces=ns) or "").strip(),
                         doi=C.norm_doi(e.findtext("x:doi", namespaces=ns)), year=y,
                         abstract=re.sub(r"\s+", " ", e.findtext("a:summary", namespaces=ns) or "").strip(), venue="arXiv",
                         first_author=(au[0].split()[-1] if au and au[0] else ""), cites=None, arxiv=aid))
    return hits, [tx], int(total) if total else None


def s_openalex(q, n, ymin):
    """Costs 10 credits per call from the shared keyless daily budget; usually exhausted. Logged either way."""
    url = (f"https://api.openalex.org/works?search={quote(q)}&per-page=200&filter=from_publication_date:{ymin}-01-01"
           f"&select=id,doi,title,publication_year,cited_by_count&mailto={C.MAILTO}")
    st, tx = C.fetch(url, retries=1)
    if st != 200:
        return None, [], None
    d = json.loads(tx)
    hits = [dict(title=w.get("title") or "", doi=C.norm_doi(w.get("doi")), year=w.get("publication_year"), abstract="",
                 venue="", first_author="", cites=w.get("cited_by_count"), oaid=C.wid(w["id"])) for w in d.get("results", [])]
    return hits, [d], d.get("meta", {}).get("count")


SEARCHERS = {"crossref": s_crossref, "s2": s_s2, "eric": s_eric, "arxiv": s_arxiv, "openalex": s_openalex}
DEFAULT_N = {"crossref": 300, "s2": 1000, "eric": 400, "arxiv": 100, "openalex": 200}


def stage_search(B, cfg):
    all_hits, qlog = [], []
    for sk, sl in cfg["sublits"].items():
        for db in ["crossref", "s2", "eric", "arxiv", "openalex"]:
            for i, q in enumerate(sl.get(db, [])):
                qid = f"{db}_{sk}_{i+1:02d}"
                n = cfg.get("n_per_query", {}).get(db, DEFAULT_N[db])
                hits, raw, total = SEARCHERS[db](q, n, cfg["year_min"])
                status = "ok"
                if hits is None:
                    hits, status = [], "FAILED (OpenAlex keyless daily budget exhausted)"
                elif not raw:
                    status = "FAILED (no response)"
                C.jdump({"qid": qid, "db": db, "sublit": sk, "query": q, "date": TODAY, "responses": raw}, P(B, "data", "raw", db, qid + ".json"))
                for h in hits:
                    h.update(db=db, sublit=sk, qid=qid)
                all_hits.extend(hits)
                qlog.append(dict(qid=qid, db=db, sublit=sk, query=q, total_in_db=total, retrieved=len(hits), status=status, date=TODAY))
                print(f"  {qid}: total={total} retrieved={len(hits)} {status}", flush=True)
    # seeds: titles (verified against Crossref), DOIs, arXiv ids, prior-work notes
    seeds = []
    for t in cfg.get("seed_titles", []):
        d = C.fetch_json(f"https://api.crossref.org/works?query.bibliographic={quote(t)}&rows=5&select=DOI,title,issued,type&mailto={C.MAILTO}")
        best = None
        for it in (d or {}).get("message", {}).get("items", []):
            tt = (it.get("title") or [""])[0]
            sc = max(fuzz.ratio(C.norm_title(t), C.norm_title(tt)), fuzz.ratio(C.norm_title(t), C.norm_title(tt)[:len(C.norm_title(t)) + 2]))
            pref = 0 if it.get("type") == "journal-article" else 1
            if sc >= 90 and (best is None or (pref, -sc) < best[0]):
                best = ((pref, -sc), it)
        if best:
            it = best[1]
            seeds.append(dict(title=(it.get("title") or [""])[0], doi=C.norm_doi(it["DOI"]), year=None, abstract="", venue="", first_author="",
                              cites=None, db="seed", sublit="seed", qid="seed_title"))
            qlog.append(dict(qid="seed_title", db="seed", sublit="", query=t, total_in_db=None, retrieved=1, status="matched " + it["DOI"], date=TODAY))
        else:
            qlog.append(dict(qid="seed_title", db="seed", sublit="", query=t, total_in_db=None, retrieved=0, status="NOT MATCHED in Crossref", date=TODAY))
            print("  seed title not matched:", t)
    pw = prior_work_ids(B)
    for d in list(cfg.get("seed_dois", [])) + sorted(pw["doi"]):
        seeds.append(dict(title="", doi=C.norm_doi(d), year=None, abstract="", venue="", first_author="", cites=None, db="seed", sublit="seed", qid="seed_doi"))
    for a in list(cfg.get("seed_arxiv", [])) + sorted(pw["arxiv"]):
        seeds.append(dict(title="", doi="10.48550/arxiv." + a.lower(), year=None, abstract="", venue="arXiv", first_author="", cites=None,
                          db="seed", sublit="seed", qid="seed_arxiv", arxiv=a))
    all_hits.extend(seeds)
    df = pd.DataFrame(all_hits)
    for c in ["mag", "arxiv", "eric", "s2id", "oaid", "type"]:
        if c not in df:
            df[c] = ""
    df.to_csv(P(B, "data", "raw", "all_hits.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(qlog).to_csv(P(B, "data", "raw", "query_log.csv"), index=False, encoding="utf-8-sig")
    C.jdump({"prior_work_files": pw["files"], "prior_work_dois": sorted(pw["doi"]), "prior_work_arxiv": sorted(pw["arxiv"])},
            P(B, "data", "raw", "prior_work_ids.json"), indent=1)
    print(f"search: {len(df)} hits from {len(qlog)} queries")


# ----------------------------------------------------------------------------- stage 2: enrich + screen
def cand_key(r):
    if r["doi"]:
        return "doi:" + r["doi"]
    if r.get("arxiv"):
        return "doi:10.48550/arxiv." + str(r["arxiv"]).lower()
    if r.get("oaid"):
        return str(r["oaid"])
    if r.get("mag"):
        return "mag:" + str(r["mag"])
    return "title:" + C.norm_title(r["title"])


def title_to_doi(title, first_author=""):
    d = C.fetch_json(f"https://api.crossref.org/works?query.bibliographic={quote((title + ' ' + (first_author or ''))[:300])}"
                     f"&rows=3&select=DOI,title&mailto={C.MAILTO}")
    nt = C.norm_title(title)
    for it in (d or {}).get("message", {}).get("items", []):
        tt = C.norm_title((it.get("title") or [""])[0])
        if tt and len(nt) > 15 and fuzz.ratio(nt, tt) >= 93:
            return C.norm_doi(it["DOI"])
    return ""


def work_text(w):
    title = w.get("title") or w.get("display_name") or ""
    ab = C.abstract_from_inverted(w.get("abstract_inverted_index"))
    return title, ab


def screen_work(w, cfg, extra_abs="", blurb_abs=frozenset()):
    """Return (keep, reason, sublits). Same rules for search hits and snowballed records."""
    title, ab = work_text(w)
    if not ab:
        ab = extra_abs or ""
    if w.get("is_paratext") or CONTAINER_RE.search(title or "") or not title:
        return False, "paratext_or_container_record", []
    if w.get("type") not in KEEP_TYPES:
        return False, "type_excluded", []
    y = w.get("publication_year") or 0
    if y < cfg["year_min"] or y > cfg["year_max"]:
        return False, "year_out_of_range", []
    if w.get("language") not in (None, "en"):
        return False, "language_not_english", []
    if cfg["_exc"] is not None and cfg["_exc"].search(title):
        return False, "offtopic_exclusion_term_in_title", []
    is_blurb = bool(ab) and (BLURB_RE.search(ab) or C.norm_title(ab)[:300] in blurb_abs)
    if is_blurb:
        ab_use = ""
    else:
        ab_use = ab
    kw = " ; ".join(k.get("display_name", "") for k in (w.get("keywords") or [])) if not ab_use else ""
    sl = match_sublits(title + " . " + ab_use + " . " + kw, cfg, title)
    if not sl:
        return False, ("series_or_proceedings_blurb_only" if is_blurb and match_sublits(title + " " + ab, cfg, title) else "offtopic_fails_inclusion_rule"), []
    mc = cfg.get("min_citations_if_older_than")
    if mc and (w.get("cited_by_count") or 0) < mc[1] and y <= cfg["year_max"] - mc[0]:
        return False, "uncited_older_record (citation floor)", []
    return True, "", sl


def stage_enrich(B, cfg):
    df = pd.read_csv(P(B, "data", "raw", "all_hits.csv"), dtype=str, keep_default_na=False)
    df["key"] = df.apply(cand_key, axis=1)
    n_hits = len(df)
    grp = df.groupby("key")
    cands = grp.agg(title=("title", lambda s: max(s, key=len)), doi=("doi", "max"), abstract=("abstract", lambda s: max(s, key=len)),
                    first_author=("first_author", "max"), year=("year", "max"), dbs=("db", lambda s: ";".join(sorted(set(s)))),
                    sublits_q=("sublit", lambda s: ";".join(sorted(set(s)))), mag=("mag", "max"), eric=("eric", "max"),
                    arxiv=("arxiv", "max"), oaid=("oaid", "max"), n_hits=("db", "size")).reset_index()
    # merge DOI-less records onto DOI records with the same normalised title
    cands["nt"] = cands["title"].map(C.norm_title)
    doi_titles = {r.nt: r.key for r in cands.itertuples() if r.key.startswith("doi:") and len(r.nt) > 20}
    def merge_key(r):
        if not r.key.startswith("doi:") and r.nt in doi_titles:
            return doi_titles[r.nt]
        return r.key
    cands["key2"] = cands.apply(merge_key, axis=1)
    g2 = cands.groupby("key2")
    cands = g2.agg(title=("title", lambda s: max(s, key=len)), doi=("doi", "max"), abstract=("abstract", lambda s: max(s, key=len)),
                   first_author=("first_author", "max"), year=("year", "max"), dbs=("dbs", lambda s: ";".join(sorted(set(";".join(s).split(";"))))),
                   sublits_q=("sublits_q", lambda s: ";".join(sorted(set(";".join(s).split(";"))))), mag=("mag", "max"), eric=("eric", "max"),
                   arxiv=("arxiv", "max"), oaid=("oaid", "max"), n_hits=("n_hits", "sum")).reset_index().rename(columns={"key2": "key"})
    n_unique = len(cands)
    # title/abstract pre-screen (cheap, before any OpenAlex call)
    def pre(r):
        if "seed" in r.dbs.split(";"):
            return "seed"
        t = r.title
        if cfg["_exc"] is not None and cfg["_exc"].search(t):
            return ""
        if CONTAINER_RE.search(t):
            return ""
        if match_sublits(t + " . " + r.abstract, cfg, t) or (title_any(t, cfg) and not any(sl["_tmust"] for sl in cfg["sublits"].values())):
            return "pass"
        if not r.abstract and any(all(g.search(t) for g in sl["_tmust"]) and sl["_tmust"] for sl in cfg["sublits"].values()):
            return "pass"
        return ""
    cands["pre"] = cands.apply(pre, axis=1)
    todo = cands[cands.pre != ""].copy()
    print(f"enrich: hits={n_hits} unique={n_unique} pass title pre-screen={len(todo)}", flush=True)

    def resolve(r):
        key = r["key"]
        w = None
        if key.startswith("doi:"):
            w = C.oa_single(key)
            if w is None and r["mag"]:
                w = C.oa_single("mag:" + r["mag"])
        elif key.startswith("W"):
            w = C.oa_single(key)
        elif key.startswith("mag:"):
            w = C.oa_single(key)
        if w is None and not key.startswith("doi:") and r["title"]:
            d = title_to_doi(r["title"], r["first_author"])
            if d:
                w = C.oa_single("doi:" + d)
        return w
    recs = todo.to_dict("records")
    works = C.pmap(resolve, recs, workers=10, label="openalex")
    blurbs = Counter(C.norm_title(work_text(w)[1])[:300] for w in works if w and len(work_text(w)[1]) > 200)
    blurb_abs = frozenset(k for k, v in blurbs.items() if v >= 3)
    log, kept, seen = [], {}, {}
    raw_out = []
    for r, w in zip(recs, works):
        row = dict(key=r["key"], title=r["title"], dbs=r["dbs"], sublits_queried=r["sublits_q"], oa_id="", decision="", reason="", sublit="")
        if w is None:
            row.update(decision="excluded", reason="no_openalex_record (no DOI / not indexed)")
            log.append(row); continue
        oid = C.wid(w["id"])
        row["oa_id"] = oid
        row["title"] = w.get("title") or r["title"]
        if oid in seen:
            row.update(decision="duplicate", reason="same OpenAlex work as " + seen[oid])
            kept.get(oid, {}).get("_dbs", set()).update(r["dbs"].split(";"))
            log.append(row); continue
        seen[oid] = r["key"]
        raw_out.append(w)
        if r["pre"] == "seed" or "seed" in r["dbs"].split(";"):
            ok, why, sl = True, "", (screen_work(w, cfg, r["abstract"], blurb_abs)[2] or ["seed"])
        else:
            ok, why, sl = screen_work(w, cfg, r["abstract"], blurb_abs)
        if oid in cfg.get("manual_exclude", {}):
            ok, why = False, "manual_exclude: " + cfg["manual_exclude"][oid]
        if ok:
            w["_sublits"] = sl
            w["_origin"] = "seed" if "seed" in r["dbs"].split(";") else "search"
            w["_dbs"] = set(r["dbs"].split(";"))
            w["_abs_extra"] = r["abstract"] if not w.get("abstract_inverted_index") else ""
            kept[oid] = w
            row.update(decision="included", sublit=";".join(sl))
        else:
            row.update(decision="excluded", reason=why)
        log.append(row)
    # title duplicates (preprint + published version etc.)
    bytitle = defaultdict(list)
    for oid, w in kept.items():
        bytitle[C.norm_title(w.get("title"))].append(oid)
    ndup = 0
    logidx = {r["oa_id"]: r for r in log if r["decision"] == "included"}
    for nt, ids in bytitle.items():
        if len(ids) > 1 and len(nt) > 20:
            ids.sort(key=lambda i: (kept[i].get("type") == "preprint", -(kept[i].get("cited_by_count") or 0)))
            for i in ids[1:]:
                kept[ids[0]]["_dbs"].update(kept[i]["_dbs"])
                if kept[i]["_origin"] == "seed":
                    kept[ids[0]]["_origin"] = "seed"
                del kept[i]
                logidx[i].update(decision="duplicate", reason="same title as " + ids[0], sublit="")
                ndup += 1
    for w in kept.values():
        w["_dbs"] = sorted(w["_dbs"])
    C.jsonl_gz_write(P(B, "data", "raw", "openalex", "works_enriched_search.jsonl.gz"),
                     [{k: v for k, v in w.items() if not k.startswith("_")} for w in raw_out])
    C.jsonl_gz_write(P(B, "data", "clean", "corpus_stage1.jsonl.gz"), list(kept.values()))
    ld = pd.DataFrame(log)
    ld.to_csv(P(B, "data", "clean", "screening_log_search.csv"), index=False, encoding="utf-8-sig")
    unres = todo[todo.key.isin(set(ld[ld.reason.str.startswith("no_openalex")].key))][["key", "title", "first_author", "year", "dbs", "eric", "sublits_q"]]
    unres.to_csv(P(B, "data", "clean", "unresolved_candidates.csv"), index=False, encoding="utf-8-sig")
    counts = dict(date=TODAY, records_identified=n_hits, by_db=df.db.value_counts().to_dict(),
                  duplicates_removed_identifiers=n_hits - n_unique, unique_records=n_unique,
                  removed_title_prescreen=int(n_unique - len(todo)), sent_to_openalex=len(todo),
                  duplicates_removed_openalex=int((ld.decision == "duplicate").sum()),
                  excluded_reasons=ld[ld.decision == "excluded"].reason.map(lambda s: s.split(":")[0]).value_counts().to_dict(),
                  included_after_search_screen=len(kept))
    C.jdump(counts, P(B, "data", "clean", "prisma_search.json"), indent=1)
    C.save_api_log(P(B, "data", "api_log.json"))
    print("enrich:", json.dumps(counts)[:900])


# ----------------------------------------------------------------------------- stage 3: snowball
def local_cites(works):
    ids = set(C.wid(w["id"]) for w in works)
    lc = Counter()
    for w in works:
        for r in w.get("referenced_works") or []:
            r = C.wid(r)
            if r in ids:
                lc[r] += 1
    return lc


def relevance(w, cfg, lc=0):
    title, ab = work_text(w)
    ab = ab or w.get("_abs_extra", "")
    s = 0.0
    for rx, wt in cfg["_core"]:
        if rx.search(title):
            s += 2 * wt
        elif rx.search(ab):
            s += wt
    return s


def stage_snowball(B, cfg):
    works = C.jsonl_gz_read(P(B, "data", "clean", "corpus_stage1.jsonl.gz"))
    ids = set(C.wid(w["id"]) for w in works)
    lc = local_cites(works)
    ncen = cfg.get("snowball_n_central", 25)
    for w in works:
        w["_rel"] = relevance(w, cfg)
    # centrality = local citations, then topical relevance, then global citations
    ranked = sorted(works, key=lambda w: (-(lc[C.wid(w["id"])] + 2 * w["_rel"] + 2 * math.log10(1 + (w.get("cited_by_count") or 0)))))
    central = ranked[:ncen]
    back, fwd, fwd_log = Counter(), Counter(), []
    for w in central:
        for r in (w.get("referenced_works") or []):
            if C.wid(r) not in ids:
                back[C.wid(r)] += 1
    for w in central:
        doi = C.norm_doi(w.get("doi"))
        n = 0
        if doi:
            d = C.fetch_json(f"https://api.opencitations.net/index/v2/citations/doi:{quote(doi, safe='/.-_()')}", timeout=120, retries=3)
            if d is None:
                fwd_log.append((C.wid(w["id"]), doi, "OpenCitations: no response"))
            for c in (d or [])[: cfg.get("snowball_max_forward", 400) * 3]:
                m = re.search(r"openalex:(W\d+)", c.get("citing", ""))
                m2 = re.search(r"doi:(\S+)", c.get("citing", ""))
                k = m.group(1) if m else ("doi:" + m2.group(1) if m2 else None)
                if k and k not in ids:
                    fwd[k] += 1; n += 1
                    if n >= cfg.get("snowball_max_forward", 400):
                        break
        fwd_log.append((C.wid(w["id"]), doi, f"forward citers collected: {n}"))
    todo = [("back", k) for k in back] + [("fwd", k) for k in fwd if k not in back]
    print(f"snowball: central={len(central)} backward candidates={len(back)} forward candidates={len(fwd)}", flush=True)
    got = C.pmap(lambda t: C.oa_single(t[1]), todo, workers=12, label="snowball")
    added, log, raw_out, seen = [], [], [], set(ids)
    titles = set(C.norm_title(w.get("title")) for w in works)
    for (kind, k), w in zip(todo, got):
        if w is None:
            log.append(dict(key=k, kind=kind, oa_id="", title="", decision="excluded", reason="no_openalex_record", sublit="")); continue
        oid = C.wid(w["id"])
        if oid in seen or C.norm_title(w.get("title")) in titles:
            log.append(dict(key=k, kind=kind, oa_id=oid, title=w.get("title"), decision="duplicate", reason="already in corpus", sublit="")); continue
        seen.add(oid)
        raw_out.append(w)
        ok, why, sl = screen_work(w, cfg)
        if oid in cfg.get("manual_exclude", {}):
            ok, why = False, "manual_exclude: " + cfg["manual_exclude"][oid]
        if ok:
            w["_sublits"], w["_origin"], w["_dbs"], w["_abs_extra"] = sl, "snowball_" + ("backward" if kind == "back" else "forward"), ["openalex_snowball"], ""
            added.append(w); titles.add(C.norm_title(w.get("title")))
        log.append(dict(key=k, kind=kind, oa_id=oid, title=w.get("title"), decision="included" if ok else "excluded", reason=why, sublit=";".join(sl)))
    C.jsonl_gz_write(P(B, "data", "raw", "openalex", "works_enriched_snowball.jsonl.gz"), raw_out)
    C.jsonl_gz_write(P(B, "data", "clean", "corpus_final.jsonl.gz"), works + added)
    ld = pd.DataFrame(log)
    ld.to_csv(P(B, "data", "clean", "screening_log_snowball.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame([dict(oa_id=C.wid(w["id"]), title=w.get("title"), year=w.get("publication_year"), local_cites=lc[C.wid(w["id"])],
                       cited_by=w.get("cited_by_count"), relevance=w["_rel"]) for w in central]).to_csv(
        P(B, "data", "clean", "snowball_central_papers.csv"), index=False, encoding="utf-8-sig")
    counts = dict(central_papers=len(central), backward_candidates=len(back), forward_candidates=len([1 for t in todo if t[0] == "fwd"]),
                  snowball_screened=len(todo), snowball_duplicates=int((ld.decision == "duplicate").sum()) if len(ld) else 0,
                  snowball_excluded_reasons=ld[ld.decision == "excluded"].reason.map(lambda s: s.split(":")[0]).value_counts().to_dict() if len(ld) else {},
                  snowball_included=len(added), backward_included=sum(1 for w in added if w["_origin"].endswith("backward")),
                  forward_included=sum(1 for w in added if w["_origin"].endswith("forward")), forward_log=fwd_log,
                  final_corpus=len(works) + len(added))
    C.jdump(counts, P(B, "data", "clean", "prisma_snowball.json"), indent=1)
    C.save_api_log(P(B, "data", "api_log.json"))
    print("snowball:", {k: v for k, v in counts.items() if k != "forward_log"})


# ----------------------------------------------------------------------------- stage 4: resolve cited references
def stage_refs(B, cfg):
    works = C.jsonl_gz_read(P(B, "data", "clean", "corpus_final.jsonl.gz"))
    ids = set(C.wid(w["id"]) for w in works)
    cnt = Counter()
    for w in works:
        for r in set(w.get("referenced_works") or []):
            cnt[C.wid(r)] += 1
    cap = cfg.get("max_refs_resolve", 22000)
    order = [r for r, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0])) if r not in ids][:cap]
    print(f"refs: distinct cited works={len(cnt)} to resolve={len(order)} (cap {cap})", flush=True)
    got = C.pmap(lambda r: C.oa_single(r, C.OA_SELECT_REF), order, workers=12, label="refs", every=2000)
    out = [g for g in got if g]
    C.jsonl_gz_write(P(B, "data", "raw", "openalex", "refs_resolved.jsonl.gz"), out)
    C.jdump(dict(distinct_cited_works=len(cnt), cited_twice_or_more=sum(1 for v in cnt.values() if v >= 2), in_corpus=sum(1 for r in cnt if r in ids),
                 attempted=len(order), resolved=len(out), total_reference_links=sum(cnt.values())), P(B, "data", "clean", "refs_stats.json"), indent=1)
    C.save_api_log(P(B, "data", "api_log.json"))
    print(f"refs: resolved {len(out)}/{len(order)}")


# ----------------------------------------------------------------------------- stage 5: master table
PARTICLES = {"de", "del", "della", "der", "van", "von", "da", "di", "la", "le", "dos", "das", "du", "bin", "al", "el", "ter", "den"}
CO_FIX = {"US": "USA", "GB": "UNITED KINGDOM", "KR": "KOREA", "RU": "RUSSIA", "IR": "IRAN", "TW": "TAIWAN", "VN": "VIETNAM", "CZ": "CZECH REPUBLIC",
          "TZ": "TANZANIA", "SY": "SYRIA", "VE": "VENEZUELA", "BO": "BOLIVIA", "MD": "MOLDOVA", "LA": "LAOS", "BN": "BRUNEI", "TR": "TURKEY",
          "HK": "HONG KONG", "MO": "MACAU", "PS": "PALESTINE", "CD": "DR CONGO", "CI": "IVORY COAST", "MK": "NORTH MACEDONIA", "XK": "KOSOVO"}


def co_name(code):
    if not code:
        return ""
    if code in CO_FIX:
        return CO_FIX[code]
    try:
        import pycountry
        c = pycountry.countries.get(alpha_2=code)
        return C.ascii_up(c.name.split(",")[0]) if c else code
    except Exception:
        return code


def au_short(name):
    n = C.ascii_up(name).replace(",", " ").replace(";", " ").replace(".", " ")
    toks = [t for t in n.split() if t]
    if not toks:
        return ""
    if len(toks) == 1:
        return toks[0]
    i = len(toks) - 1
    while i - 1 >= 1 and toks[i - 1].lower() in PARTICLES:
        i -= 1
    sur = " ".join(toks[i:])
    ini = "".join(t[0] for t in toks[:i])
    return f"{sur} {ini}".strip()


def clean_field(s):
    return re.sub(r"\s+", " ", re.sub(r"[;,]", " ", C.ascii_up(s or ""))).strip()


def src_name(w):
    s = ((w.get("primary_location") or {}).get("source") or {})
    return s.get("display_name") or ""


def cr_string(w):
    """WoS-style cited-reference string, deterministic per OpenAlex work."""
    au = w.get("authorships") or []
    a1 = au_short(au[0]["author"]["display_name"]) if au and au[0].get("author", {}).get("display_name") else "ANONYMOUS"
    y = w.get("publication_year")
    if not y:
        return None
    so = clean_field(src_name(w)) or {"book": "BOOK", "book-chapter": "BOOK CHAPTER", "dissertation": "THESIS", "report": "REPORT",
                                      "preprint": "PREPRINT"}.get(w.get("type"), "UNPUBLISHED")
    return f"{a1}, {y}, {so}"


def cr_full(w, sr):
    b = w.get("biblio") or {}
    s = sr
    if b.get("volume"):
        s += f", V{clean_field(str(b['volume']))}"
    if b.get("first_page"):
        s += f", P{clean_field(str(b['first_page']))}"
    d = C.norm_doi(w.get("doi"))
    if d:
        s += f", DOI {d.replace(';', '').replace(',', '').upper()}"
    return s


def stage_master(B, cfg):
    works = C.jsonl_gz_read(P(B, "data", "clean", "corpus_final.jsonl.gz"))
    mex = cfg.get("manual_exclude", {})
    n_before = len(works)
    removed_manual = [dict(oa_id=C.wid(w["id"]), title=w.get("title"), reason=mex[C.wid(w["id"])]) for w in works if C.wid(w["id"]) in mex]
    works = [w for w in works if C.wid(w["id"]) not in mex]
    refs = {C.wid(r["id"]): r for r in C.jsonl_gz_read(P(B, "data", "raw", "openalex", "refs_resolved.jsonl.gz"))}
    ids = [C.wid(w["id"]) for w in works]
    idset = set(ids)
    byid = dict(zip(ids, works))
    lc = local_cites(works)
    # unique SR labels for corpus docs
    sr, used = {}, Counter()
    for i in ids:
        base = cr_string(byid[i]) or f"ANONYMOUS, {byid[i].get('publication_year')}, UNPUBLISHED"
        used[base] += 1
        sr[i] = base if used[base] == 1 else f"{base}-{chr(96 + used[base])}"
    refsr = {}
    for r, w in refs.items():
        s = cr_string(w)
        if s:
            refsr[r] = cr_full(w, s)
    for i in ids:
        refsr[i] = cr_full(byid[i], sr[i])
    rows, brows, edges = [], [], []
    for i in ids:
        w = byid[i]
        title, ab = work_text(w)
        ab = ab or w.get("_abs_extra", "")
        aus = w.get("authorships") or []
        names = [a["author"].get("display_name") or "" for a in aus if a.get("author")]
        insts, ccodes, c1, first_co, corr_co, first_un, corr_un = [], [], [], "", "", "", ""
        for k, a in enumerate(aus):
            a_c = list(a.get("countries") or [])
            for ins in a.get("institutions") or []:
                nm = clean_field(ins.get("display_name"))
                cc = ins.get("country_code") or ""
                if nm:
                    insts.append(nm)
                    c1.append(f"{nm}, {co_name(cc)}" if cc else nm)
                if cc and cc not in a_c:
                    a_c.append(cc)
            ccodes.extend(a_c)
            un = clean_field((a.get("institutions") or [{}])[0].get("display_name")) if a.get("institutions") else ""
            if k == 0:
                first_co, first_un = (a_c[0] if a_c else ""), un
            if a.get("is_corresponding") and not corr_co:
                corr_co, corr_un = (a_c[0] if a_c else ""), un
        corr_co, corr_un = corr_co or first_co, corr_un or first_un
        ucc = list(dict.fromkeys(ccodes))
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        oa = w.get("open_access") or {}
        best = w.get("best_oa_location") or {}
        pt = w.get("primary_topic") or {}
        kws = [k.get("display_name", "") for k in (w.get("keywords") or [])]
        topics = [t.get("display_name", "") for t in (w.get("topics") or [])]
        concepts = [c.get("display_name", "") for c in (w.get("concepts") or []) if (c.get("score") or 0) >= 0.35 and (c.get("level") or 0) >= 1]
        rw = [C.wid(r) for r in (w.get("referenced_works") or [])]
        for r in rw:
            if r in idset and r != i:
                edges.append((i, r))
        pdfs = [l.get("pdf_url") for l in (w.get("locations") or []) if l.get("pdf_url") and l.get("is_oa")]
        rows.append(dict(
            oa_id=i, doi=C.norm_doi(w.get("doi")), title=title, year=w.get("publication_year"), date=w.get("publication_date"), type=w.get("type"),
            language=w.get("language") or "", source=src.get("display_name") or "", source_type=src.get("type") or "",
            publisher=src.get("host_organization_name") or "", issn=src.get("issn_l") or "", authors="; ".join(names), n_authors=len(names),
            first_author=names[0] if names else "", institutions="; ".join(dict.fromkeys(insts)), countries="; ".join(ucc),
            first_author_country=first_co, corresponding_country=corr_co, international_collab=int(len(ucc) > 1),
            cited_by_count=w.get("cited_by_count") or 0, fwci=w.get("fwci"), local_citations=lc[i], n_refs=len(rw),
            is_oa=oa.get("is_oa"), oa_status=oa.get("oa_status") or "", oa_url=oa.get("oa_url") or "", best_pdf_url=best.get("pdf_url") or (pdfs[0] if pdfs else ""),
            best_oa_landing=best.get("landing_page_url") or "", all_pdf_urls=" | ".join(dict.fromkeys(pdfs)),
            sublit=w["_sublits"][0], sublits_all="; ".join(w["_sublits"]), origin=w["_origin"], found_in="; ".join(w["_dbs"]),
            relevance=round(relevance(w, cfg), 2), primary_topic=pt.get("display_name") or "", subfield=(pt.get("subfield") or {}).get("display_name") or "",
            field=(pt.get("field") or {}).get("display_name") or "", domain=(pt.get("domain") or {}).get("display_name") or "",
            keywords="; ".join(kws), topics="; ".join(topics), concepts="; ".join(concepts), abstract=ab, has_abstract=int(bool(ab)),
            is_retracted=w.get("is_retracted"), sr=sr[i]))
        crs = [refsr[r] for r in rw if r in refsr]
        so = clean_field(src.get("display_name")) or {"preprint": "PREPRINT / WORKING PAPER", "book": "BOOK", "book-chapter": "BOOK CHAPTER",
                                                       "dissertation": "THESIS", "report": "REPORT"}.get(w.get("type"), "NO SOURCE RECORDED")
        brows.append(dict(
            AU=";".join(au_short(n) for n in names if n) or "ANONYMOUS", AF=";".join(clean_field(n) for n in names if n) or "ANONYMOUS",
            TI=C.ascii_up(title), SO=so, JI=so, J9=so, DT=(w.get("type") or "").upper(), DE=";".join(clean_field(k) for k in kws if k),
            ID=";".join(dict.fromkeys(clean_field(k) for k in concepts + topics if k)), AB=C.ascii_up(ab), C1=";".join(dict.fromkeys(c1)),
            RP=f"{corr_un}, {co_name(corr_co)}" if corr_un or corr_co else "", CR=";".join(dict.fromkeys(crs)), TC=w.get("cited_by_count") or 0,
            PY=w.get("publication_year"), DI=C.norm_doi(w.get("doi")).upper(), LA="ENGLISH", UT=i, DB="ISI", SR=sr[i], SR_FULL=sr[i],
            AU_UN=";".join(dict.fromkeys(insts)), AU1_UN=corr_un, AU_CO=";".join(co_name(c) for c in ucc), AU1_CO=co_name(corr_co),
            SUBLIT=w["_sublits"][0], LCS=lc[i], NR=len(rw), id_oa=i))
    os.makedirs(P(B, "data", "clean"), exist_ok=True)
    M = pd.DataFrame(rows)
    # ---- cross-checks: Crossref (per DOI) and Semantic Scholar (batch)
    dois = [d for d in M.doi if d][: cfg.get("max_crosscheck", 2500)]
    def cr1(d):
        j = C.fetch_json(f"https://api.crossref.org/works/{quote(d, safe='/.-_()')}?mailto={C.MAILTO}")
        m = (j or {}).get("message")
        return (d, m.get("is-referenced-by-count"), m.get("reference-count"), int(bool(m.get("abstract")))) if m else (d, None, None, None)
    cr = C.pmap(cr1, dois, workers=4, label="crossref-check", every=500)
    crd = {t[0]: t for t in cr if t}
    M["crossref_cited_by"] = M.doi.map(lambda d: crd.get(d, (0, None, None, None))[1])
    M["crossref_n_refs"] = M.doi.map(lambda d: crd.get(d, (0, None, None, None))[2])
    s2 = {}
    for k in range(0, len(dois), 400):
        chunk = dois[k:k + 400]
        st, tx = C.fetch("https://api.semanticscholar.org/graph/v1/paper/batch?fields=citationCount,referenceCount,externalIds,openAccessPdf",
                         method="POST", body={"ids": ["DOI:" + d for d in chunk]}, retries=7)
        if st == 200:
            for d, it in zip(chunk, json.loads(tx)):
                if it:
                    s2[d] = it
        else:
            C.API_LOG.append(("api.semanticscholar.org", "paper/batch", st, "batch cross-check chunk failed"))
    M["s2_citation_count"] = M.doi.map(lambda d: (s2.get(d) or {}).get("citationCount"))
    M["s2_pdf_url"] = M.doi.map(lambda d: ((s2.get(d) or {}).get("openAccessPdf") or {}).get("url") or "")
    M.to_csv(P(B, "data", "clean", "master.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(brows).to_csv(P(B, "data", "clean", "bibliometrix_input.csv"), index=False, encoding="utf-8")
    pd.DataFrame(edges, columns=["citing", "cited"]).to_csv(P(B, "data", "clean", "citation_edges.csv"), index=False)
    refrows = []
    cnt = Counter(C.wid(r) for w in works for r in set(w.get("referenced_works") or []))
    for r, n in cnt.most_common():
        w = byid.get(r) or refs.get(r)
        if w:
            au = w.get("authorships") or []
            refrows.append(dict(oa_id=r, local_citations=n, in_corpus=int(r in idset), first_author=(au[0]["author"].get("display_name") if au else ""),
                                year=w.get("publication_year"), title=w.get("display_name") or w.get("title"), source=src_name(w),
                                doi=C.norm_doi(w.get("doi")), global_citations=w.get("cited_by_count"), cr_label=refsr.get(r, "")))
    pd.DataFrame(refrows).to_csv(P(B, "data", "clean", "cited_references.csv"), index=False, encoding="utf-8-sig")
    # ---- PRISMA table
    p1 = C.jload(P(B, "data", "clean", "prisma_search.json"), {})
    p2 = C.jload(P(B, "data", "clean", "prisma_snowball.json"), {})
    rs = C.jload(P(B, "data", "clean", "refs_stats.json"), {})
    prisma = [("Records identified through database searching (all query hits)", p1.get("records_identified"))]
    for db, n in sorted(p1.get("by_db", {}).items()):
        prisma.append((f"   of which from {db}", n))
    prisma += [("Duplicates removed (same DOI / id / title across queries and databases)", p1.get("duplicates_removed_identifiers")),
               ("Unique records screened on title (+ abstract where the database supplied one)", p1.get("unique_records")),
               ("Removed at title pre-screen (off-topic)", p1.get("removed_title_prescreen")),
               ("Records looked up in OpenAlex", p1.get("sent_to_openalex")),
               ("Duplicates removed after OpenAlex matching (same work / same title)", p1.get("duplicates_removed_openalex"))]
    for r, n in sorted(p1.get("excluded_reasons", {}).items(), key=lambda kv: -kv[1]):
        prisma.append((f"Excluded at full screen: {r}", n))
    prisma += [("Included after search screening", p1.get("included_after_search_screen")),
               ("Snowball: central papers used", p2.get("central_papers")),
               ("Snowball: backward-reference candidates", p2.get("backward_candidates")),
               ("Snowball: forward-citation candidates (OpenCitations)", p2.get("forward_candidates")),
               ("Snowball: duplicates of corpus records", p2.get("snowball_duplicates"))]
    for r, n in sorted(p2.get("snowball_excluded_reasons", {}).items(), key=lambda kv: -kv[1]):
        prisma.append((f"Snowball excluded: {r}", n))
    prisma += [("Snowball: included (backward)", p2.get("backward_included")), ("Snowball: included (forward)", p2.get("forward_included")),
               ("Corpus before hand-screening", n_before), ("Removed at hand-screening (see tables/hand_screen_removed.csv)", len(removed_manual)),
               ("FINAL CORPUS", len(works)), ("   with abstract", int(M.has_abstract.sum())), ("   with DOI", int((M.doi != "").sum())),
               ("   with a reference list in OpenAlex", int((M.n_refs > 0).sum())),
               ("Distinct cited references / resolved to metadata", f"{rs.get('distinct_cited_works')} / {rs.get('resolved')}")]
    os.makedirs(P(B, "tables"), exist_ok=True)
    pd.DataFrame(prisma, columns=["stage", "n"]).to_csv(P(B, "tables", "prisma_counts.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(removed_manual).to_csv(P(B, "tables", "hand_screen_removed.csv"), index=False, encoding="utf-8-sig")
    # ---- coverage / cross-check table
    def corr(a, b):
        d = M[[a, b]].dropna()
        return round(d[a].corr(d[b], method="spearman"), 3) if len(d) > 5 else None
    cov = [("corpus records", len(M)), ("records with DOI", int((M.doi != "").sum())),
           ("found in Crossref (DOI lookup)", int(M.crossref_cited_by.notna().sum())), ("found in Semantic Scholar (batch DOI lookup)", int(M.s2_citation_count.notna().sum())),
           ("Spearman corr. OpenAlex vs Crossref cited-by", corr("cited_by_count", "crossref_cited_by")),
           ("Spearman corr. OpenAlex vs Semantic Scholar cited-by", corr("cited_by_count", "s2_citation_count")),
           ("median cited-by: OpenAlex", float(M.cited_by_count.median())), ("median cited-by: Crossref", M.crossref_cited_by.median()),
           ("median cited-by: Semantic Scholar", M.s2_citation_count.median()),
           ("records with no reference list in OpenAlex", int((M.n_refs == 0).sum())),
           ("  of which Crossref holds a reference list", int(((M.n_refs == 0) & (M.crossref_n_refs.fillna(0) > 0)).sum())),
           ("records with no institution/country data", int((M.countries == "").sum())), ("records without abstract", int((M.has_abstract == 0).sum())),
           ("open-access records (OpenAlex)", int(M.is_oa.fillna(False).astype(bool).sum()))]
    for o, n in M.origin.value_counts().items():
        cov.append((f"origin: {o}", int(n)))
    fi = Counter(d for s in M.found_in for d in s.split("; "))
    for d, n in fi.most_common():
        cov.append((f"retrieved by: {d}", n))
    pd.DataFrame(cov, columns=["item", "value"]).to_csv(P(B, "tables", "coverage_crosscheck.csv"), index=False, encoding="utf-8-sig")
    # ---- prior-work coverage
    pw = prior_work_ids(B)
    pwd = [dict(id=d, kind="doi", in_corpus=int(d in set(M.doi))) for d in sorted(pw["doi"])]
    arx_in = set(M.doi) | set(x for w in works for x in [C.norm_doi((w.get("ids") or {}).get("doi"))])
    for a in sorted(set(pw["arxiv"]) | set(cfg.get("seed_arxiv", []))):
        w = C.oa_single("doi:10.48550/arxiv." + a.lower(), "id,title")
        pwd.append(dict(id="arXiv:" + a, kind="arxiv", in_corpus=int(bool(w) and (C.wid(w["id"]) in idset or C.norm_title(w.get("title")) in set(M.title.map(C.norm_title)))),
                        title=(w or {}).get("title", "NOT IN OPENALEX")))
    pd.DataFrame(pwd).to_csv(P(B, "tables", "prior_work_coverage.csv"), index=False, encoding="utf-8-sig")
    # ---- evidence-table candidates (top by topical relevance, then local + global citations)
    M["_rank"] = M.relevance * 2 + M.local_citations.map(lambda x: math.log1p(x)) + M.cited_by_count.map(lambda x: 0.5 * math.log1p(x))
    top = M.sort_values("_rank", ascending=False).head(cfg.get("n_evidence_candidates", 70))
    C.jdump([dict(oa_id=r.oa_id, doi=r.doi, title=r.title, year=r.year, authors=r.authors, source=r.source, type=r.type, sublit=r.sublit,
                  cited_by=r.cited_by_count, local_citations=r.local_citations, relevance=r.relevance, countries=r.countries,
                  oa_url=r.oa_url, pdf=r.best_pdf_url, abstract=r.abstract) for r in top.itertuples()],
            P(B, "data", "clean", "evidence_candidates.json"), indent=1)
    C.save_api_log(P(B, "data", "api_log.json"))
    print(f"master: corpus={len(M)} edges={len(edges)} refs_labelled={len(refsr)} manual_removed={len(removed_manual)}")
    print(M.sublit.value_counts().to_string())


STAGES = {"search": stage_search, "enrich": stage_enrich, "snowball": stage_snowball, "refs": stage_refs, "master": stage_master}

if __name__ == "__main__":
    B = os.path.abspath(sys.argv[1])
    if not os.path.exists("D:\\"):
        sys.exit("D: is missing - stopping.")
    stages = sys.argv[2:]
    if stages == ["all"]:
        stages = list(STAGES)
    cfg = load_cfg(B)
    for s in stages:
        t0 = time.time()
        print(f"=== {cfg['paper_id']} :: {s}", flush=True)
        STAGES[s](B, cfg)
        print(f"=== {s} done in {time.time()-t0:.0f}s", flush=True)
