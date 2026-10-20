"""Quantify two look-ahead effects in the phase-3 results (follow-up of audit F9 and of the new pivot-overwrite finding), for ONE asset x ladder cell.

  LAG  (audit F9, limit-entry configs only): a resting limit order is filled inside touch bar j, but the shipped code reads the storyline, the storyline target,
       the roadblock level, the extra indicator filter, the liquidity count and the stop-sizing ATR as of the CLOSE of bar j. Here all of them are read as of the
       close of bar j-1 (topdown_lag.py, see topdown_lag.diff). Session flag (a clock fact) and the touch/fill rule are left as shipped.
  CAUS (new finding): msnr.storyline overwrites an already-confirmed pivot when a later, more extreme pivot of the same type appears (see causal_ref.py).
       'story_simple' is replaced by the strictly causal storyline. Affects configs with story=simple (all confirmation types).
  Configs: every config of the shipped grid (p3_msnr.all_configs) that is touched by either change. Statistics are the shipped walk-forward statistics
  (p3_msnr.stats_row: folds 2-5 of 5, pre-holdout data only, phase 'A').
Output: limit_leak/<asset>_<ladder>.csv  (one row per config). Validation: with no change the numbers must equal results/phase3_configs_compact.parquet.
Usage: python -B 09_limit_entry_leak.py ASSET LADDER      (NUMBA_CACHE_DIR must be set)"""
import os, sys, time
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead")
assert os.path.exists("D:/") and os.environ.get("NUMBA_CACHE_DIR")
sys.path.insert(0, str(HERE / "code_copy")); sys.path.insert(0, str(HERE))
import p3common as C, p3_msnr as M, msnr, topdown_lag as TL
from causal_ref import storyline_causal
ASSET, LADDER = sys.argv[1], sys.argv[2]
PART = sys.argv[3] if len(sys.argv) > 3 else "all"      # all | limit (conf=limit configs) | simple (story=simple, non-limit): lets heavy cells fit the 10-minute limit
OUT = HERE / "limit_leak"; OUT.mkdir(exist_ok=True)
for mod in (C, M, M.msnr, TL):
    assert Path(mod.__file__).resolve().parent == (HERE / "code_copy").resolve(), mod.__file__

CAUSAL = []
_orig_story = msnr.storyline
def _story_wrap(df, depth=2):
    CAUSAL.append((df.end.to_numpy(), storyline_causal(df, depth)))
    return _orig_story(df, depth)
msnr.storyline = _story_wrap


class CellL(M.Cell3):
    var = "ship"                      # which storyline is in force: "ship" (as shipped) or "caus" (strictly causal); part of every cache key

    def get_setups(self, depth, gaps):
        key = (self.var, depth, gaps)
        if key not in self.setups:
            S, f = M.Cell3.get_setups(self, depth, gaps)      # stores under (depth, gaps); move it so the two storylines never mix
            self.setups[key] = (S, f); self.setups.pop((depth, gaps), None)
        return self.setups[key]

    def get_setups_lag(self, depth, gaps):
        key = ("lag", self.var, depth, gaps)
        if key not in self.setups:
            ev = msnr.level_events(self.b3, include_qm=False, av_depth=depth)
            if gaps:
                ev = pd.concat([ev, M.gap_events(self.b3)], ignore_index=True).sort_values("avail", kind="stable")
            ej, ep, ek, _ = msnr.map_events_to_bars(ev, self.b4)
            S = TL.gen_setups(self.o, self.h, self.l, self.c, self.a4, self.atr3_at, self.t3c, self.t3h, self.t3l, ej, ep, ek, *self.sw, self.K, 50.0)
            jl = np.maximum((S[:, 2].astype(int) if len(S) else np.zeros(0, int)) - 1, 0)
            d = S[:, 0] if len(S) else np.zeros(0)
            feats = dict(td=self.story_td[jl], simple=self.story_simple[jl], tgt=self.story_tgt[jl], rb=np.where(d == 1, self.rb_res[jl], self.rb_sup[jl]))
            self.setups[key] = (S, feats)
        return self.setups[key]

    def trades_lag(self, cf, j_lo=None, j_hi=None):
        """Same as Cell3.trades but for conf == limit with every read moved from bar j to bar j-1."""
        S, f = self.get_setups_lag(cf["depth"], cf["gaps"])
        if len(S) == 0:
            return np.zeros((0, 13))
        d = S[:, 0]; keep = np.ones(len(S), bool)
        if cf["story"] != "none":
            keep &= f[cf["story"]] == d
        if cf["liq"]:
            keep &= S[:, 10] >= 1
        if cf["miss"]:
            keep &= S[:, 11] >= 1
        cj = S[:, 2]; okc = ~np.isnan(cj); cji = np.where(okc, cj, 0).astype(int); cjl = np.maximum(cji - 1, 0)
        if cf["sess"]:
            keep &= okc & self.sess[cji]
        if cf["xf"]:
            L, Sx = self.XF[cf["xf"]]
            keep &= okc & np.where(d == 1, np.asarray(L)[cjl], np.asarray(Sx)[cjl])
        lo = 260 if j_lo is None else j_lo; hi = self.n if j_hi is None else j_hi
        keep &= okc & (cj >= lo) & (cj < hi)
        tname, tm, tr_ = dict((t[0], t) for t in M.TGT)[cf["tgt"]]
        cs = self.cost
        a4l = np.concatenate([[np.nan], self.a4[:-1]]); a4l = np.where(a4l > 0, a4l, np.nan)   # zero ATR in the previous bar (flat 5-minute spell): cannot size, skip
        return TL.sim_setups(self.o, self.h, self.l, self.c, a4l, S, keep, 4, 0 if cf["stop"] == "zone" else 1, tm, tr_, f["tgt"], f["rb"], bool(cf["rb"]),
                             cs["l_eabs"], cs["l_epct"], cs["tabs"], cs["tpct"], cs["sabs"], cs["spct"], cs["carry"], self.bar_h, 0.1, 0.05)


t0 = time.time()
cell = CellL(ASSET, LADDER, "A"); e = cell.edges
print(ASSET, LADDER, "cell built", round(time.time() - t0, 1), "s; T4 bars", cell.n, flush=True)
e1, caus = CAUSAL[0]
story_ship = cell.story_simple.copy()
story_caus = M.asof(e1, cell.b4.end.to_numpy(), caus).astype(np.int64)
print("story_simple differs (shipped vs causal) on", int((story_ship != story_caus).sum()), "of", cell.n, "entry bars", flush=True)
cfgs = M.all_configs(cell.gapsok)
if not ASSET.endswith("USDT"):
    cfgs = [c for c in cfgs if c["xf"] != "vwap_trend"]
stored = pd.read_parquet(r"D:/Research-Publishing/02-malaysian-snr/results/phase3_configs_compact.parquet")
stored = stored[(stored.asset == ASSET) & (stored.ladder == LADDER)].reset_index(drop=True)
assert len(stored) == len(cfgs), (len(stored), len(cfgs))


def stat(tr):
    r, _, _, _ = M.stats_row(tr, cell, e)
    return r["wf_n"], r["wf_netR"], r["wf_grossR"], r["wf_t"], r["wf_p"]


rows = []
for i, cf in enumerate(cfgs):
    lim = cf["conf"] == "limit"; simp = cf["story"] == "simple"
    if not (lim or simp) or (PART == "limit" and not lim) or (PART == "simple" and lim):
        continue
    rec = dict(asset=ASSET, ladder=LADDER, idx=i, name=M.cname(cf), conf=cf["conf"], story=cf["story"], tgt=cf["tgt"], depth=cf["depth"], gaps=cf["gaps"], liq=cf["liq"], miss=cf["miss"],
               sess=cf["sess"], rb=cf["rb"], stored_n=int(stored.wf_n[i]), stored_net=float(stored.wf_netR[i]), stored_gross=float(stored.wf_grossR[i]),
               stored_p=float(stored.wf_p[i]), stored_DSR=float(stored.DSR[i]))
    cell.story_simple = story_ship; cell.var = "ship"
    rec["n0"], rec["net0"], rec["gross0"], rec["t0"], rec["p0"] = stat(cell.trades(cf))
    if lim:
        rec["nL"], rec["netL"], rec["grossL"], rec["tL"], rec["pL"] = stat(cell.trades_lag(cf))
    if simp:
        cell.story_simple = story_caus; cell.var = "caus"
        rec["nC"], rec["netC"], rec["grossC"], rec["tC"], rec["pC"] = stat(cell.trades(cf))
        if lim:
            rec["nLC"], rec["netLC"], rec["grossLC"], rec["tLC"], rec["pLC"] = stat(cell.trades_lag(cf))
        cell.story_simple = story_ship; cell.var = "ship"
    rows.append(rec)
    if len(rows) % 200 == 0: print("  configs done", len(rows), round(time.time() - t0), "s", flush=True)
R = pd.DataFrame(rows)
ok = (R.n0 == R.stored_n) & ((R.net0 - R.stored_net).abs() < 1e-9)
print("validation vs stored results (no change applied):", int(ok.sum()), "of", len(R), "configs identical", flush=True)
R["validated"] = ok
R.to_csv(OUT / (f"{ASSET}_{LADDER}.csv" if PART == "all" else f"{ASSET}_{LADDER}.{PART}.csv"), index=False)
print("seconds", round(time.time() - t0, 1))
