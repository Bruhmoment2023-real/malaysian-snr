"""Run the frozen MSNR rule (V0-V4, 1h/4h/1d) on one asset and write cell stats, trades and regime benchmarks.
Usage: python -I run_asset.py ASSET [--legacy-file PATH --tag TAG] [--reps N]
Pre-specified in PLAN_2026-11-17.md (P0-P3, P7)."""
import sys, time, argparse
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/rework-v3/code")
import core, msnr_frozen as msnr

ap = argparse.ArgumentParser()
ap.add_argument("asset"); ap.add_argument("--legacy-file"); ap.add_argument("--tag", default="new")
ap.add_argument("--reps", type=int, default=500); ap.add_argument("--rreps", type=int, default=300)
ap.add_argument("--no-regime", action="store_true")
args = ap.parse_args()
asset = args.asset
OUT = core.ROOT / "results" / "cells"; OUT.mkdir(exist_ok=True, parents=True)
try:
    import os, ctypes
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL
except Exception:
    pass
t0 = time.time()
d1, sm, so, fxday = core.load_series(asset, args.legacy_file)
cell_rows, trade_frames, reg_rows = [], [], []
seed0 = 1000 * (abs(hash(asset)) % 1000) if False else (sum(ord(ch) * (i + 1) for i, ch in enumerate(asset)) * 7919) % 900000
for ti, tf in enumerate(core.TFS):
    cell = core.build_cell(asset, tf, d1, sm, so, fxday)
    bars, n, bh = cell["bars"], cell["n"], cell["bh"]
    trend, vol = core.regime_labels(cell, tf)
    year = bars.index.year.to_numpy()
    windows = {"IS": (cell["first"], cell["split"]), "OOS": (cell["split"], n), "FULL": (cell["first"], n)}
    for vi, v in enumerate(core.VARIANTS):
        sg, nr, ns, use_story = cell["sigs"][v]
        for wi, (w, (lo, hi)) in enumerate(windows.items()):
            arr = msnr.simulate(cell["o"], cell["h"], cell["l"], cell["c"], cell["a"], sg, nr, ns, lo, hi, core.BUF, 0, core.TPR, core.TPR,
                                0.0, 0.0, 0.0, bh, True)
            tr = core.trades_to_df(arr)
            ntr = len(tr)
            row = dict(asset=asset, tf=tf, variant=v, window=w, start=str(bars.index[lo].date()), end=str(bars.end.iloc[hi - 1].date()),
                       n_bars=hi - lo, trades=ntr)
            if ntr:
                row.update(long_share=float((tr.dir == 1).mean()), gross=float(tr.grossR.mean()), gross_sd=float(tr.grossR.std(ddof=1)) if ntr > 1 else np.nan,
                           win_gross=float((tr.grossR > 0).mean()))
            if ntr >= 5:
                seed = seed0 + 10000 * ti + 1000 * vi + 100 * wi
                bm = core.bench_all(cell, use_story, tr, lo, hi, args.reps, seed)
                for mode, arr_r in bm.items():
                    ok = arr_r[~np.isnan(arr_r)]
                    g = row["gross"]
                    row[f"{mode}_mean"] = float(ok.mean()); row[f"{mode}_sd"] = float(ok.std(ddof=1))
                    ge = (np.sum(ok >= g) + 1) / (len(ok) + 1); le = (np.sum(ok <= g) + 1) / (len(ok) + 1)
                    row[f"{mode}_p_two"] = float(min(1.0, 2 * min(ge, le)))
                    row[f"{mode}_z"] = float((g - ok.mean()) / ok.std(ddof=1)) if ok.std(ddof=1) > 0 else np.nan
            cell_rows.append(row)
            if ntr:
                sj = tr.sig_j.astype(int).to_numpy(); ej = tr.entry_j.astype(int).to_numpy(); xj = tr.exit_j.astype(int).to_numpy()
                t = pd.DataFrame(dict(asset=asset, tf=tf, variant=v, window=w, sig_j=sj, dir=tr.dir.astype(int), E=tr.E, risk=tr.risk,
                                      grossR=tr.grossR, risk_atr=tr.risk_atr, tgtR=tr.tgtR, hold_h=(xj - sj) * bh,
                                      sig_time=bars.end.to_numpy()[sj], year=year[sj], trend=trend[sj], vol=vol[sj]))
                if cell["spr_med"] is not None:
                    t["spr_med"] = cell["spr_med"][ej]; t["spr_obs"] = cell["spr_obs"][ej]
                trade_frames.append(t)
                # regime benchmarks (FULL window only), B1
                if w == "FULL" and not args.no_regime:
                    for scheme, lab in (("year", year), ("trend", trend), ("vol", vol)):
                        tl = lab[sj]
                        for bucket in np.unique(tl):
                            if scheme != "year" and bucket < 0:
                                continue
                            sel = tl == bucket
                            sub = tr[sel]
                            if len(sub) < 1:
                                continue
                            mask = lab == bucket
                            seedr = seed0 + 10000 * ti + 1000 * vi + 50 + int(bucket) % 40
                            bm = core.bench_all(cell, use_story, sub.reset_index(drop=True), lo, hi, args.rreps, seedr, elig_mask=mask, modes=("B1",))
                            ok = bm["B1"][~np.isnan(bm["B1"])]
                            reg_rows.append(dict(asset=asset, tf=tf, variant=v, scheme=scheme, bucket=int(bucket), trades=int(sel.sum()),
                                                 gross=float(sub.grossR.mean()), B1_mean=float(ok.mean()) if len(ok) else np.nan,
                                                 B1_sd=float(ok.std(ddof=1)) if len(ok) > 1 else np.nan))
    print(asset, tf, "done", round(time.time() - t0), "s", flush=True)
tag = args.tag
pd.DataFrame(cell_rows).to_csv(OUT / f"{asset}_{tag}_cells.csv", index=False)
pd.concat(trade_frames).to_parquet(OUT / f"{asset}_{tag}_trades.parquet")
pd.DataFrame(reg_rows).to_csv(OUT / f"{asset}_{tag}_regime.csv", index=False)
print(asset, "finished", round(time.time() - t0), "s")
