"""Shared helpers for the literature-mapping kit (papers 04-07).

- Every HTTP response is cached in SQLite (D:\\Research-Publishing\\_tools\\biblio-cache\\kit_http_cache.sqlite)
  so nothing is fetched twice. Only 200/404 responses are cached.
- Per-host rate limiting (one global clock per host, shared by all threads).
- OpenAlex: since 2026 keyless list/search calls draw on a tiny shared daily budget per IP, but
  single-record lookups (/works/<id>, /works/doi:<doi>, /works/mag:<id>) are free. The kit therefore
  DISCOVERS records through Crossref / Semantic Scholar / ERIC / arXiv and ENRICHES them through
  OpenAlex single-record lookups.
"""
import hashlib, json, os, re, sqlite3, sys, threading, time, unicodedata, zlib, gzip
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import requests

MAILTO = "research-contact-withheld@example.invalid"
UA = "LiteratureMap/1.1 (open-data literature review; no personal identifiers)"
CACHE_DIR = r"D:\Research-Publishing\_tools\biblio-cache"
CACHE_DB = os.path.join(CACHE_DIR, "kit_http_cache.sqlite")

HOST_INTERVAL = {
    "api.openalex.org": 0.115,
    "api.crossref.org": 0.2,
    "api.semanticscholar.org": 1.2,
    "api.ies.ed.gov": 0.4,
    "export.arxiv.org": 3.1,
    "api.opencitations.net": 0.4,
    "ideas.repec.org": 2.5,
}
_host_next = {}
_host_lock = threading.Lock()
_lock = threading.Lock()
_conn = None
_tl = threading.local()
API_LOG = []          # (host, url, status, note) for failures


def _db():
    global _conn
    if _conn is None:
        if not os.path.exists("D:\\"):
            sys.exit("D: is missing - stopping (nothing is written to C:).")
        os.makedirs(CACHE_DIR, exist_ok=True)
        _conn = sqlite3.connect(CACHE_DB, check_same_thread=False, timeout=120)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA synchronous=NORMAL")
        _conn.execute("CREATE TABLE IF NOT EXISTS http (k TEXT PRIMARY KEY, url TEXT, status INT, body BLOB, ts REAL)")
        _conn.commit()
    return _conn


def _session():
    if not hasattr(_tl, "s"):
        _tl.s = requests.Session()
        _tl.s.headers["User-Agent"] = UA
    return _tl.s


def _throttle(host):
    iv = HOST_INTERVAL.get(host, 0.5)
    with _host_lock:
        now = time.time()
        t = max(now, _host_next.get(host, 0))
        _host_next[host] = t + iv
    if t > now:
        time.sleep(t - now)


def cache_get(key):
    with _lock:
        r = _db().execute("SELECT status, body FROM http WHERE k=?", (key,)).fetchone()
    if r is None:
        return None
    return r[0], zlib.decompress(r[1]).decode("utf-8", "replace")


def cache_put(key, url, status, text):
    with _lock:
        _db().execute("INSERT OR REPLACE INTO http VALUES (?,?,?,?,?)",
                      (key, url, status, zlib.compress(text.encode("utf-8")), time.time()))
        _db().commit()


def fetch(url, method="GET", body=None, retries=5, ok_status=(200, 404), headers=None, timeout=60, use_cache=True):
    """Cached, throttled fetch. Returns (status, text). status 0 = network failure."""
    key = hashlib.sha1((method + url + (json.dumps(body, sort_keys=True) if body else "")).encode()).hexdigest()
    if use_cache:
        hit = cache_get(key)
        if hit is not None:
            return hit
    url = re.sub(r"[&?]mailto=[^&]*", "", url)   # never send a personal identifier (key was computed above, so old cache hits still work)
    host = urlparse(url).netloc
    delay = 3.0
    last = (0, "")
    for attempt in range(retries):
        try:
            _throttle(host)
            if method == "GET":
                r = _session().get(url, timeout=timeout, headers=headers)
            else:
                r = _session().post(url, json=body, timeout=timeout, headers=headers)
            last = (r.status_code, r.text)
            if r.status_code in ok_status:
                cache_put(key, url, r.status_code, r.text)
                return last
            if r.status_code in (429, 500, 502, 503, 504):
                ra = r.headers.get("Retry-After", "")
                if ra.isdigit() and float(ra) > 600:      # daily budget exhausted: do not hammer
                    API_LOG.append((host, url[:200], r.status_code, "daily budget exhausted; not retried"))
                    return last
                if "Insufficient budget" in r.text:
                    API_LOG.append((host, url[:200], r.status_code, "OpenAlex keyless daily budget exhausted"))
                    return last
                time.sleep(float(ra) if ra.isdigit() else delay)
                delay = min(delay * 2, 45)
                continue
            API_LOG.append((host, url[:200], r.status_code, r.text[:120]))
            return last
        except requests.RequestException as e:
            last = (0, str(e))
            time.sleep(delay)
            delay = min(delay * 2, 45)
    API_LOG.append((host, url[:200], last[0], "failed after retries: " + last[1][:120]))
    return last


def fetch_json(url, **kw):
    st, tx = fetch(url, **kw)
    if st != 200:
        return None
    try:
        return json.loads(tx)
    except Exception:
        return None


OA_SELECT_FULL = ("id,doi,title,display_name,publication_year,publication_date,language,type,authorships,"
                  "primary_location,best_oa_location,open_access,cited_by_count,counts_by_year,biblio,is_retracted,"
                  "is_paratext,primary_topic,topics,keywords,concepts,referenced_works,abstract_inverted_index,ids,"
                  "fwci,corresponding_author_ids,corresponding_institution_ids,locations,referenced_works_count")
OA_SELECT_REF = "id,doi,display_name,publication_year,type,authorships,primary_location,biblio,cited_by_count"


def oa_single(ident, select=OA_SELECT_FULL):
    """ident: 'W123', 'doi:10.x/y', 'mag:123'. Returns dict or None. Free (0 credits)."""
    from urllib.parse import quote
    url = f"https://api.openalex.org/works/{quote(ident, safe=':/.-_()')}?select={select}&mailto={MAILTO}"
    return fetch_json(url)


def pmap(fn, items, workers=5, label="", every=400):
    out = [None] * len(items)
    t0 = time.time()
    done = [0]

    def run(i):
        try:
            out[i] = fn(items[i])
        except Exception as e:           # never let one record kill a run
            out[i] = None
            API_LOG.append(("pmap", str(items[i])[:120], -1, repr(e)[:150]))
        done[0] += 1
        if every and done[0] % every == 0:
            print(f"  {label} {done[0]}/{len(items)} ({time.time()-t0:.0f}s)", flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(run, range(len(items))))
    return out


def abstract_from_inverted(inv):
    if not inv:
        return ""
    pos = []
    for w, idxs in inv.items():
        for i in idxs:
            pos.append((i, w))
    pos.sort()
    return " ".join(w for _, w in pos)


def norm_doi(d):
    if not d:
        return ""
    d = str(d).strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d


def norm_title(t):
    if not t:
        return ""
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode()
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def strip_tags(t):
    if not t:
        return ""
    t = re.sub(r"<[^>]+>", " ", str(t))
    return re.sub(r"\s+", " ", t).strip()


def ascii_up(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).upper().strip()


def wid(x):
    return x.rsplit("/", 1)[-1] if x else ""


def jdump(obj, path, indent=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)


def jload(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def jsonl_gz_write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def jsonl_gz_read(path):
    if not os.path.exists(path):
        return []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def save_api_log(path):
    old = jload(path, []) or []
    old.extend([{"host": h, "url": u, "status": s, "note": n, "ts": time.strftime("%Y-%m-%d %H:%M:%S")} for h, u, s, n in API_LOG])
    jdump(old, path, indent=1)
    API_LOG.clear()


