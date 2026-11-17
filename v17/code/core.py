"""Core library for the paper-02 rework (v17): data loading, frozen-rule signals, windows, matched random benchmarks.
The rule engine itself is msnr_frozen.py (byte copy of D:/Malaysian-SNR/backtest/msnr.py). Nothing here changes it.
Pre-specification: PLAN_2026-11-17.md.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from numba import njit

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import msnr_frozen as msnr

ROOT = Path(r"D:/Research-Publishing/02-malaysian-snr/rework-v3")
PQ = ROOT / "data" / "parquet"
RES_SPREAD = ROOT / "results" / "duka_spread_by_year.csv"
CUT_CRYPTO = pd.Timestamp("2026-11-09", tz="UTC")           # end of last full Mon-Sun UTC week
CUT_FX = pd.Timestamp("2026-11-08 22:00", tz="UTC")         # end of last full FX week (week starts Sun 22:00 UTC)

CRYPTO_LEGACY = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "PAXGUSDT"]
CRYPTO_NEW = ["BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT", "LINKUSDT", "TRXUSDT", "DOTUSDT", "AVAXUSDT", "BCHUSDT"]
METALS = ["XAUUSD", "XAGUSD"]
FX = []   # dropped (see PLAN amendments)
ASSET_CLASS = {**{a: "crypto" for a in CRYPTO_LEGACY + CRYPTO_NEW}, **{a: "metal" for a in METALS}, **{a: "fx" for a in FX}}
SAMPLE = {**{a: "legacy" for a in CRYPTO_LEGACY + METALS}, **{a: "confirmatory" for a in CRYPTO_NEW + FX}}
TFS = {"1h": ("4h", 1), "4h": ("1d", 4), "1d": ("1w", 24)}
VARIANTS = ["V0_raw", "V1_plain", "V2_story", "V3_QM_story", "V4_HTFlvl_story"]
IS_FRAC = 0.60
BUF, TPR = 0.1, 2.0


def load_series(asset, legacy_file=None):
    """Return (df1h with open/high/low/close, spr_med, spr_obs or None, is_fx_day)."""
    cls = ASSET_CLASS[asset]
    if cls == "crypto":
        f = legacy_file or PQ / f"{asset}_1h.parquet"
        d = pd.read_parquet(f)[["open", "high", "low", "close"]]
        d = d[~d.index.duplicated()].sort_index()
        d.index = d.index.tz_convert("UTC")
        return d[d.index < CUT_CRYPTO], None, None, False
    # metals: histdata.com 1h BID bars (aggregated from M1; v16 phase-3 source). Spread: yearly median measured on Dukascopy bid/ask
    # sample months (results/duka_spread_by_year.csv); v16 constant (USD 0.35 gold, 0.035 silver) as the second series.
    d = pd.read_parquet(PQ / f"{asset}_hd_1h.parquet")[["open", "high", "low", "close"]]
    d = d[~d.index.duplicated()].sort_index()
    const = {"XAUUSD": 0.35, "XAGUSD": 0.035}[asset]
    spr_const = pd.Series(const, index=d.index)
    tf = RES_SPREAD
    if tf.exists():
        t = pd.read_csv(tf); t = t[t.used] if "used" in t.columns else t
        t = t[t.asset == asset].set_index("year").median_usd
        yrs = pd.Series(d.index.year, index=d.index)
        spr_med = yrs.map(lambda y: t.loc[min(t.index, key=lambda k: abs(k - y))]).astype(float)
    else:
        spr_med = spr_const.copy()
    return d, spr_med, spr_const, True


def bar_series(d1, tf, fxday, series=None):
    """make_bars on d1; optionally also return a per-bar value of `series` at the bar's first hourly candle."""
    bars = msnr.make_bars(d1, tf, fxday)
    if series is None:
        return bars, None
    s = series.reindex(d1.index)
    tmp = pd.DataFrame({"open": s, "high": s, "low": s, "close": s}, index=d1.index)
    b2 = msnr.make_bars(tmp, tf, fxday)
    return bars, b2["open"].to_numpy()


def build_cell(asset, tf, d1, spr_med, spr_obs, fxday):
    htf, bh = TFS[tf]
    bars, sm = bar_series(d1, tf, fxday, spr_med)
    _, so = bar_series(d1, tf, fxday, spr_obs) if spr_obs is not None else (None, None)
    hbars = msnr.make_bars(d1, htf, fxday)
    o, h, l, c = (bars[k].to_numpy() for k in ("open", "high", "low", "close"))
    a = msnr.atr(bars)
    st_h = msnr.storyline(hbars)
    hi = np.searchsorted(hbars.end.to_numpy(), bars.end.to_numpy(), side="right") - 1
    story = np.where(hi >= 0, st_h[np.clip(hi, 0, None)], 0).astype(np.int64)
    ei, ep, ek, es = msnr.map_events_to_bars(msnr.level_events(bars), bars)
    sig0, sig1, _, _, nres, nsup = msnr.run_levels(o, h, l, c, ei, ep, ek, es)
    ri, rp, rk, rs = msnr.map_events_to_bars(msnr.level_events(bars, include_qm=False, av_mode="raw"), bars)
    sigR, _, _, _, nresR, nsupR = msnr.run_levels(o, h, l, c, ri, rp, rk, rs, 99)
    hi_, hp, hk, hs = msnr.map_events_to_bars(msnr.level_events(hbars, include_qm=False), bars)
    sigH, _, _, _, nresH, nsupH = msnr.run_levels(o, h, l, c, hi_, hp, hk, hs)
    sigs = {
        "V0_raw": (sigR, nresR, nsupR, False),
        "V1_plain": (sig0, nres, nsup, False),
        "V2_story": (np.where(sig0 == story, sig0, 0), nres, nsup, True),
        "V3_QM_story": (np.where(sig1 == story, sig1, 0), nres, nsup, True),
        "V4_HTFlvl_story": (np.where(sigH == story, sigH, 0), nresH, nsupH, True),
    }
    n = len(bars)
    first = int(np.argmax(~np.isnan(a))) + 1
    split = first + int((n - first) * IS_FRAC)
    return dict(bars=bars, o=o, h=h, l=l, c=c, a=a, story=story, sigs=sigs, n=n, first=first, split=split,
                bh=float(bh), spr_med=sm, spr_obs=so)


def regime_labels(cell, tf):
    """Causal regime labels per bar: trend (1 bull, 0 bear, -1 unknown), vol (1 high, 0 low, -1 unknown)."""
    bh = TFS[tf][1]
    c = pd.Series(cell["c"]); a = pd.Series(cell["a"])
    L = int(round(90 * 24 / bh)); W = int(round(365 * 24 / bh))
    ret = (c / c.shift(L) - 1).to_numpy()
    trend = np.where(np.isnan(ret), -1, (ret > 0).astype(int))
    atrp = a / c
    med = atrp.rolling(W, min_periods=W // 2).median()
    vol = np.where(np.isnan(med.to_numpy()) | np.isnan(atrp.to_numpy()), -1, (atrp.to_numpy() > med.to_numpy()).astype(int))
    return trend.astype(np.int64), vol.astype(np.int64)


def atr_bins(cell, j_lo, j_hi):
    """Quintile bin (0-4) of ATR/close within window [j_lo, j_hi); -1 outside / nan."""
    atrp = cell["a"] / cell["c"]
    seg = atrp[j_lo:j_hi]
    ok = ~np.isnan(seg)
    edges = np.quantile(seg[ok], [0.2, 0.4, 0.6, 0.8])
    b = np.full(cell["n"], -1, np.int64)
    b[j_lo:j_hi] = np.where(ok, np.searchsorted(edges, seg, side="right"), -1)
    return b


def trades_to_df(arr):
    cols = ["sig_j", "entry_j", "exit_j", "dir", "E", "S", "T", "grossR", "costR0", "risk_atr", "tgtR"]
    df = pd.DataFrame(arr, columns=cols)
    df["risk"] = (df.E - df.S).abs()
    return df


@njit(cache=True)
def rand_bench(o, h, l, c, a, story, elig, bin_sorted, bin_off, s_risk, s_tgt, s_bin, use_story, plong, vol_match, reps, seed):
    """Random-entry benchmark. Entry bars are drawn from `elig` (uniform) or, if vol_match, from the ATR quintile of a randomly
    drawn strategy trade. Stop distance (ATR units) and target multiple come jointly from that same strategy trade.
    Direction: storyline if use_story, else long with probability plong. Gross R only (costs are applied later, per scenario)."""
    np.random.seed(seed)
    ntr = len(s_risk)
    out = np.full(reps, np.nan)
    for r in range(reps):
        tot = 0.0; cnt = 0; tries = 0
        while cnt < ntr and tries < ntr * 50:
            tries += 1
            q = np.random.randint(0, ntr)
            if vol_match:
                b = s_bin[q]
                if b < 0:
                    continue
                lo = bin_off[b]; hi = bin_off[b + 1]
                if hi == lo:
                    continue
                j = bin_sorted[lo + np.random.randint(0, hi - lo)]
            else:
                j = elig[np.random.randint(0, len(elig))]
            if use_story:
                d = story[j]
                if d == 0:
                    continue
            else:
                d = 1 if np.random.random() < plong else -1
            risk = s_risk[q] * a[j]
            if risk <= 0:
                continue
            E = o[j + 1]
            S = E - d * risk
            T = E + d * s_tgt[q] * risk
            k, X, hit = msnr._exit(o, h, l, c, j + 1, d, E, S, T)
            tot += d * (X - E) / risk
            cnt += 1
        if cnt > 0:
            out[r] = tot / cnt
    return out


def make_bin_index(bins, elig):
    """bins: per-bar quintile (-1 invalid); elig: eligible bar indices. Returns bin_sorted, bin_off(6)."""
    b = bins[elig]
    order = np.argsort(b, kind="stable")
    sorted_idx = elig[order]
    bs = b[order]
    off = np.searchsorted(bs, np.arange(0, 6), side="left").astype(np.int64)
    # off[k] = first position with bin >= k ; entries with bin -1 sort first, so shift
    start = np.searchsorted(bs, 0, side="left")
    off = np.array([np.searchsorted(bs, k, side="left") for k in range(6)], dtype=np.int64)
    return sorted_idx.astype(np.int64), off


def bench_all(cell, sig_info, trades, j_lo, j_hi, reps, seed, elig_mask=None, modes=("B0", "B1", "B2")):
    """Run the requested benchmark modes for one (cell, variant, window). `trades` = trades_to_df output (strategy).
    elig_mask (bool per bar) restricts entry bars (regime benchmark). Returns dict mode -> array of rep means."""
    o, h, l, c, a, story = cell["o"], cell["h"], cell["l"], cell["c"], cell["a"], cell["story"]
    use_story = sig_info
    n = cell["n"]
    hi = min(j_hi, n - 1)
    valid = ~np.isnan(a)
    m = np.zeros(n, bool); m[j_lo:hi] = True
    m &= valid
    if elig_mask is not None:
        m &= elig_mask
    elig = np.where(m)[0].astype(np.int64)
    out = {}
    if len(trades) == 0 or len(elig) == 0:
        return {k: np.full(reps, np.nan) for k in modes}
    s_risk = trades.risk_atr.to_numpy(float); s_tgt = trades.tgtR.to_numpy(float)
    plong = float((trades.dir == 1).mean())
    bins = atr_bins(cell, j_lo, j_hi)
    bsorted, boff = make_bin_index(bins, elig)
    s_bin = bins[trades.sig_j.astype(int).to_numpy()].astype(np.int64)
    dummy_bin = np.zeros(1, np.int64)
    if "B0" in modes:
        out["B0"] = rand_bench(o, h, l, c, a, story, elig, bsorted, boff, s_risk, s_tgt, s_bin, use_story, 0.5, False, reps, seed)
    if "B1" in modes:
        out["B1"] = out["B0"] if use_story and "B0" in out else rand_bench(o, h, l, c, a, story, elig, bsorted, boff, s_risk, s_tgt, s_bin, use_story, plong, False, reps, seed + 1)
    if "B2" in modes:
        out["B2"] = rand_bench(o, h, l, c, a, story, elig, bsorted, boff, s_risk, s_tgt, s_bin, use_story, plong, True, reps, seed + 2)
    return out


@njit(cache=True)
def rand_bench_dir(o, h, l, c, a, story, elig_long, elig_short, ok_long, ok_short, s_risk, s_tgt, use_story, plong, reps, seed):
    """B3 (post hoc): random entries only on bars that show a failed breakout of the previous bar (candle without any level).
    Direction d is drawn first (storyline variants: j drawn from the union and d = storyline, rejected if the bar does not qualify for d)."""
    np.random.seed(seed)
    ntr = len(s_risk)
    out = np.full(reps, np.nan)
    nL = len(elig_long); nS = len(elig_short)
    for r in range(reps):
        tot = 0.0; cnt = 0; tries = 0
        while cnt < ntr and tries < ntr * 100:
            tries += 1
            q = np.random.randint(0, ntr)
            if use_story:
                if np.random.random() < 0.5:
                    if nL == 0:
                        continue
                    j = elig_long[np.random.randint(0, nL)]
                else:
                    if nS == 0:
                        continue
                    j = elig_short[np.random.randint(0, nS)]
                d = story[j]
                if d == 0:
                    continue
                if d == 1 and not ok_long[j]:
                    continue
                if d == -1 and not ok_short[j]:
                    continue
            else:
                d = 1 if np.random.random() < plong else -1
                if d == 1:
                    if nL == 0:
                        continue
                    j = elig_long[np.random.randint(0, nL)]
                else:
                    if nS == 0:
                        continue
                    j = elig_short[np.random.randint(0, nS)]
            risk = s_risk[q] * a[j]
            if risk <= 0:
                continue
            E = o[j + 1]
            S = E - d * risk
            T = E + d * s_tgt[q] * risk
            k, X, hit = msnr._exit(o, h, l, c, j + 1, d, E, S, T)
            tot += d * (X - E) / risk
            cnt += 1
        if cnt > 0:
            out[r] = tot / cnt
    return out
