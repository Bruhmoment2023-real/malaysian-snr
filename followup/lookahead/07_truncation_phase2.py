"""Truncation (look-ahead) test of the PHASE-2 pipeline, in the style of code/06_truncation_lookahead_test.py.

Idea: anything the pipeline knows at bar j must not change when all data after bar j is deleted. For each
asset/timeframe cell the whole phase-2 Cell (bars, ATR, storyline, MSNR signals V0/V1, all confluence filters,
standalone triggers, regimes, level-dependent filters, limit-fill arrays) is built on the full price series and on
the series cut at 35%, 60% and 85%, and compared bar by bar on every bar that is complete in both (all bars of the cut
series except its last one). A sample of configurations is then SIMULATED both ways; every trade that has closed
before the last two bars of the cut series must be identical in the full run.

Works on COPIES of the code (followup/lookahead/code_copy); price data are read from D:/Malaysian-SNR read-only.
Not truncated: the macro side-series (DXY, real yield, gold/silver ratio, funding). They enter through an as-of merge
with a 2-day lag (funding: at settlement time) and are built with backward-looking ewm/rolling/diff only (read in code).

Run:  set NUMBA_CACHE_DIR=<followup>/lookahead/.numba_cache ;  python -B 07_truncation_phase2.py
"""
import os, sys, time
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead")
assert os.path.exists("D:/") and os.environ.get("NUMBA_CACHE_DIR"), "set NUMBA_CACHE_DIR first"
sys.path.insert(0, str(HERE / "code_copy"))
import p2common as P

assert Path(P.__file__).resolve().parent == (HERE / "code_copy").resolve(), P.__file__
assert Path(P.msnr.__file__).resolve().parent == (HERE / "code_copy").resolve()
_REAL_LOAD = P.load_src
CUT = {"t": None}; LASTN = {}


def ORIG_LOAD(asset, tf):
    """Source bars; optionally only the last N rows (argument ASSET:tf:N) so that a heavy cell fits the 10-minute limit."""
    d, base = _REAL_LOAD(asset, tf)
    n = LASTN.get((asset, tf))
    return (d.iloc[-n:] if n else d), base


def load_cut(asset, tf):
    d, base = ORIG_LOAD(asset, tf)
    if CUT["t"] is not None:
        d = d[d.index < CUT["t"]]
    return d, base


P.load_src = load_cut
# usage: 07_truncation_phase2.py TAG ASSET:tf[:lastN],ASSET:tf,...
TAG = sys.argv[1]; CELLS = []
for spec in sys.argv[2].split(","):
    p = spec.split(":"); CELLS.append((p[0], p[1]))
    if len(p) > 2:
        LASTN[(p[0], p[1])] = int(p[2])
LIM_EXITS = [(0, 1.0, 0.0), (0, 2.0, 0.0), (0, 3.0, 0.0), (1, 1.0, 0.0), (2, 2.0, 1.0), (3, 2.0, 0.0)]


def series_of(cell):
    """Every per-bar array the phase-2 Cell holds, flattened to name -> 1-D float array."""
    out = {"atr": cell.a, "story": cell.story}
    for b, (s0, l0, nr, ns) in cell.base.items():
        out.update({f"base_{b}_signal": s0, f"base_{b}_level": l0, f"base_{b}_nres": nr, f"base_{b}_nsup": ns})
    for k, (a, b) in cell.F.items():
        out[f"filter_{k}_long"] = a; out[f"filter_{k}_short"] = b
    for k, v in cell.S.items():
        out[f"trigger_{k}"] = v
    for k, v in cell.G.items():
        out[f"regime_{k}"] = v
    for k, v in cell.aux.items():
        if isinstance(v, tuple):
            for i, x in enumerate(v):
                out[f"aux_{k}_{i}"] = x
        else:
            out[f"aux_{k}"] = v
    for b, lf in cell.levelF.items():
        for k, (x, y) in lf.items():
            out[f"levelfilter_{b}_{k}_long"] = x; out[f"levelfilter_{b}_{k}_short"] = y
    for b in ("V0", "V1"):
        for eps in (0.0, 0.05):
            for nm, x in zip(("dir", "price", "level", "nres", "nsup"), cell.limit_fills(b, eps)):
                out[f"limitfill_{b}_eps{eps:g}_{nm}"] = x
    return {k: np.asarray(v, float) for k, v in out.items()}


def sample_cfgs(cell):
    cf = []
    for b in ("V0", "V1"):
        for x in P.EXITS:
            cf.append(dict(kind="mkt", base=b, filters=[], exit=x))
        cf.append(dict(kind="mkt", base=b, filters=[], exit=P.DEFAULT_EXIT, buf=0.3))
        for f in sorted(cell.F) + sorted(cell.levelF[b]):
            cf.append(dict(kind="mkt", base=b, filters=[f], exit=P.DEFAULT_EXIT))
        for eps in (0.0, 0.05):
            for x in LIM_EXITS:
                cf.append(dict(kind="lim", base=b, filters=[], exit=x, eps=eps, sl_atr=0.5))
        for f in sorted(cell.F):
            cf.append(dict(kind="lim", base=b, filters=[f], exit=P.DEFAULT_EXIT, eps=0.05, sl_atr=0.5))
    for s in sorted(cell.S):
        cf.append(dict(kind="alone", trigger=s, exit=P.DEFAULT_EXIT))
    return cf


def ndiff(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    bad = ~((np.abs(a - b) <= 1e-9 * np.maximum(1.0, np.abs(a))) | (np.isnan(a) & np.isnan(b)))
    return bad


rows, trows = [], []
t00 = time.time()
for asset, tf in CELLS:
    t0 = time.time()
    CUT["t"] = None
    full = P.Cell(asset, tf, "B"); fs = series_of(full); cfgs = sample_cfgs(full)
    print(asset, tf, "full cell built", round(time.time() - t0, 1), "s; bars", full.n, flush=True)
    ftr = [full.trades(c) for c in cfgs]          # keyed by position: cfg_name() omits the stop buffer, so names can collide
    src_index = ORIG_LOAD(asset, tf)[0].index
    for frac in (0.35, 0.6, 0.85):
        CUT["t"] = src_index[int(len(src_index) * frac)]
        part = P.Cell(asset, tf, "B"); ps = series_of(part)
        m = part.n - 1                                           # bars complete in the cut set: all but its last
        assert (part.bars.index[:m] == full.bars.index[:m]).all()
        for k in sorted(fs):
            if k not in ps:
                rows.append(dict(asset=asset, tf=tf, cut_frac=frac, series=k, bars_compared=0, mismatches=-1, first_bad=-1, mismatches_after_warmup=-1)); continue
            bad = ndiff(fs[k][:m], ps[k][:m]); w = np.where(bad)[0]
            rows.append(dict(asset=asset, tf=tf, cut_frac=frac, series=k, bars_compared=m, mismatches=int(bad.sum()),
                             first_bad=int(w[0]) if len(w) else -1, last_bad=int(w[-1]) if len(w) else -1,
                             mismatches_after_warmup=int(bad[P.WARMUP:].sum())))
        for ci, c in enumerate(cfgs):
            nm = P.cfg_name(c) + (f"|buf{c['buf']}" if "buf" in c else ""); tp = part.trades(c); tf_ = ftr[ci]
            closed = tp[tp[:, 2] < part.n - 2] if len(tp) else tp
            k = len(closed)
            if len(tf_) < k:
                bad_tr = k
            else:
                bad_tr = int(ndiff(closed, tf_[:k]).any(axis=1).sum()) if k else 0
            trows.append(dict(asset=asset, tf=tf, cut_frac=frac, config=nm, kind=c["kind"], closed_trades_compared=k, trades_differing=bad_tr))
    print(asset, tf, "done", round(time.time() - t0, 1), "s; bars", full.n, "; series", len(fs), "; configs simulated", len(cfgs), flush=True)

R = pd.DataFrame(rows); T = pd.DataFrame(trows)
R["source_rows_used"] = [LASTN.get((a, t), "all") for a, t in zip(R.asset, R.tf)]
R.to_csv(HERE / f"check_phase2_truncation_series.{TAG}.csv", index=False); T.to_csv(HERE / f"check_phase2_truncation_trades.{TAG}.csv", index=False)
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 300)
R["family"] = R.series.str.split("_").str[0]
print(R.groupby("family").agg(series=("series", "nunique"), checks=("mismatches", "size"), bar_comparisons=("bars_compared", "sum"), mismatches=("mismatches", "sum"),
                              mismatches_after_warmup=("mismatches_after_warmup", "sum")))
print("\nSERIES: total checks", len(R), "; bar comparisons", int(R.bars_compared.sum()), "; mismatching bars", int(R.mismatches.sum()),
      "; of which after the 260-bar warm-up", int(R.mismatches_after_warmup.sum()))
print(R[R.mismatches != 0].groupby("series").agg(checks_with_mismatch=("mismatches", "size"), mismatches=("mismatches", "sum"), first_bad_min=("first_bad", "min"),
                                                  last_bad_max=("last_bad", "max"), after_warmup=("mismatches_after_warmup", "sum")).to_string())
print("\nTRADES: checks", len(T), "; closed trades compared", int(T.closed_trades_compared.sum()), "; trades differing", int(T.trades_differing.sum()))
print(T.groupby("kind").agg(checks=("config", "size"), closed_trades=("closed_trades_compared", "sum"), differing=("trades_differing", "sum")))
print(T[T.trades_differing > 0].to_string(index=False))
print("total seconds", round(time.time() - t00, 1))
