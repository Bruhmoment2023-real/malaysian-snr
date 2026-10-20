"""Prevalence of the pivot-overwrite look-ahead in msnr.storyline (see causal_ref.py) over the price series used by phases 1, 2 and 3.
For every series: share of bars where the SHIPPED storyline differs from the strictly causal one (this equals a truncation test at EVERY cut point, which the
3-cut tests of code/06 and 07/08 cannot be). Then the same share after mapping onto the entry-timeframe bars the way each pipeline does it.
Usage: python -B 10_storyline_overwrite_check.py   (NUMBA_CACHE_DIR must be set)"""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead")
assert os.path.exists("D:/") and os.environ.get("NUMBA_CACHE_DIR")
sys.path.insert(0, str(HERE / "code_copy")); sys.path.insert(0, str(HERE))
import p2common as P, p3common as C, msnr
from causal_ref import storyline_causal
rows = []

def cmp(series, name, c_df, tf_bars=None, htf_bars=None):
    s = msnr.storyline(c_df); k = storyline_causal(c_df)
    r = dict(phase=series[0], cell=series[1], series=name, bars=len(s), differing=int((s != k).sum()))
    r["share_differing"] = r["differing"] / len(s)
    if tf_bars is not None:           # map to entry bars as the pipeline does (last HTF bar whose end <= entry bar end)
        hi = np.searchsorted(c_df.end.to_numpy(), tf_bars.end.to_numpy(), side="right") - 1
        ms = np.where(hi >= 0, s[np.clip(hi, 0, None)], 0); mk = np.where(hi >= 0, k[np.clip(hi, 0, None)], 0)
        r["entry_bars"] = len(ms); r["entry_bars_differing"] = int((ms != mk).sum())
        r["entry_share_differing"] = r["entry_bars_differing"] / len(ms)
        r["entry_bars_sign_flipped"] = int(((ms != mk) & (ms != 0) & (mk != 0)).sum())
    rows.append(r)

# ---- phase 1 (the three assets of code/06, 1h source, same TFS), full history
sys.path.insert(0, r"D:/Malaysian-SNR/backtest")
import importlib.util
spec = importlib.util.spec_from_file_location("msnr_p1", r"D:/Malaysian-SNR/backtest/msnr.py")   # read-only import of the ORIGINAL phase-1 file
p1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p1)
for asset, fn, metals in (("BTCUSDT", "BTCUSDT_1h.parquet", False), ("SOLUSDT", "SOLUSDT_1h.parquet", False), ("GC=F", "yf_GC_F_1h.parquet", True)):
    d1 = pd.read_parquet(rf"D:/Malaysian-SNR/data/{fn}"); d1.columns = [x.lower() for x in d1.columns]; d1 = d1[["open", "high", "low", "close"]].copy()
    d1.index = d1.index.tz_localize("UTC") if d1.index.tz is None else d1.index.tz_convert("UTC"); d1 = d1[~d1.index.duplicated()].sort_index()
    for tf, htf in {"1h": "4h", "4h": "1d", "1d": "1w"}.items():
        bars = p1.make_bars(d1, tf, metals); hb = p1.make_bars(d1, htf, metals)
        s = p1.storyline(hb); k = storyline_causal(hb)
        hi = np.searchsorted(hb.end.to_numpy(), bars.end.to_numpy(), side="right") - 1
        ms = np.where(hi >= 0, s[np.clip(hi, 0, None)], 0); mk = np.where(hi >= 0, k[np.clip(hi, 0, None)], 0)
        rows.append(dict(phase="1", cell=f"{asset} {tf}", series=f"storyline of {htf} bars", bars=len(s), differing=int((s != k).sum()), share_differing=float((s != k).mean()),
                         entry_bars=len(ms), entry_bars_differing=int((ms != mk).sum()), entry_share_differing=float((ms != mk).mean()), entry_bars_sign_flipped=int(((ms != mk) & (ms != 0) & (mk != 0)).sum())))
        print("P1", asset, tf, rows[-1]["entry_bars_differing"], flush=True)
# ---- phase 2: 20 cells
for asset, tf in P.CELLS:
    src, base = P.load_src(asset, tf); metals = P.ASSETS[asset]["cost"]["metals"]
    bars = P.make_bars_v(src, tf, metals, base); hb = P.make_bars_v(src, P.HTF[tf], metals, base)
    cmp(("2", f"{asset} {tf}"), f"storyline of {P.HTF[tf]} bars", hb, tf_bars=bars)
    print("P2", asset, tf, rows[-1]["entry_bars_differing"], flush=True)
# ---- phase 3: story_simple = storyline(T1 bars) mapped to T4 (5 real assets + MCX proxy x 3 ladders)
for asset in C.ASSETS:
    base = C.load_base(asset); sh = C.ASSETS[asset]["shift_h"]
    for ladder, (T1, T2, T3, T4) in C.LADDERS.items():
        b1 = C.bars(base, T1, sh); b4 = C.bars(base, T4, sh)
        cmp(("3", f"{asset} {ladder}"), f"storyline of {T1} bars", b1, tf_bars=b4)
        print("P3", asset, ladder, rows[-1]["entry_bars_differing"], flush=True)
    del base
R = pd.DataFrame(rows); R.to_csv(HERE / "check_storyline_overwrite_prevalence.csv", index=False)
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)
print(R.to_string(index=False))
g = R.groupby("phase").agg(series=("cell", "size"), series_with_any=("differing", lambda x: int((x > 0).sum())), htf_bars=("bars", "sum"), htf_differing=("differing", "sum"),
                           entry_bars=("entry_bars", "sum"), entry_differing=("entry_bars_differing", "sum"), entry_sign_flipped=("entry_bars_sign_flipped", "sum"))
g["entry_share"] = g.entry_differing / g.entry_bars; print(g)
