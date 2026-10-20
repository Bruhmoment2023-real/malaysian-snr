"""Truncation (look-ahead) test of the PHASE-3 top-down pipeline, in the style of code/06_truncation_lookahead_test.py.

For each asset x ladder the whole Cell3 object (four timeframes of bars, T1 rejections, top-down storyline and its
target, simple storyline, T2 roadblock levels, T3 ATR/closes mapped to T4, session flag, indicator filters, the POI
setup table from gen_setups, and simulated trades for a sample of configurations) is built on the full 5-minute base
series and on the series cut at 35%, 60% and 85%. Per-bar arrays are compared on every T4 bar that is complete in the
cut set (all but its last). Setup rows are compared when their zone had closed before the cut; trades when they had
exited before the last two bars of the cut set.

NOTE what this test can and cannot see. It checks that the value stored for bar j does not depend on data after bar j
closes. It does NOT check that a trade entered INSIDE bar j uses only values known before bar j closes - that is the
limit-entry leak (audit F9), which is measured separately in 09_limit_entry_leak.py.

Works on COPIES of the code (followup/lookahead/code_copy); data are read from D:/Malaysian-SNR read-only.
Usage: python -B 08_truncation_phase3.py TAG ASSET[,ASSET...] [ladder,ladder]
"""
import os, sys, time
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead")
assert os.path.exists("D:/") and os.environ.get("NUMBA_CACHE_DIR"), "set NUMBA_CACHE_DIR first"
sys.path.insert(0, str(HERE / "code_copy"))
import p3common as C
import p3_msnr as M

for mod in (C, M, M.TD, M.msnr, M.E2, M.IND):
    assert Path(mod.__file__).resolve().parent == (HERE / "code_copy").resolve(), mod.__file__
TAG = sys.argv[1]; ASSETS = sys.argv[2].split(",")
LADDERS = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] != "all" else list(C.LADDERS)
STABLE = len(sys.argv) > 4 and sys.argv[4] == "stable"
if STABLE:                      # variant: identical engine except that simultaneous setups are ordered by a STABLE sort
    import topdown_stable
    M.TD = topdown_stable
_REAL = C.load_base; BASE = {}; CUT = {"t": None}
LASTN = int(sys.argv[5]) if len(sys.argv) > 5 else 0      # optional: use only the last N rows of the 5-minute base (keeps the 5-minute ladder inside the time limit)


def load_cut(asset):
    if asset not in BASE:
        BASE.clear(); BASE[asset] = _REAL(asset) if not LASTN else _REAL(asset).iloc[-LASTN:]
    d = BASE[asset]
    return d if CUT["t"] is None else d[d.index < CUT["t"]]


C.load_base = load_cut
CFGS = [dict(M.CANON),
        dict(M.CANON, conf="limit", stop="lvl"), dict(M.CANON, conf="limit", stop="lvl", liq=1, tgt="storyEnd", rb=0, sess=1),
        dict(M.CANON, conf="limit", stop="lvl", story="simple", tgt="roadblock", liq=1, miss=1),
        dict(M.CANON, conf="bos", tgt="roadblock", liq=1), dict(M.CANON, conf="rej", stop="ltf", tgt="storyEnd"),
        dict(M.CANON, conf="eng", story="simple", tgt="4R", sess=1, miss=1), dict(M.CANON, story="none", depth=2, tgt="2R", rb=0),
        dict(M.CANON, xf="ema200"), dict(M.CANON, xf="sweep", conf="bos", tgt="2R")]


def ndiff(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    return ~((np.abs(a - b) <= 1e-9 * np.maximum(1.0, np.abs(a))) | (np.isnan(a) & np.isnan(b)))


def series_of(cell):
    out = dict(atr_T4=cell.a4, story_topdown=cell.story_td, story_target=cell.story_tgt, story_simple=cell.story_simple,
               roadblock_res=cell.rb_res, roadblock_sup=cell.rb_sup, atr_T3_at_T4=cell.atr3_at, T3_close_at_T4=cell.t3c,
               T3_high_at_T4=cell.t3h, T3_low_at_T4=cell.t3l, session_flag=cell.sess)
    for k, (a, b) in cell.XF.items():
        out[f"xfilter_{k}_long"] = a; out[f"xfilter_{k}_short"] = b
    return {k: np.asarray(v, float) for k, v in out.items()}


rows, srows, trows = [], [], []
t00 = time.time()
for asset in ASSETS:
    for ladder in LADDERS:
        t0 = time.time(); CUT["t"] = None
        full = M.Cell3(asset, ladder, "B"); fs = series_of(full)
        fS = {k: full.get_setups(*k)[0] for k in ((3, 0), (2, 0))}
        ftr = [full.trades(c) for c in CFGS]
        print(asset, ladder, "full cell built", round(time.time() - t0, 1), "s; T4 bars", full.n, "; setups d3", len(fS[(3, 0)]), flush=True)
        idx = BASE[asset].index
        for frac in (0.35, 0.6, 0.85):
            CUT["t"] = idx[int(len(idx) * frac)]
            part = M.Cell3(asset, ladder, "B"); ps = series_of(part); m = part.n - 1
            assert (part.b4.index[:m] == full.b4.index[:m]).all()
            for k in sorted(fs):
                bad = ndiff(fs[k][:m], ps[k][:m]); w = np.where(bad)[0]
                rows.append(dict(asset=asset, ladder=ladder, cut_frac=frac, series=k, bars_compared=m, mismatches=int(bad.sum()),
                                 first_bad=int(w[0]) if len(w) else -1, last_bad=int(w[-1]) if len(w) else -1, mismatches_after_warmup=int(bad[260:].sum())))
            for key in ((3, 0), (2, 0)):
                pS = part.get_setups(*key)[0]
                closed = pS[pS[:, 2] < part.n - 2 - part.K - 3] if len(pS) else pS; k = len(closed)
                bad = int(ndiff(closed, fS[key][:k]).any(axis=1).sum()) if (k and len(fS[key]) >= k) else (k if len(fS[key]) < k else 0)
                srows.append(dict(asset=asset, ladder=ladder, cut_frac=frac, pivot_depth=key[0], setups_compared=k, setups_differing=bad))
                # features attached to setups (story at touch, target, roadblock)
                pf = part.get_setups(*key)[1]; ff = full.get_setups(*key)[1]
                for fk in ("td", "simple", "tgt", "rb"):
                    b2 = int(ndiff(pf[fk][:k], ff[fk][:k]).sum()) if k else 0
                    srows.append(dict(asset=asset, ladder=ladder, cut_frac=frac, pivot_depth=key[0], setups_compared=k, setups_differing=b2, feature=fk))
            for ci, c in enumerate(CFGS):
                tp = part.trades(c); closed = tp[tp[:, 2] < part.n - 2] if len(tp) else tp; k = len(closed)
                bad = (k if len(ftr[ci]) < k else int(ndiff(closed, ftr[ci][:k]).any(axis=1).sum())) if k else 0
                # order-free view: is each closed trade of the cut run present (same setup row, same entry bar, same result) in the full run?
                key_full = {(int(x[12]), int(x[1])): x for x in ftr[ci]}
                absent = sum(1 for x in closed if (int(x[12]), int(x[1])) not in key_full or ndiff(x, key_full[(int(x[12]), int(x[1]))]).any())
                # how many entry bars carry more than one eligible setup (a tie the sort has to break)?
                trows.append(dict(asset=asset, ladder=ladder, cut_frac=frac, config=M.cname(c), closed_trades_compared=k, trades_differing=bad, trades_not_in_full_run=absent))
            del part
        print(asset, ladder, "done", round(time.time() - t0, 1), "s", flush=True)
        del full

R = pd.DataFrame(rows); S = pd.DataFrame(srows); T = pd.DataFrame(trows)
R.to_csv(HERE / f"check_phase3_truncation_series.{TAG}.csv", index=False); S.to_csv(HERE / f"check_phase3_truncation_setups.{TAG}.csv", index=False)
T.to_csv(HERE / f"check_phase3_truncation_trades.{TAG}.csv", index=False)
pd.set_option("display.width", 240); pd.set_option("display.max_rows", 300); pd.set_option("display.max_colwidth", 100)
print(R.groupby("series").agg(checks=("mismatches", "size"), bar_comparisons=("bars_compared", "sum"), mismatches=("mismatches", "sum"), after_warmup=("mismatches_after_warmup", "sum")))
print("SERIES: checks", len(R), "; bar comparisons", int(R.bars_compared.sum()), "; mismatching bars", int(R.mismatches.sum()))
print(R[R.mismatches > 0].to_string(index=False))
print("SETUPS: checks", len(S), "; setup rows compared", int(S.setups_compared.sum()), "; differing", int(S.setups_differing.sum()))
print(S[S.setups_differing > 0].to_string(index=False))
print("TRADES: checks", len(T), "; closed trades compared", int(T.closed_trades_compared.sum()), "; differing", int(T.trades_differing.sum()))
print("TRADES of the cut run that are absent from (or different in) the full run:", int(T.trades_not_in_full_run.sum()))
print(T[T.trades_differing > 0].to_string(index=False))
print("sort used for simultaneous setups:", "stable (follow-up variant)" if STABLE else "as in the original code (numpy argsort default, not stable)")
print("base rows used:", LASTN if LASTN else "all"); print("total seconds", round(time.time() - t00, 1))
