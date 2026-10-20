"""Diagnose the only non-trivial phase-2 truncation mismatch: SI=F 1h, 35% cut, `story` series, bars 4797-4802.
Question: does the full-run value at those bars depend on data AFTER the bar (a leak), or is the cut run's value the odd one
(an incomplete higher-timeframe bar at the cut treated as complete)?  Prints the HTF bars around the cut and both story series."""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead")
assert os.path.exists("D:/") and os.environ.get("NUMBA_CACHE_DIR")
sys.path.insert(0, str(HERE / "code_copy"))
import p2common as P
REAL = P.load_src; CUT = {"t": None}
def load_cut(a, t):
    d, b = REAL(a, t)
    return (d if CUT["t"] is None else d[d.index < CUT["t"]]), b
P.load_src = load_cut
asset, tf = "SI=F", "1h"
src = REAL(asset, tf)[0]
full = P.Cell(asset, tf, "B")
CUT["t"] = src.index[int(len(src) * 0.35)]
part = P.Cell(asset, tf, "B")
m = part.n - 1
bad = np.where(full.story[:m] != part.story[:m])[0]
print("cut time (first row removed):", CUT["t"], "| bars compared", m, "| mismatching bar idx", bad.tolist())
idx = part.bars.index; end = part.bars.end
print("bar start / end / story_full / story_cut for the last 10 compared bars")
for j in range(m - 9, m):
    print(j, idx[j], end.iloc[j], int(full.story[j]), int(part.story[j]))
metals = P.ASSETS[asset]["cost"]["metals"]
src_c = src[src.index < CUT["t"]]
hb_part = P.make_bars_v(src_c, P.HTF[tf], metals, REAL(asset, tf)[1]); hb_full = P.make_bars_v(src, P.HTF[tf], metals, REAL(asset, tf)[1])
print("\nHTF (", P.HTF[tf], ") bars, cut run, last 3: start / end / close")
print(hb_part.tail(3)[["end", "close"]])
print("same HTF bars in the full run:")
print(hb_full.loc[hb_part.index[-3:], ["end", "close"]])
last = hb_part.index[-1]
print("\nlast HTF bar of the cut run: constituent source rows in cut =", int(((src_c.index >= last)).sum()), "| in full run =", int(((src.index >= last) & (src.index < hb_full.loc[last, 'end'])).sum()))

# ---- direct test of msnr.storyline on the HTF closes
stp = P.msnr.storyline(hb_part); stf = P.msnr.storyline(hb_full)
k = len(hb_part); dd = np.where(stp[:k] != stf[:k])[0]
print("\nHTF bars compared:", k, "| storyline differs at HTF idx:", dd.tolist())
for i in range(k - 8, k):
    print(i, hb_part.index[i], "end_cut", hb_part.end.iloc[i], "close_cut", round(float(hb_part.close.iloc[i]), 4), "close_full", round(float(hb_full.close.iloc[i]), 4), "st_cut", int(stp[i]), "st_full", int(stf[i]))
cp = hb_part.close.to_numpy(); pf = P.msnr._close_pivots(cp, 2); pF = P.msnr._close_pivots(hb_full.close.to_numpy(), 2)
print("cut run pivots (confirm idx, type, px), last 4:", [(int(a), int(b), round(float(c_), 4)) for a, b, c_ in zip(pf[1][-4:], pf[2][-4:], pf[3][-4:])])
print("full run pivots with confirm idx <= k-1, last 4:", [(int(a), int(b), round(float(c_), 4)) for a, b, c_ in zip(pF[1], pF[2], pF[3]) if a <= k - 1][-4:])
