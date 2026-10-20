"""Select 30-60 evidence-table papers and write data/clean/evidence_notes.json (input of pdfs.py evidence).

Usage: python evidence_auto.py <bibliometrics_dir> [n_total]

Selection: records with a real abstract (>= 250 chars), balanced across sub-literatures (weight ~ sqrt(size)), best topical
relevance + local/global citations first; every prior-work paper that is in the corpus is added. The 'finding' column is a
VERBATIM sentence from the abstract chosen by cue words (found / show / result / evidence ...), never paraphrased. study_type,
method and data are keyword-detected from the abstract and say 'not stated in abstract' when nothing matches. All rows are
'abstract read' (the abstract text was read by the pipeline, then the top rows spot-checked by hand); none is 'full text read'
unless the notes file is edited by hand afterwards.
"""
import json, math, os, re, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import pipeline as PL

B = os.path.abspath(sys.argv[1])
NTOT = int(sys.argv[2]) if len(sys.argv) > 2 else 48
cfg = C.jload(os.path.join(B, "config.json"))
M = pd.read_csv(os.path.join(B, "data", "clean", "master.csv"), encoding="utf-8-sig", keep_default_na=False)
for c in ("relevance", "local_citations", "cited_by_count"):
    M[c] = pd.to_numeric(M[c], errors="coerce").fillna(0)
M["_rank"] = M.relevance * 2 + M.local_citations.map(math.log1p) + 0.5 * M.cited_by_count.map(math.log1p)
M["alen"] = M.abstract.str.len()
ok = M[(M.alen >= 250) & (M.is_retracted.astype(str).str.lower() != "true") & M.type.isin(["article", "review", "preprint", "report", "book-chapter", "book", "dissertation"])]
ok = ok.sort_values("_rank", ascending=False)

# ---- balanced selection across sub-literatures
groups = {k: list(g.oa_id) for k, g in ok.groupby("sublit")}
size = {k: len(v) for k, v in groups.items()}
w = {k: math.sqrt(v) for k, v in size.items()}
tot = sum(w.values())
quota = {k: max(6, round(NTOT * w[k] / tot)) for k in groups}
quota = {k: min(q, size[k]) for k, q in quota.items()}
sel = []
for k, q in quota.items():
    sel += groups[k][:q]
# ---- prior-work papers in the corpus
pw = PL.prior_work_ids(B)
pwids = []
for d in pw["doi"]:
    hit = M[M.doi.str.lower() == d]
    if len(hit):
        pwids.append(hit.iloc[0].oa_id)
for oid in pwids:
    if oid not in sel:
        sel.append(oid)
Mi = M.set_index("oa_id")

CUES = re.compile(r"\b(we find|find that|found that|finds that|results? (show|indicate|suggest|reveal)|show(s|ed)? that|reveal(s|ed)?|"
                  r"evidence (suggests?|shows?|indicates?)|conclude|suggests? that|indicates? that|significantly|increase[sd]?|decrease[sd]?|"
                  r"reduc(e|ed|es|tion)|effect of|impact|associated with|higher|lower|more likely|less likely)\b", re.I)
STUDY = [
    (r"randomi[sz]ed (controlled|field|experiment|trial)|field experiment|double-blind|\bRCT\b", "Randomised experiment"),
    (r"natural experiment|quasi-experiment|difference-in-differences?|regression discontinuity|instrumental variable|event study", "Quasi-experimental / natural experiment"),
    (r"meta-analy", "Meta-analysis"), (r"systematic (literature )?review|scoping review|systematic mapping", "Systematic review"),
    (r"literature review|review of (the )?literature|this review|narrative review", "Literature review"),
    (r"questionnaire|survey|respondents|interviews?|focus group|likert", "Survey / interview study"),
    (r"case study", "Case study"),
    (r"deep learning|neural network|\bCNN\b|computer vision|classifier|prototype|we propose|proposed (system|model|method)|biometric", "System / method proposal"),
    (r"panel data|administrative data|regression|econometric|fixed effects|large-scale|longitudinal", "Observational / econometric analysis"),
    (r"corpus|text analysis|content analysis|topic model|text mining|word embedding|natural language", "Text / content analysis"),
    (r"conceptual|theoretical|theory|doctrine|legal analysis|statute|case law|jurisprudence|comparative law", "Conceptual / doctrinal analysis"),
    (r"simulation|agent-based|model(l?ing)?\b", "Model / simulation"),
]
METHOD = [
    (r"difference-in-differences?", "difference-in-differences"), (r"regression discontinuity", "regression discontinuity"), (r"instrumental variable", "instrumental variables"),
    (r"randomi[sz]ed|field experiment|\bRCT\b", "randomised experiment"), (r"fixed effects", "fixed-effects regression"), (r"regression", "regression analysis"),
    (r"structural equation|\bSEM\b|factor analysis", "structural equation / factor analysis"), (r"questionnaire|survey", "questionnaire survey"), (r"interview", "interviews"),
    (r"focus group", "focus groups"), (r"case study", "case study"), (r"thematic analysis|content analysis", "thematic / content analysis"), (r"topic model", "topic modelling"),
    (r"word embedding|natural language|text mining|text analysis|corpus", "computational text analysis"), (r"deep learning|neural network|\bCNN\b", "deep learning"),
    (r"machine learning", "machine learning"), (r"computer vision|video", "video / computer-vision"), (r"bibliometric|scientometric|co-citation", "bibliometric analysis"),
    (r"meta-analy", "meta-analysis"), (r"systematic review|literature review|scoping review", "literature review"), (r"doctrinal|case law|statut|legal analysis", "doctrinal / legal analysis"),
    (r"comparative", "comparative analysis"), (r"time series|interrupted", "time-series analysis"), (r"descriptive statistics|percentage", "descriptive statistics"),
]
DATA = re.compile(r"(?:^|(?<=[.!?] ))([^.!?]*\b(data(set)?s? (from|on|of|for)|sample of|samples? (of|from)|survey of|respondents|participants|students (from|in)|"
                  r"records|observations|schools|enrol+ed|panel of|(\d[\d,]*) (students|pupils|candidates|schools|firms|countries|respondents|participants|articles|studies|papers|cases))[^.!?]*[.!?])", re.I)
COUNTRIES = {"India": r"\bindia(n)?\b|karnataka|kerala|tamil nadu|bihar|uttar pradesh|maharashtra|rajasthan|gujarat|delhi", "United States": r"\bunited states\b|\bU\.S\.A?\b|\bUSA\b|\bamerican\b",
             "United Kingdom": r"\bunited kingdom\b|\bU\.K\.|\bUK\b|\bengland\b|\bbritish\b|\bscotland\b", "Nigeria": r"\bnigeria(n)?\b", "Kenya": r"\bkenya(n)?\b", "Pakistan": r"\bpakistan(i)?\b",
             "Italy": r"\bitaly\b|\bitalian\b", "China": r"\bchina\b|\bchinese\b", "Ghana": r"\bghana(ian)?\b", "Ethiopia": r"\bethiopia(n)?\b", "Zambia": r"\bzambia(n)?\b",
             "Uganda": r"\buganda(n)?\b", "Singapore": r"\bsingapore\b", "Australia": r"\baustralia(n)?\b", "Germany": r"\bgermany\b|\bgerman\b", "Canada": r"\bcanada\b|\bcanadian\b",
             "Malaysia": r"\bmalaysia(n)?\b", "Bangladesh": r"\bbangladesh(i)?\b", "Indonesia": r"\bindonesia(n)?\b", "South Africa": r"\bsouth africa(n)?\b", "Turkey": r"\bturk(ey|ish)\b",
             "Russia": r"\brussia(n)?\b", "Hong Kong": r"\bhong kong\b", "Sub-Saharan Africa": r"\bsub-saharan\b|\bAfrica\b", "Latin America": r"\blatin america\b"}
ISO = {"IN": "India", "US": "United States", "GB": "United Kingdom", "NG": "Nigeria", "KE": "Kenya", "PK": "Pakistan", "IT": "Italy", "CN": "China", "SG": "Singapore", "AU": "Australia",
       "DE": "Germany", "CA": "Canada", "MY": "Malaysia", "BD": "Bangladesh", "ID": "Indonesia", "ZA": "South Africa", "TR": "Turkey", "ET": "Ethiopia", "ZM": "Zambia", "UG": "Uganda", "GH": "Ghana"}


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", re.sub(r"\s+", " ", t)) if len(s.strip()) > 25]


def finding(t):
    ss = sentences(t)
    best, bs = None, -1
    for i, s in enumerate(ss):
        sc = (len(CUES.findall(s)) * 2 + (1 if i >= len(ss) // 2 else 0) + (3 if re.search(r"\b(we find|we found|found that|find that|results? (show|indicate|suggest|reveal)|findings? (show|indicate|suggest|reveal)|show(s|ed)? that)\b", s, re.I) else 0)
              - (4 if re.match(r"(this|the present|the) (paper|study|article|research|objective|purpose|aim)|(the )?(objective|purpose|aim) of", s, re.I) else 0)
              - (3 if re.search(r"\b(was|were) (used|administered|sent|collected|adopted|selected)|titled|is organi[sz]ed|we (use|used|propose|develop)\b", s, re.I) else 0))
        if sc > bs:
            best, bs = s, sc
    best = best or (ss[-1] if ss else t[:300])
    return best if len(best) <= 420 else best[:417].rsplit(" ", 1)[0] + " [...]"


def first(rules, t, default):
    for p, lab in rules:
        if re.search(p, t, re.I):
            return lab
    return default


REL = cfg.get("evidence_relation") or {}
DEFAULT_REL = {"seed": "Named in the paper's own prior-work notes; core comparison for the design."}
notes = []
for oid in sel:
    r = Mi.loc[oid]
    t = r.abstract or ""
    txt = f"{r.title}. {t}"
    st = first(STUDY, txt, "not stated in abstract")
    meths = []
    for p, lab in METHOD:
        if re.search(p, txt, re.I) and lab not in meths:
            meths.append(lab)
    dm = DATA.search(t)
    ctry = [c for c, p in COUNTRIES.items() if re.search(p, txt, 0 if c in ("United States", "United Kingdom") else re.I)]
    ctry += [ISO[c] for c in r.countries.split("; ") if c in ISO and ISO[c] not in ctry] if not ctry else []
    rel = REL.get(r.sublit) or DEFAULT_REL.get(r.sublit, "")
    for pat, text in (cfg.get("evidence_relation_keywords") or {}).items():
        if re.search(pat, txt, re.I):
            rel = text
            break
    has_abs = len(t) >= 250
    notes.append(dict(oa_id=oid, include=True, study_type=st, country=", ".join(ctry[:4]) if ctry else "not stated in abstract",
                      data=(dm.group(1).strip()[:230] if dm else "not stated in abstract"),
                      method="; ".join(meths[:3]) if meths else "not stated in abstract",
                      finding=finding(t) if has_abs else "No abstract available in OpenAlex/Crossref/Semantic Scholar; metadata only.",
                      read_status="abstract read" if has_abs else "metadata only (no abstract)", relation=rel))
C.jdump(notes, os.path.join(B, "data", "clean", "evidence_notes.json"), indent=1)
print(len(notes), "evidence rows;", len(pwids), "prior-work papers in corpus; quotas", quota)
