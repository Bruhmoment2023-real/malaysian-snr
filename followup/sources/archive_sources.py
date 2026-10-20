"""Archive every URL listed in D:/Malaysian-SNR/research/MSNR-rules-and-sources.md (read-only).

Phase "fetch": one plain GET per URL with a single honest User-Agent (no retries with other identities, no cookies,
no login). Saves raw bytes + extracted text + metadata, SHA-256 of each file, UTC access time. Then asks the Internet
Archive availability API for an existing capture and, if one exists, saves that capture's raw content too.
Phase "spn": for URLs with no capture, request one via the public Save Page Now endpoint (GET web.archive.org/save/<url>),
then re-check availability.
Writes only under followup/sources/.
Usage: python -I -B archive_sources.py fetch | spn
"""
import hashlib, json, re, sys, time, html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse
import requests
from bs4 import BeautifulSoup

SRC_MD = Path(r"D:/Malaysian-SNR/research/MSNR-rules-and-sources.md")
OUT = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/sources")
SNAP = OUT / "snapshots"
UA = "Mozilla/5.0 (compatible; MSNR-source-archiver/1.0; one-off academic citation archiving; python-requests)"
H = {"User-Agent": UA, "Accept-Language": "en;q=0.9,ms;q=0.8,id;q=0.7"}
MAN = OUT / "manifest.json"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def save(p, b):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)
    return dict(file=str(p.relative_to(OUT)).replace("\\", "/"), bytes=len(b), sha256=sha(b))


def urls_from_md():
    t = SRC_MD.read_text(encoding="utf-8")
    seen, out = set(), []
    for m in re.finditer(r"https?://[^\s<>\")\]]+", t):
        u = m.group(0).rstrip(".,;:*")
        line = t.count("\n", 0, m.start()) + 1
        if u not in seen:
            seen.add(u); out.append((u, line))
    return out


def slug(i, u):
    p = urlparse(u)
    s = re.sub(r"[^A-Za-z0-9]+", "-", (p.netloc.replace("www.", "") + p.path))[:70].strip("-")
    return f"{i:02d}-{s}"


def extract(b, ctype):
    """Return (text, meta) from an HTML byte string."""
    soup = BeautifulSoup(b, "lxml")
    meta = {}
    if soup.title and soup.title.string:
        meta["title"] = soup.title.string.strip()
    for tag in soup.find_all("meta"):
        k = tag.get("property") or tag.get("name") or tag.get("itemprop")
        v = tag.get("content")
        if k and v and k.lower() in ("description", "og:title", "og:description", "og:site_name", "author", "article:published_time",
                                     "article:modified_time", "datepublished", "uploaddate", "og:url", "og:video:tag", "keywords", "interactioncount"):
            meta.setdefault(k.lower(), v.strip()[:5000])
    lds = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            lds.append(json.loads(s.string or ""))
        except Exception:
            pass
    if lds:
        meta["json_ld"] = lds
    raw = b.decode("utf-8", errors="replace")
    for s in soup(["script", "style", "noscript", "svg"]):
        s.decompose()
    text = soup.get_text("\n")
    text = "\n".join(l.strip() for l in text.splitlines() if l.strip())
    return text, meta, raw


def youtube_extra(raw, d, rec):
    """Pull title/channel/date/description from the public watch-page JSON; try a public caption track without login."""
    yt = {}
    m = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;\s*(?:var\s|</script>)", raw, re.S)
    if m:
        try:
            pr = json.loads(m.group(1))
            vd = pr.get("videoDetails", {}); mf = pr.get("microformat", {}).get("playerMicroformatRenderer", {})
            yt = dict(title=vd.get("title"), channel=vd.get("author"), channel_id=vd.get("channelId"), length_seconds=vd.get("lengthSeconds"),
                      view_count=vd.get("viewCount"), description=vd.get("shortDescription"), publish_date=mf.get("publishDate"),
                      upload_date=mf.get("uploadDate"), category=mf.get("category"),
                      playability=pr.get("playabilityStatus", {}).get("status"), playability_reason=pr.get("playabilityStatus", {}).get("reason"))
            tracks = pr.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
            yt["caption_tracks_listed"] = [dict(lang=t.get("languageCode"), kind=t.get("kind", "manual"), name=(t.get("name", {}).get("simpleText"))) for t in tracks]
            if tracks:
                t0 = next((t for t in tracks if t.get("languageCode", "").startswith("en")), tracks[0])
                try:
                    r = requests.get(t0["baseUrl"], headers=H, timeout=40)
                    body = r.content
                    yt["transcript_http_status"] = r.status_code
                    if r.status_code == 200 and len(body) > 200:
                        rec["files"].append(save(d / "transcript.xml", body))
                        lines = [html.unescape(html.unescape(x)) for x in re.findall(r"<(?:text|p)[^>]*>(.*?)</(?:text|p)>", body.decode("utf-8", "replace"), re.S)]
                        lines = [re.sub(r"<[^>]+>", "", x).strip() for x in lines]
                        rec["files"].append(save(d / "transcript.txt", "\n".join(x for x in lines if x).encode("utf-8")))
                        yt["transcript"] = f"saved ({t0.get('languageCode')}, {t0.get('kind', 'manual')}, {len(lines)} lines)"
                    else:
                        yt["transcript"] = f"NOT available without login/token: caption track listed but the public timedtext URL returned HTTP {r.status_code} with {len(body)} bytes"
                except Exception as e:
                    yt["transcript"] = f"NOT retrieved: {type(e).__name__}: {e}"
            else:
                yt["transcript"] = "no caption track listed in the public page data"
        except Exception as e:
            yt["parse_error"] = f"{type(e).__name__}: {e}"
    else:
        yt["note"] = "ytInitialPlayerResponse not found in the page returned"
    return yt


def oembed(u):
    host = urlparse(u).netloc
    ep = None
    if "youtube.com" in host or "youtu.be" in host:
        ep = "https://www.youtube.com/oembed?format=json&url=" + quote(u, safe="")
    elif "tiktok.com" in host:
        ep = "https://www.tiktok.com/oembed?url=" + quote(u, safe="")
    if not ep:
        return None
    try:
        r = requests.get(ep, headers=H, timeout=40)
        return dict(endpoint=ep, status=r.status_code, data=(r.json() if r.status_code == 200 else r.text[:300]))
    except Exception as e:
        return dict(endpoint=ep, error=f"{type(e).__name__}: {e}")


def polite_get(url, params=None, timeout=90, tries=4, base_sleep=45):
    """GET with respect for rate limits: on 429/5xx wait (Retry-After if given, else growing pause) and try again."""
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, params=params, headers=H, timeout=timeout)
            last = r
            if r.status_code not in (429, 500, 502, 503, 504):
                return r
            ra = r.headers.get("Retry-After")
            wait = int(ra) if ra and ra.isdigit() else base_sleep * (k + 1)
        except Exception as e:
            last = e; wait = base_sleep * (k + 1)
        if k < tries - 1:
            time.sleep(min(wait, 300))
    return last


def wayback_available(u):
    r = polite_get("https://archive.org/wayback/available", params={"url": u}, timeout=60)
    if isinstance(r, Exception):
        return dict(checked=now(), error=f"{type(r).__name__}: {r}")
    try:
        c = r.json().get("archived_snapshots", {}).get("closest")
        return dict(checked=now(), status=r.status_code, closest=c)
    except Exception as e:
        return dict(checked=now(), status=r.status_code, error=f"non-JSON reply: {r.text[:120]!r}")


def cdx(u):
    """First/last capture and count from the public CDX index (collapsed by day, max 2000 rows)."""
    r = polite_get("https://web.archive.org/cdx/search/cdx", params={"url": u, "output": "json", "fl": "timestamp,statuscode,mimetype,length", "collapse": "timestamp:8", "limit": "2000"})
    if isinstance(r, Exception):
        return dict(checked=now(), error=f"{type(r).__name__}: {r}")
    if r.status_code != 200:
        return dict(checked=now(), status=r.status_code)
    try:
        rows = r.json()[1:] if r.text.strip() else []
    except Exception:
        return dict(checked=now(), status=200, error=f"non-JSON reply: {r.text[:120]!r}")
    ok = [x for x in rows if x[1] == "200"]
    return dict(checked=now(), status=200, captures_days=len(rows), captures_200=len(ok), first=rows[0][0] if rows else None, last=rows[-1][0] if rows else None,
                last_200=ok[-1][0] if ok else None)


def classify(status, text, raw, u):
    low = (text or "").lower()[:4000]
    if status is None:
        return "FETCH ERROR"
    if status in (401, 403, 429) or "captcha" in low or "verify you are human" in low or "are you a robot" in low or "access denied" in low or "just a moment" in low:
        return f"BLOCKED (HTTP {status})"
    if status == 404 or status == 410:
        return f"DEAD (HTTP {status})"
    if status >= 400:
        return f"ERROR (HTTP {status})"
    return f"OK (HTTP {status})"


def fetch_all():
    man = json.loads(MAN.read_text(encoding="utf-8")) if MAN.exists() else {}
    for i, (u, line) in enumerate(urls_from_md(), 1):
        key = slug(i, u)
        if key in man and man[key].get("done"):
            continue
        d = SNAP / key
        rec = dict(n=i, url=u, source_md_line=line, accessed_utc=now(), user_agent=UA, files=[])
        try:
            r = requests.get(u, headers=H, timeout=60, allow_redirects=True)
            body = r.content
            ctype = r.headers.get("Content-Type", "")
            rec.update(http_status=r.status_code, final_url=r.url, content_type=ctype, redirects=[h.status_code for h in r.history])
            if "pdf" in ctype.lower() or body[:5] == b"%PDF-":
                rec["files"].append(save(d / "live.pdf", body)); text, meta, raw = "", {}, ""
                rec["kind"] = "pdf"
            else:
                rec["files"].append(save(d / "live.html", body))
                text, meta, raw = extract(body, ctype)
                rec["files"].append(save(d / "live.txt", text.encode("utf-8")))
                rec["kind"] = "html"; rec["text_chars"] = len(text); rec["page_meta"] = meta
                if "youtube.com/watch" in u:
                    rec["youtube"] = youtube_extra(raw, d, rec)
            rec["live_status"] = classify(r.status_code, text, raw, u)
        except Exception as e:
            rec.update(http_status=None, live_status="FETCH ERROR", error=f"{type(e).__name__}: {e}")
        oe = oembed(u)
        if oe:
            rec["oembed"] = oe
        rec["done"] = True
        (d).mkdir(parents=True, exist_ok=True)
        (d / "meta.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        man[key] = rec
        MAN.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{i:02d} {rec['live_status']:<22} chars={rec.get('text_chars', '-'):<7} {u}", flush=True)
        time.sleep(2.0)


def wayback_pass():
    """Slow pass over archive.org: availability API, CDX index, and a copy of the latest good capture."""
    man = json.loads(MAN.read_text(encoding="utf-8"))
    for key, rec in man.items():
        if rec.get("wayback_done"):
            continue
        u = rec["url"]; d = SNAP / key
        rec["files"] = [f for f in rec["files"] if not f["file"].split("/")[-1].startswith("wayback.")]
        rec["wayback_available"] = wayback_available(u)
        time.sleep(15)
        rec["wayback_cdx"] = cdx(u)
        c = rec["wayback_available"].get("closest") or {}
        ts = c.get("timestamp") if c.get("available") else None
        if not ts:
            ts = rec["wayback_cdx"].get("last_200")        # availability API silent/limited: fall back to the CDX index
        rec["wayback_existing_capture"] = (f"https://web.archive.org/web/{ts}/{u}" if ts else None)
        if ts:
            wu = f"https://web.archive.org/web/{ts}id_/{u}"   # id_ = original bytes without the Wayback toolbar
            time.sleep(15)
            w = polite_get(wu, timeout=120)
            if isinstance(w, Exception):
                rec["wayback_copy"] = dict(url=wu, error=f"{type(w).__name__}: {w}")
            else:
                rec["wayback_copy"] = dict(url=wu, status=w.status_code, timestamp=ts, fetched_utc=now())
                if w.status_code == 200:
                    wb = w.content
                    if wb[:5] == b"%PDF-":
                        rec["files"].append(save(d / "wayback.pdf", wb))
                    else:
                        rec["files"].append(save(d / "wayback.html", wb))
                        wt, wmeta, wraw = extract(wb, "")
                        rec["files"].append(save(d / "wayback.txt", wt.encode("utf-8")))
                        rec["wayback_copy"]["text_chars"] = len(wt); rec["wayback_copy"]["title"] = wmeta.get("title")
        ok = ("closest" in rec["wayback_available"]) or (rec["wayback_cdx"].get("status") == 200 and "error" not in rec["wayback_cdx"])
        rec["wayback_done"] = bool(ok)
        (d / "meta.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        MAN.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{rec['n']:02d} avail={rec['wayback_available'].get('status', rec['wayback_available'].get('error'))} cdx={rec['wayback_cdx'].get('status', rec['wayback_cdx'].get('error'))} "
              f"days={rec['wayback_cdx'].get('captures_days')} existing={rec['wayback_existing_capture']}", flush=True)
        time.sleep(15)


def spn():
    man = json.loads(MAN.read_text(encoding="utf-8"))
    for key, rec in man.items():
        if not rec.get("wayback_done") or rec.get("wayback_existing_capture") or rec.get("spn", {}).get("final"):
            continue                                   # only URLs positively shown to have no capture
        u = rec["url"]; s = dict(requested_utc=now(), endpoint="https://web.archive.org/save/" + u)
        try:
            r = requests.get(s["endpoint"], headers=H, timeout=240, allow_redirects=True)
            s.update(status=r.status_code, final_url=r.url, content_location=r.headers.get("Content-Location"), x_archive=r.headers.get("X-Archive-Orig-Date"),
                     body_head=re.sub(r"\s+", " ", BeautifulSoup(r.content[:20000], "lxml").get_text(" "))[:300])
        except Exception as e:
            s["error"] = f"{type(e).__name__}: {e}"
        time.sleep(20)
        s["recheck_cdx"] = cdx(u)
        s["final"] = True
        rec["spn"] = s
        MAN.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
        (SNAP / key / "meta.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{rec['n']:02d} SPN status={s.get('status', s.get('error'))} final_url={s.get('final_url')} recheck_last={s['recheck_cdx'].get('last')}  {u}", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    assert Path("D:/").exists(), "D: offline"
    {"fetch": fetch_all, "wayback": wayback_pass, "spn": spn}[sys.argv[1]]()
