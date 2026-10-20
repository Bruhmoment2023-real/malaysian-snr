"""Second attempt at public captions for the two YouTube watch pages whose caption URL was relative (a bug in archive_sources.py: MissingSchema).
Uses only the caption track URL that the public page itself lists; one request per video; no login, no cookies. Updates manifest.json."""
import json, re, html, hashlib, time
from pathlib import Path
import requests
OUT = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/sources")
UA = "Mozilla/5.0 (compatible; MSNR-source-archiver/1.0; one-off academic citation archiving; python-requests)"
man = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
for key, rec in man.items():
    if rec["n"] not in (29, 32):
        continue
    d = OUT / "snapshots" / key
    raw = (d / "live.html").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;\s*(?:var\s|</script>)", raw, re.S)
    pr = json.loads(m.group(1))
    tracks = pr.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    url = tracks[0]["baseUrl"]
    if url.startswith("/"):
        url = "https://www.youtube.com" + url
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    yt = rec["youtube"]
    yt["transcript_http_status_retry"] = r.status_code
    yt["transcript_retry_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if r.status_code == 200 and len(r.content) > 200:
        (d / "transcript.xml").write_bytes(r.content)
        body = r.content.decode("utf-8", "replace")
        lines = [re.sub(r"<[^>]+>", "", html.unescape(html.unescape(x))).strip() for x in re.findall(r"<(?:text|p)[^>]*>(.*?)</(?:text|p)>", body, re.S)]
        txt = "\n".join(x for x in lines if x)
        (d / "transcript.txt").write_text(txt, encoding="utf-8")
        for fn in ("transcript.xml", "transcript.txt"):
            b = (d / fn).read_bytes()
            rec["files"].append(dict(file=f"snapshots/{key}/{fn}", bytes=len(b), sha256=hashlib.sha256(b).hexdigest()))
        yt["transcript"] = f"saved (auto-generated English captions listed on the public page, {len(lines)} lines, no login)"
    else:
        yt["transcript"] = f"NOT available without login: public caption URL returned HTTP {r.status_code} with {len(r.content)} bytes"
    print(rec["n"], yt["transcript"])
    (d / "meta.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    time.sleep(5)
(OUT / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
