"""Audit look-ahead test for the phase-1 engine (the original report says a truncation test passed but no test script
or log is stored). Idea: a causal signal at bar j must not change when all data after bar j is deleted.
For each asset/timeframe and several cut points, signals/levels/storyline are computed on the full series and on the
series truncated at the cut, and compared on every bar that is complete in both.
Imports D:/Malaysian-SNR/backtest/msnr.py READ-ONLY (run with -B and NUMBA_CACHE_DIR pointing away from that folder).
Run (about 2-4 min, mostly numba compilation):
  set NUMBA_CACHE_DIR=D:\\Research-Publishing\\02-malaysian-snr\\.numba_cache
  D:\\Malaysian-SNR\\.venv\\Scripts\\python.exe -B D:\\Research-Publishing\\02-malaysian-snr\\code\\06_truncation_lookahead_test.py
"""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd

assert os.path.exists("D:/") and os.environ.get("NUMBA_CACHE_DIR"), "set NUMBA_CACHE_DIR to the project folder first"
sys.path.insert(0, r"D:/Malaysian-SNR/backtest")
import msnr

OUT = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/rerun/results")
TFS = {"1h": "4h", "4h": "1d", "1d": "1w"}


def build(d1, tf, htf, metals):
    bars = msnr.make_bars(d1, tf, metals); hb = msnr.make_bars(d1, htf, metals)
    o, h, l, c = (bars[k].to_numpy() for k in ("open", "high", "low", "close"))
    st = msnr.storyline(hb)
    hi = np.searchsorted(hb.end.to_numpy(), bars.end.to_numpy(), side="right") - 1
    story = np.where(hi >= 0, st[np.clip(hi, 0, None)], 0)
    ev = msnr.map_events_to_bars(msnr.level_events(bars), bars)
    s0, s1, _, _, nr, ns = msnr.run_levels(o, h, l, c, *ev)
    evr = msnr.map_events_to_bars(msnr.level_events(bars, include_qm=False, av_mode="raw"), bars)
    sR = msnr.run_levels(o, h, l, c, *evr, 99)[0]
    evh = msnr.map_events_to_bars(msnr.level_events(hb, include_qm=False), bars)
    sH = msnr.run_levels(o, h, l, c, *evh)[0]
    return pd.DataFrame(dict(end=bars.end.to_numpy(), story=story, sig_pivot=s0, sig_qm=s1, sig_raw=sR, sig_htf=sH,
                             nres=np.nan_to_num(nr, nan=-1.0), nsup=np.nan_to_num(ns, nan=-1.0), atr=np.nan_to_num(msnr.atr(bars), nan=-1.0)), index=bars.index)


rows = []
for asset, fn, metals in (("BTCUSDT", "BTCUSDT_1h.parquet", False), ("SOLUSDT", "SOLUSDT_1h.parquet", False), ("GC=F", "yf_GC_F_1h.parquet", True)):
    d1 = pd.read_parquet(rf"D:/Malaysian-SNR/data/{fn}"); d1.columns = [x.lower() for x in d1.columns]
    d1 = d1[["open", "high", "low", "close"]].copy()
    d1.index = d1.index.tz_localize("UTC") if d1.index.tz is None else d1.index.tz_convert("UTC")
    d1 = d1[~d1.index.duplicated()].sort_index()
    for tf, htf in TFS.items():
        full = build(d1, tf, htf, metals)
        for frac in (0.35, 0.6, 0.85):
            cut = d1.index[int(len(d1) * frac)]
            part = build(d1[d1.index < cut], tf, htf, metals)
            # bars complete in the truncated set: every bar except its last one (which may be partial)
            idx = part.index[:-1]; a = full.loc[idx]; b = part.loc[idx]
            for col in ("story", "sig_pivot", "sig_qm", "sig_raw", "sig_htf", "nres", "nsup", "atr"):
                bad = int((np.abs(a[col].to_numpy(float) - b[col].to_numpy(float)) > 1e-9).sum())
                rows.append(dict(asset=asset, tf=tf, cut_frac=frac, series=col, bars_compared=len(idx), mismatches=bad))
        print(asset, tf, "done", flush=True)
R = pd.DataFrame(rows); R.to_csv(OUT / "check_phase1_truncation_test.csv", index=False)
print(R.groupby("series").agg(checks=("mismatches", "size"), bars=("bars_compared", "sum"), mismatches=("mismatches", "sum")))
print("TOTAL mismatches:", int(R.mismatches.sum()), "in", len(R), "checks")
print(R[R.mismatches > 0].to_string(index=False))
