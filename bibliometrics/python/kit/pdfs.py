"""Download legal open-access PDFs of the core papers, and assemble evidence-table.csv.

Usage: python pdfs.py <bibliometrics_dir> download     (core = papers listed in data/clean/evidence_notes.json, else top 30 candidates)
       python pdfs.py <bibliometrics_dir> evidence     (merge evidence_notes.json + master.csv -> evidence-table.csv)

Only locations that OpenAlex / Semantic Scholar flag as open access are tried (publisher OA, arXiv, SSRN-free excluded,
institutional and subject repositories). ResearchGate / Academia.edu and anything else are skipped. Cap: 300 MB per paper folder.
"""
import os, re, sys, time
from urllib.parse import urlparse
import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

B = os.path.abspath(sys.argv[1])
mode = sys.argv[2]
if not os.path.exists("D:\\"):
    sys.exit("D: is missing")
PDF = os.path.join(B, "pdfs")
os.makedirs(PDF, exist_ok=True)
M = pd.read_csv(os.path.join(B, "data", "clean", "master.csv"), encoding="utf-8-sig", keep_default_na=False).set_index("oa_id")
notes = C.jload(os.path.join(B, "data", "clean", "evidence_notes.json"), None)
cands = C.jload(os.path.join(B, "data", "clean", "evidence_candidates.json"), [])
BLOCK = re.compile(r"(researchgate\.net|academia\.edu|sci-hub|libgen|z-lib|annas-archive|scholar\.archive\.org/fatcat)", re.I)
CAP_TOTAL, CAP_FILE = 300 * 1024 * 1024, 45 * 1024 * 1024


def fname(r):
    sur = re.sub(r"[^A-Za-z]", "", (r.first_author or "Anon").split()[-1]) or "Anon"
    t = re.sub(r"[^A-Za-z0-9]+", "-", r.title)[:55].strip("-")
    return f"{sur}_{int(float(r.year))}_{t}.pdf"


def cite(r):
    au = [a.strip() for a in r.authors.split(";") if a.strip()]
    a = au[0] + " et al." if len(au) > 3 else ", ".join(au)
    s = f"{a} ({int(float(r.year))}). {r.title}."
    if r.source:
        s += f" {r.source}."
    return s


if mode == "download":
    ids = [n["oa_id"] for n in notes if n.get("include", True)][:32] if notes else [c["oa_id"] for c in cands[:30]]
    ids = [i for i in ids if i in M.index]
    # top up with further high-ranked candidates that record an open PDF location, so that about 30 core papers are attempted
    extra = [c['oa_id'] for c in cands if c['oa_id'] in M.index and c['oa_id'] not in ids and (M.loc[c['oa_id']].best_pdf_url or M.loc[c['oa_id']].s2_pdf_url or M.loc[c['oa_id']].all_pdf_urls)]
    ids = ids + extra[:40]
    sess = requests.Session()
    sess.headers["User-Agent"] = C.UA
    total = sum(os.path.getsize(os.path.join(PDF, f)) for f in os.listdir(PDF) if f.lower().endswith(".pdf"))
    log = []
    for i in ids:
        if sum(1 for l in log if l['status'] in ('downloaded', 'already downloaded')) >= 32:
            break
        r = M.loc[i]
        fn = fname(r)
        dest = os.path.join(PDF, fn)
        if os.path.exists(dest):
            log.append(dict(oa_id=i, title=r.title, doi=r.doi, status="already downloaded", file=fn, url="", bytes=os.path.getsize(dest))); continue
        urls = [u for u in [r.best_pdf_url] + r.all_pdf_urls.split(" | ") + [r.s2_pdf_url] if u]
        for l in [r.best_oa_landing, r.oa_url]:
            m = re.search(r"arxiv\.org/(?:abs|pdf)/([\w.\-/]+?)(?:v\d+)?(?:\.pdf)?$", l or "")
            if m:
                urls.append(f"https://arxiv.org/pdf/{m.group(1)}")
        if r.oa_url and r.oa_url.lower().endswith(".pdf"):
            urls.append(r.oa_url)
        urls = [u for u in dict.fromkeys(urls) if not BLOCK.search(u)]
        if not urls:
            log.append(dict(oa_id=i, title=r.title, doi=r.doi, status="no open-access PDF location recorded" if not str(r.is_oa).lower() == "true" else "open access but no direct PDF link", file="", url=r.oa_url, bytes=0)); continue
        ok = False
        why = ""
        for u in urls[:5]:
            if total > CAP_TOTAL:
                why = "300 MB cap reached"; break
            try:
                time.sleep(1.0)
                resp = sess.get(u, timeout=60, stream=True, allow_redirects=True)
                if resp.status_code != 200:
                    why = f"HTTP {resp.status_code} at {urlparse(u).netloc}"; continue
                data = b""
                for chunk in resp.iter_content(1 << 16):
                    data += chunk
                    if len(data) > CAP_FILE:
                        break
                if len(data) > CAP_FILE:
                    why = "file larger than 45 MB"; continue
                if not data[:5].startswith(b"%PDF"):
                    why = f"not a PDF (HTML landing page) at {urlparse(u).netloc}"; continue
                with open(dest, "wb") as f:
                    f.write(data)
                total += len(data)
                log.append(dict(oa_id=i, title=r.title, doi=r.doi, status="downloaded", file=fn, url=u, bytes=len(data), oa_status=r.oa_status))
                ok = True
                break
            except Exception as e:
                why = f"{type(e).__name__} at {urlparse(u).netloc}"
        if not ok:
            log.append(dict(oa_id=i, title=r.title, doi=r.doi, status="FAILED: " + why, file="", url=urls[0], bytes=0, oa_status=r.oa_status))
        print(log[-1]["status"][:60], "|", r.title[:70], flush=True)
    pd.DataFrame(log).to_csv(os.path.join(PDF, "download_log.csv"), index=False, encoding="utf-8-sig")
    print(f"PDFs: {sum(1 for l in log if l['status'] in ('downloaded', 'already downloaded'))}/{len(ids)} core papers; folder size {total/1e6:.1f} MB")

elif mode == "evidence":
    if not notes:
        sys.exit("data/clean/evidence_notes.json is missing")
    have = {f for f in os.listdir(PDF) if f.lower().endswith(".pdf")}
    rows = []
    for k, n in enumerate([n for n in notes if n.get("include", True) and n["oa_id"] in M.index], 1):
        r = M.loc[n["oa_id"]]
        fn = fname(r)
        rows.append(dict(
            rank=k, citation=cite(r), year=int(float(r.year)), doi_or_link=("https://doi.org/" + r.doi) if r.doi else "https://openalex.org/" + n["oa_id"],
            open_access_link=r.oa_url or r.best_pdf_url or "", oa_status=r.oa_status, pdf_in_folder=fn if fn in have else "",
            sub_literature=r.sublit, study_type=n.get("study_type", ""), country_or_setting=n.get("country", ""), data=n.get("data", ""), method=n.get("method", ""),
            main_finding_from_abstract=n.get("finding", ""), read_status=n.get("read_status", "abstract read"), relation_to_seans_paper=n.get("relation", ""),
            local_citations=int(float(r.local_citations)), global_citations_openalex=int(float(r.cited_by_count)), openalex_id=n["oa_id"]))
    pd.DataFrame(rows).to_csv(os.path.join(B, "evidence-table.csv"), index=False, encoding="utf-8-sig")
    print(f"evidence-table.csv: {len(rows)} rows")
