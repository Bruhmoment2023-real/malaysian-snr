"""Download Binance Vision spot 1h klines (monthly zips + daily zips for the current month).
Source: https://data.binance.vision  (terms: github.com/binance/binance-public-data TERMS_AND_CONDITIONS.md:
academic research / personal backtesting permitted; no redistribution of the datasets).
Polite: sequential, 0.3 s between requests, generic User-Agent. Output: raw zips + one parquet per symbol.
Timestamps: milliseconds before 2025-01-01, microseconds from 2025-01-01 (normalised here).
"""
import sys, io, time, zipfile, datetime as dt
from pathlib import Path
import requests, pandas as pd
ROOT = Path(r"D:/Research-Publishing/02-malaysian-snr/rework-v3/data")
ZIPS = ROOT / "binance_zips"; OUT = ROOT / "parquet"
UA = {"User-Agent": "academic-research-client/1.0"}
INTERVAL = sys.argv[1] if len(sys.argv) > 1 else "1h"
SYMS = sys.argv[2:] or ["BTCUSDT","ETHUSDT","SOLUSDT","PAXGUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
        "LTCUSDT","LINKUSDT","TRXUSDT","DOTUSDT","AVAXUSDT","BCHUSDT"]
BASE = "https://data.binance.vision/data/spot"
def get(url, dest):
    if dest.exists() and dest.stat().st_size > 0: return True
    for a in range(5):
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code == 404: return False
        if r.status_code == 200:
            dest.write_bytes(r.content); time.sleep(0.3); return True
        time.sleep(5 * (a + 1))
    raise RuntimeError(url)
def read_zip(p):
    with zipfile.ZipFile(p) as z:
        df = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=range(6),
                         names=["t","open","high","low","close","volume"])
    t = df.t.astype("int64")
    unit = "us" if t.iloc[0] > 10**14 else "ms"
    df.index = pd.to_datetime(t, unit=unit, utc=True)
    return df.drop(columns="t").astype(float)
today = dt.datetime.now(dt.timezone.utc).date()
for s in SYMS:
    d = ZIPS / INTERVAL / s; d.mkdir(parents=True, exist_ok=True)
    frames = []; y, m = 2017, 8; n_ok = 0
    while (y, m) < (today.year, today.month):
        f = d / f"{s}-{INTERVAL}-{y}-{m:02d}.zip"
        if get(f"{BASE}/monthly/klines/{s}/{INTERVAL}/{f.name}", f):
            frames.append(read_zip(f)); n_ok += 1
        elif f.exists(): f.unlink()
        m += 1
        if m == 13: y, m = y + 1, 1
    # daily files for the current month (up to yesterday)
    day = dt.date(today.year, today.month, 1)
    while day < today:
        f = d / f"{s}-{INTERVAL}-{day.isoformat()}.zip"
        if get(f"{BASE}/daily/klines/{s}/{INTERVAL}/{f.name}", f): frames.append(read_zip(f))
        day += dt.timedelta(days=1)
    df = pd.concat(frames).sort_index(); df = df[~df.index.duplicated()]
    df.to_parquet(OUT / f"{s}_{INTERVAL}.parquet")
    print(s, INTERVAL, "months", n_ok, "rows", len(df), df.index[0], df.index[-1], flush=True)
