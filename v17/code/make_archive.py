"""Build the local archive (code, frozen-engine checksum, results CSVs, download scripts, file checksums). NO vendor data (Binance, histdata, Dukascopy bars or zips) is copied. Not pushed anywhere."""
import hashlib, shutil, csv
from pathlib import Path
R = Path(r"D:/Research-Publishing/02-malaysian-snr/rework-v3"); A = Path(r"D:/Research-Publishing/02-malaysian-snr/archive-v17")
if A.exists(): shutil.rmtree(A)
(A / "code").mkdir(parents=True); (A / "results").mkdir(); (A / "figures").mkdir(); (A / "manifests").mkdir()
for f in (R / "code").glob("*"):
    if f.is_file() and f.suffix in (".py", ".sh", ".ps1"): shutil.copy(f, A / "code" / f.name)
for f in R.glob("*.md"): shutil.copy(f, A / f.name)
for f in (R / "results").glob("*"):
    if f.is_file() and f.suffix in (".csv", ".json", ".txt"): shutil.copy(f, A / "results" / f.name)
(A / "results" / "cells").mkdir()
for f in (R / "results" / "cells").glob("*.csv"): shutil.copy(f, A / "results" / "cells" / f.name)     # aggregate per-cell tables only; no trade-level price files
for f in (R / "figures").glob("*"): shutil.copy(f, A / "figures" / f.name)
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def manifest(name, files, urlf):
    with open(A / "manifests" / name, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["file", "bytes", "sha256", "source_url"])
        for f in sorted(files): w.writerow([f.name, f.stat().st_size, sha(f), urlf(f)])
bz = [f for f in (R / "data/binance_zips").rglob("*.zip")]
def burl(f):
    p = f.name.split("-"); sym = p[0]; itv = p[1]; per = "-".join(p[2:]).replace(".zip", "")
    kind = "daily" if len(per) == 10 else "monthly"
    return f"https://data.binance.vision/data/spot/{kind}/klines/{sym}/{itv}/{f.name}"
manifest("binance_vision_zips_sha256.csv", bz, burl)
dz = [f for f in (R / "data/duka_raw").rglob("*.bi5") if f.stat().st_size > 0 and "_05" in f.name]
manifest("dukascopy_sample_months_sha256.csv", dz, lambda f: f"https://datafeed.dukascopy.com/datafeed/{f.parent.name}/{f.name.split('_')[1]}/{f.name.split('_')[2][:2]}/{f.name.split('_')[0]}_candles_hour_1.bi5")
hz = [f for f in Path(r"D:/Malaysian-SNR/phase3/data/histdata_zips").glob("*.zip") if f.name.startswith(("XAUUSD", "XAGUSD"))]
manifest("histdata_zips_sha256.csv", hz, lambda f: "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/" + f.name[:6].lower() + "/" + f.name.split("_")[1][:4])
with open(A / "ENGINE_CHECKSUM.txt", "w") as fh:
    fh.write(f"msnr_frozen.py sha256 {sha(R / 'code/msnr_frozen.py')}\n(identical to D:/Malaysian-SNR/backtest/msnr.py of the earlier version)\n")
(A / "README.md").write_text("""# Archive v17: Malaysian SnR test (local copy, not pushed)

Contents: code/ (frozen engine msnr_frozen.py, downloaders, runners, analysis, figures, manuscript builders), PLAN_2026-11-17.md (time-stamped pre-specification and labelled amendments), results/ (CSV tables and logs), figures/ (600 dpi PNG and PDF), manifests/ (file names, byte sizes, SHA-256 and source URLs of every vendor file used), ENGINE_CHECKSUM.txt.

NOT included, on purpose: any vendor price data (Binance Vision klines, histdata.com bars, Dukascopy candles) and the trade-level files derived from them. Terms: Binance Vision (github.com/binance/binance-public-data TERMS_AND_CONDITIONS.md) allows academic research and personal back-testing and prohibits hosting or redistributing the datasets; no licence text was found for the Dukascopy feed and histdata.com data, so they are treated the same way.

Reproduction: (1) python code/dl_binance_vision.py 1h and 5m (checks sizes and checksums against manifests/binance_vision_zips_sha256.csv); (2) metals: download the histdata.com XAUUSD and XAGUSD M1 files listed in manifests/histdata_zips_sha256.csv, aggregate with the M1 loader of the earlier version, then code/make_metals.py; (3) code/run_batch.sh, run_metals.sh, run_b3.py per asset, rewalk5m.py per crypto asset; (4) code/final_run.sh. Paths in the scripts are the author's D: paths and must be edited. Seeds are fixed in code.
""", encoding="utf-8")
print("archive done", sum(1 for _ in A.rglob("*") if _.is_file()), "files")
