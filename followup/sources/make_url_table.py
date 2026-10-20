"""Build the per-URL table of sources-archive.md from manifest.json (live fetch, SHA-256, Wayback availability, Save Page Now). Writes url_table.md."""
import json
from pathlib import Path
OUT = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/sources")
man = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
rows = []
dead = []
for key, r in man.items():
    n = r["n"]; url = r["url"]
    live = [f for f in r["files"] if f["file"].split("/")[-1].startswith("live.")]
    html = next((f for f in live if f["file"].endswith((".html", ".pdf"))), None)
    txt = next((f for f in live if f["file"].endswith(".txt")), None)
    sha = (html["sha256"][:16] + "..") if html else "-"
    status = r.get("live_status", "?")
    cdx = r.get("wayback_cdx", {}) or {}
    ex = r.get("wayback_existing_capture")
    spn = r.get("spn")
    if ex:
        wb = f"capture exists: {ex}"
    elif spn:
        rc = (spn.get("recheck_cdx") or {})
        if spn.get("status") == 200 and rc.get("last"):
            wb = f"none before; Save Page Now requested, now: https://web.archive.org/web/{rc['last']}/{url}"
        else:
            wb = f"none before; Save Page Now requested, HTTP {spn.get('status', spn.get('error'))}; re-check CDX last={rc.get('last')}"
    elif r.get("wayback_done"):
        wb = "none found (availability API and CDX); Save Page Now not yet requested"
    else:
        wb = "Wayback check not completed"
    extra = ""
    yt = r.get("youtube")
    if yt:
        extra = f"video metadata: title={yt.get('title')!r}, channel={yt.get('channel')!r}, published={yt.get('publish_date')}, transcript: {yt.get('transcript', yt.get('note'))}"
    elif r.get("oembed") and r["oembed"].get("status") == 200:
        d = r["oembed"]["data"]; extra = f"oEmbed metadata: title={d.get('title')!r}, author={d.get('author_name')!r}"
    elif r.get("oembed"):
        extra = f"oEmbed: HTTP {r['oembed'].get('status', r['oembed'].get('error'))}"
    if any(x in status for x in ("DEAD", "BLOCKED", "ERROR")):
        dead.append((n, url, status))
    rows.append((n, url, r["accessed_utc"], status, sha, wb, extra, r.get("text_chars", "")))
lines = ["| # | URL | Accessed (UTC) | Live fetch | SHA-256 of saved page (first 16 hex) | Internet Archive | Notes |", "|---|---|---|---|---|---|---|"]
for n, url, acc, st, sha, wb, extra, tc in rows:
    lines.append(f"| {n} | {url} | {acc} | {st} | {sha} | {wb} | {extra} |")
(OUT / "url_table.md").write_text("\n".join(lines), encoding="utf-8")
(OUT / "dead_links.txt").write_text("\n".join(f"{n}\t{u}\t{s}" for n, u, s in dead), encoding="utf-8")
print(len(rows), "rows;", len(dead), "dead/blocked/errored")
for d in dead:
    print(d)
