"""Pull the slide text that SlideShare embeds in the HTML of snapshot 22 (public page, no login) into slides.txt next to it."""
import glob, re, json
p = glob.glob(r"D:/Research-Publishing/02-malaysian-snr/followup/sources/snapshots/22-*/live.html")[0]
t = open(p, encoding="utf8", errors="replace").read()
blocks = re.findall(r'"(?:transcript|text|content)"\s*:\s*"((?:[^"\\]|\\.){200,})"', t)
print("candidate blocks", len(blocks))
best = max(blocks, key=len) if blocks else ""
try:
    s = json.loads('"' + best + '"')
except Exception:
    s = best.encode().decode("unicode_escape", errors="replace")
out = p.replace("live.html", "slides.txt")
open(out, "w", encoding="utf8").write(s)
print(out, len(s))
print(s[:5000])
