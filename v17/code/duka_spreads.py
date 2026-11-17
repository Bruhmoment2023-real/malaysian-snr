"""Spread calibration and clock check from the Dukascopy sample months (June 2010-2026): median hourly bid-ask spread in USD per ounce
(ask open minus bid open of each hourly candle with volume), and the lag (in hours) at which Dukascopy bid hourly returns best match the histdata 1h bars
(checks the histdata time convention). Raw Dukascopy files are used locally only."""
import lzma, struct
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(r"D:/Research-Publishing/02-malaysian-snr/rework-v3")
rows, lagrows = [], []
def load(a, side, y):
    f = ROOT / "data/duka_raw" / a / f"{side}_{y}_05.bi5"
    if not f.exists() or f.stat().st_size == 0: return None
    raw = lzma.decompress(f.read_bytes())
    r = [struct.unpack(">5if", raw[i:i + 24]) for i in range(0, len(raw), 24)]
    df = pd.DataFrame(r, columns=["sec", "open", "close", "low", "high", "vol"])
    df.index = pd.Timestamp(year=y, month=6, day=1, tz="UTC") + pd.to_timedelta(df.sec, unit="s")
    df[["open", "close", "low", "high"]] /= 1000.0
    return df
for a in ("XAUUSD", "XAGUSD"):
    hd = pd.read_parquet(ROOT / f"data/parquet/{a}_hd_1h.parquet")
    for y in range(2010, 2027):
        b, k = load(a, "BID", y), load(a, "ASK", y)
        if b is None or k is None: continue
        j = b.join(k, lsuffix="_b", rsuffix="_a", how="inner"); j = j[(j.vol_b > 0) & (j.vol_a > 0)]
        sp = (j.open_a - j.open_b)
        sp = sp[(sp > 0) & (sp < sp.median() * 10)]
        rows.append(dict(asset=a, year=y, median_usd=float(sp.median()), p25=float(sp.quantile(.25)), p75=float(sp.quantile(.75)), n=len(sp),
                         median_bps=float((sp / j.open_b.loc[sp.index]).median() * 1e4)))
        # clock check: correlation of hourly close-to-close returns, Dukascopy bid vs histdata, at lags -2..2 h
        rb = b.close.pct_change().dropna()
        rh = hd.close.pct_change().dropna()
        best = {}
        for lag in range(-3, 4):
            x = rh.copy(); x.index = x.index + pd.Timedelta(hours=lag)
            jj = pd.concat([rb.rename("d"), x.rename("h")], axis=1, join="inner").dropna()
            best[lag] = jj.corr().iloc[0, 1] if len(jj) > 100 else np.nan
        lagrows.append(dict(asset=a, year=y, best_lag_h=max(best, key=lambda z: (-1 if np.isnan(best[z]) else best[z])), corr_best=max(v for v in best.values() if not np.isnan(v)), corr_lag0=best[0]))
sp = pd.DataFrame(rows); sp["used"] = ((sp.p75 - sp.p25) / sp.median_usd) <= 0.8   # drop samples with very dispersed spreads (thin or interrupted quotes)
sp.to_csv(ROOT / "results/duka_spread_by_year.csv", index=False)
pd.DataFrame(lagrows).to_csv(ROOT / "results/histdata_vs_duka_clock_check.csv", index=False)
print(pd.DataFrame(rows).round(4).to_string()); print(pd.DataFrame(lagrows).round(3).to_string())
