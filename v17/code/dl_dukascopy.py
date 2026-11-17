"""Download Dukascopy public datafeed 1h BID and ASK candles (monthly bi5 files) for local research only.
Terms: no explicit licence for this feed was found; raw files are NOT redistributed (derived results only).
Polite: sequential, 8 s between requests, 90 s pause on HTTP 503/timeouts. Order: year by year, both metals and both sides.
Usage: dl_dukascopy.py download [SYM ...] | parse [SYM ...]
Format: LZMA records ">5if" = (seconds since month start, open, close, low, high, volume); integer prices scaled by 1000 (metals, JPY).
"""
import sys, lzma, struct, time, datetime as dt
from pathlib import Path
import requests, pandas as pd
ROOT = Path(r"D:/Research-Publishing/02-malaysian-snr/rework-v3/data")
UA = {"User-Agent": "academic-research-client/1.0"}
SPEC = {"XAUUSD": (1000.0, 2010), "XAGUSD": (1000.0, 2010), "EURUSD": (100000.0, 2010), "GBPUSD": (100000.0, 2010),
        "USDJPY": (1000.0, 2010), "AUDUSD": (100000.0, 2010)}
mode = sys.argv[1]; SYMS = sys.argv[2:] or ["XAUUSD", "XAGUSD"]
now = dt.datetime.now(dt.timezone.utc)
def months(y0):
    for y in range(y0, now.year + 1):
        for m0 in range(12):
            if y == now.year and m0 > now.month - 1: return
            yield y, m0
def fetch(sym, side, y, m0):
    f = ROOT / "duka_raw" / sym / f"{side}_{y}_{m0:02d}.bi5"
    f.parent.mkdir(parents=True, exist_ok=True)
    if f.exists(): return
    url = f"https://datafeed.dukascopy.com/datafeed/{sym}/{y}/{m0:02d}/{side}_candles_hour_1.bi5"
    for a in range(30):
        time.sleep(8)
        try:
            r = requests.get(url, headers=UA, timeout=45)
        except Exception:
            time.sleep(90); continue
        if r.status_code in (200, 404):
            f.write_bytes(r.content if r.status_code == 200 else b""); return
        time.sleep(90)
    raise RuntimeError(url)
def parse(sym):
    scale, y0 = SPEC[sym]; parts = {"BID": [], "ASK": []}
    for y, m0 in months(y0):
        for side in ("BID", "ASK"):
            f = ROOT / "duka_raw" / sym / f"{side}_{y}_{m0:02d}.bi5"
            if not f.exists() or f.stat().st_size == 0: continue
            raw = lzma.decompress(f.read_bytes())
            rows = [struct.unpack(">5if", raw[i:i + 24]) for i in range(0, len(raw), 24)]
            df = pd.DataFrame(rows, columns=["sec", "open", "close", "low", "high", "vol"])
            df.index = pd.Timestamp(year=y, month=m0 + 1, day=1, tz="UTC") + pd.to_timedelta(df.sec, unit="s")
            o = df[["open", "high", "low", "close"]].astype(float) / scale; o["vol"] = df.vol
            parts[side].append(o)
    bid = pd.concat(parts["BID"]).sort_index(); ask = pd.concat(parts["ASK"]).sort_index()
    bid = bid[~bid.index.duplicated()]; ask = ask[~ask.index.duplicated()]
    bid = bid[~((bid.vol <= 0) & (bid.high == bid.low))]
    df = bid[["open", "high", "low", "close"]].add_prefix("bid_").join(ask[["open", "high", "low", "close"]].add_prefix("ask_"), how="inner")
    df.to_parquet(ROOT / "parquet" / f"{sym}_duka_1h.parquet")
    print(sym, "rows", len(df), df.index[0], df.index[-1], flush=True)
if mode == "download":
    y0 = min(SPEC[s][1] for s in SYMS)
    for y, m0 in months(y0):
        for sym in SYMS:
            if y < SPEC[sym][1]: continue
            for side in ("BID", "ASK"): fetch(sym, side, y, m0)
        print("done", y, m0 + 1, flush=True)
else:
    for s in SYMS: parse(s)
