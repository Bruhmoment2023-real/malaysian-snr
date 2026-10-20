"""Robustness check R1 (written by the audit, NOT part of the original study).

Question: the phase-1 simulator decides "stop first" whenever stop and target both lie inside one
1H/4H/1D bar. Random entries with the same geometry therefore show a NEGATIVE gross expectancy
(-0.03 to -0.10 R), i.e. the simulator is pessimistic. Does the conclusion "levels = random" survive
when the order of stop/target is resolved on 5-minute bars instead?

Method (crypto only: BTC/ETH/SOL, where 5-minute Binance bars are on disk):
  * take every stored phase-1 trade (entry price E, stop S, target T, direction) as given;
  * re-walk it (a) on the trade-timeframe bars with the original stop-first rule (must reproduce the
    stored gross R exactly) and (b) on 5-minute bars (stop-first only inside a single 5m bar);
  * draw random entries (uniform bar, coin-flip side, stop distance in ATR and target R sampled from
    the strategy's own trades) and walk them both ways too (V0 and V1 only - they have no direction filter);
  * report strategy-minus-random gross R under both resolutions.
The trade list is held fixed (the one-position-at-a-time sequencing is not re-derived).

READ-ONLY on D:/Malaysian-SNR. Run (about 1-3 min):
  set NUMBA_CACHE_DIR=D:\\Research-Publishing\\02-malaysian-snr\\.numba_cache
  D:\\Malaysian-SNR\\.venv\\Scripts\\python.exe -B D:\\Research-Publishing\\02-malaysian-snr\\code\\02_intrabar_resolution_check.py
"""
import os
from pathlib import Path
import numpy as np, pandas as pd
from numba import njit

SRC = Path(r"D:/Malaysian-SNR"); OUT = Path(r"D:/Research-Publishing/02-malaysian-snr/results")
assert os.path.exists("D:/"), "D: offline"
TF = {"1h": "1h", "4h": "4h", "1d": "1D"}
NRAND = 200_000


@njit
def walk(o, h, l, k0, d, E, S, T):
    """Stop-first walk from bar k0 (entry at E inside bar k0). Returns exit price, exit idx."""
    n = len(o)
    for k in range(k0, n):
        if d == 1:
            if l[k] <= S:
                return (min(S, o[k]) if k > k0 else S), k
            if h[k] >= T:
                return T, k
        else:
            if h[k] >= S:
                return (max(S, o[k]) if k > k0 else S), k
            if l[k] <= T:
                return T, k
    return np.nan, n - 1


@njit
def walk_many(o, h, l, k0, d, E, S, T):
    out = np.empty(len(k0))
    for i in range(len(k0)):
        if k0[i] < 0 or k0[i] >= len(o):
            out[i] = np.nan; continue
        X, _ = walk(o, h, l, k0[i], d[i], E[i], S[i], T[i])
        out[i] = d[i] * (X - E[i]) / abs(E[i] - S[i])
    return out


def atr(o, h, l, c, n=14):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy()


def main():
    tr = pd.read_csv(SRC / "results" / "trades_default_full.csv")
    oos = pd.read_csv(SRC / "results" / "key_table_default_OOS.csv")
    oos_start = {(a, t): pd.Timestamp(s, tz="UTC") for a, t, s in oos[["asset", "tf", "start"]].drop_duplicates().itertuples(index=False)}
    tr["t_entry"] = pd.to_datetime(tr.signal_time, utc=True)
    rows = []; rng = np.random.default_rng(20261013)
    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        m5 = pd.read_parquet(SRC / "phase3" / "data" / f"{sym}_5m.parquet")
        t5 = m5.index.as_unit("ns").asi8
        o5, h5, l5, c5 = (m5[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        for tf, rule in TF.items():
            g = m5.groupby(m5.index.floor(rule))
            b = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last()})
            tb = b.index.as_unit("ns").asi8
            ob, hb, lb, cb = (b[k].to_numpy(float) for k in ("open", "high", "low", "close"))
            ab = atr(ob, hb, lb, cb)
            for v in ("V0_raw", "V1_plain", "V2_story", "V3_QM_story", "V4_HTFlvl_story"):
                x = tr[(tr.asset == sym) & (tr.tf == tf) & (tr.variant == v)]
                if len(x) < 30:
                    continue
                te = x.t_entry.dt.as_unit("ns").astype("int64").to_numpy()
                kb = np.searchsorted(tb, te); k5 = np.searchsorted(t5, te)
                ok = (kb < len(tb)) & (k5 < len(t5))
                ok[ok] &= (tb[kb[ok]] == te[ok]) & (t5[k5[ok]] == te[ok])
                E, S, T, d = (x[k].to_numpy(float) for k in ("E", "S", "T", "dir")); d = d.astype(np.int64)
                ok[ok] &= np.abs(ob[kb[ok]] / E[ok] - 1) < 1e-5          # same entry open in both data sets (stored prices are rounded to 6 significant figures)
                kb, k5, E, S, T, d, te = kb[ok], k5[ok], E[ok], S[ok], T[ok], d[ok], te[ok]
                stored = x.grossR.to_numpy()[ok]
                gc = walk_many(ob, hb, lb, kb, d, E, S, T); gf = walk_many(o5, h5, l5, k5, d, E, S, T)
                good = ~np.isnan(gc) & ~np.isnan(gf)
                is_oos = te >= oos_start[(sym, tf)].as_unit("ns").value
                base = dict(asset=sym, tf=tf, variant=v, n_stored=len(x), n_matched=int(good.sum()),
                            repro_max_abs_diff=float(np.nanmax(np.abs(gc[good] - stored[good]))),
                            repro_share_exact=float(np.mean(np.abs(gc[good] - stored[good]) < 0.02)))
                # random benchmark for the no-filter variants
                have_rand = v in ("V0_raw", "V1_plain")
                if have_rand:
                    ra = x.risk_atr.to_numpy()[ok][good]; tg = x.tgtR.to_numpy()[ok][good]
                    lo, hi = kb[good].min() - 1, kb[good].max() - 1
                    j = rng.integers(max(lo, 15), hi, NRAND); q = rng.integers(0, len(ra), NRAND)
                    dd = np.where(rng.random(NRAND) < 0.5, 1, -1).astype(np.int64)
                    risk = ra[q] * ab[j]; Er = ob[j + 1]; okr = np.isfinite(risk) & (risk > 0)
                    j, dd, risk, Er, q = j[okr], dd[okr], risk[okr], Er[okr], q[okr]
                    Sr = Er - dd * risk; Tr = Er + dd * tg[q] * risk
                    kr5 = np.searchsorted(t5, tb[j + 1])
                    rc = walk_many(ob, hb, lb, j + 1, dd, Er, Sr, Tr); rf = walk_many(o5, h5, l5, kr5, dd, Er, Sr, Tr)
                    gr = ~np.isnan(rc) & ~np.isnan(rf); r_oos = tb[j + 1] >= oos_start[(sym, tf)].as_unit("ns").value
                for per, mk, mr in (("FULL", good, None), ("OOS", good & is_oos, "oos"), ("IS", good & ~is_oos, "is")):
                    if mk.sum() < 20:
                        continue
                    r = dict(base, period=per, n=int(mk.sum()), strat_gross_coarse=gc[mk].mean(), strat_gross_5m=gf[mk].mean(),
                             strat_sd_5m=gf[mk].std(ddof=1), win_coarse=(gc[mk] > 0).mean(), win_5m=(gf[mk] > 0).mean())
                    if have_rand:
                        rm = gr if mr is None else (gr & r_oos if mr == "oos" else gr & ~r_oos)
                        r.update(n_rand=int(rm.sum()), rand_gross_coarse=rc[rm].mean(), rand_gross_5m=rf[rm].mean(),
                                 rand_sd_5m=rf[rm].std(ddof=1), rand_sd_coarse=rc[rm].std(ddof=1), strat_sd_coarse=gc[mk].std(ddof=1))
                    rows.append(r)
            print(sym, tf, "done", flush=True)
    R = pd.DataFrame(rows)
    R["edge_coarse"] = R.strat_gross_coarse - R.rand_gross_coarse
    R["edge_5m"] = R.strat_gross_5m - R.rand_gross_5m
    R["se_edge_5m"] = np.sqrt(R.strat_sd_5m ** 2 / R.n + R.rand_sd_5m ** 2 / R.n_rand)
    R["se_edge_coarse"] = np.sqrt(R.strat_sd_coarse ** 2 / R.n + R.rand_sd_coarse ** 2 / R.n_rand)
    R.round(5).to_csv(OUT / "robustness_R1_intrabar_by_cell.csv", index=False)
    # pooled
    P = []
    for (per, tf, v), g in R.groupby(["period", "tf", "variant"]):
        w = g.n.to_numpy(float); r = dict(period=per, tf=tf, variant=v, n=int(w.sum()), cells=len(g),
                                          strat_gross_coarse=np.average(g.strat_gross_coarse, weights=w), strat_gross_5m=np.average(g.strat_gross_5m, weights=w),
                                          win_coarse=np.average(g.win_coarse, weights=w), win_5m=np.average(g.win_5m, weights=w))
        if g.edge_5m.notna().all():
            for k in ("coarse", "5m"):
                r[f"rand_gross_{k}"] = np.average(g[f"rand_gross_{k}"], weights=w)
                r[f"edge_{k}"] = np.average(g[f"edge_{k}"], weights=w)
                se = np.sqrt((w ** 2 * g[f"se_edge_{k}"] ** 2).sum()) / w.sum()
                r[f"z_{k}"] = r[f"edge_{k}"] / se
        P.append(r)
    P = pd.DataFrame(P); P["tf"] = pd.Categorical(P.tf, ["1d", "4h", "1h"]); P = P.sort_values(["period", "tf", "variant"])
    P.round(4).to_csv(OUT / "robustness_R1_intrabar_pooled.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(P.round(4).to_string(index=False))
    print("reproduction of stored gross R on coarse bars: min share exact", R.repro_share_exact.min(), "matched share", (R.n_matched / R.n_stored).min())


if __name__ == "__main__":
    main()
