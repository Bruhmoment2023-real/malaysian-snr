"""Aggregate analysis for the paper-02 rework (v17). Pre-specified in PLAN_2026-11-17.md (P3-P8).
Reads results/cells/*_new_{cells.csv,trades.parquet,regime.csv}; writes results/*.csv and results/analysis_log.txt.
"""
import sys, glob, json
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/rework-v3/code")
import core

RES = core.ROOT / "results"; CELLS = RES / "cells"
TAG = sys.argv[1] if len(sys.argv) > 1 else "new"
MINT = 30; NBOOT = 5000
rng = np.random.default_rng(20261117)
CLS, SMP = core.ASSET_CLASS, core.SAMPLE

# ---------------------------------------------------------------- load
cells = pd.concat([pd.read_csv(f) for f in sorted(CELLS.glob(f"*_{TAG}_cells.csv"))], ignore_index=True)
trades = pd.concat([pd.read_parquet(f) for f in sorted(CELLS.glob(f"*_{TAG}_trades.parquet"))], ignore_index=True)
reg = pd.concat([pd.read_csv(f) for f in sorted(CELLS.glob(f"*_{TAG}_regime.csv"))], ignore_index=True)
for df in (cells, trades, reg):
    df["cls"] = df.asset.map(CLS); df["sample"] = df.asset.map(SMP)
if core.RES_SPREAD.exists() and "spr_med" in trades.columns:      # metals: yearly median measured on Dukascopy bid/ask sample months
    sp = pd.read_csv(core.RES_SPREAD); sp = sp[sp.used] if "used" in sp.columns else sp
    for a, g in sp.groupby("asset"):
        yrs = g.set_index("year").median_usd
        m = trades.asset == a
        trades.loc[m, "spr_med"] = trades.loc[m, "year"].map(lambda y: yrs.loc[min(yrs.index, key=lambda k: abs(k - y))])
trades["month"] = pd.to_datetime(trades.sig_time).dt.strftime("%Y-%m")
log = open(RES / f"analysis_log_{TAG}.txt", "w")
def P(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); log.write(s + "\n"); log.flush()

# ---------------------------------------------------------------- costs (P5)
def cost_R(t, crypto_bps=None, spread_mult=1.0, spread_col="spr_med"):
    """Cost per trade in R. crypto_bps None = base case (7 bps, PAXG 10 bps)."""
    E = t.E.to_numpy(); risk = t.risk.to_numpy(); hold = t.hold_h.to_numpy()
    cls = t.asset.map(CLS).to_numpy()
    out = np.zeros(len(t))
    cr = cls == "crypto"
    if cr.any():
        bps = np.where(t.asset.to_numpy() == "PAXGUSDT", 10.0, 7.0) if crypto_bps is None else np.full(len(t), float(crypto_bps))
        carry = 0.02
        out[cr] = ((2 * bps / 1e4 * E) / risk + carry * hold / 8760.0 * E / risk)[cr]
    nm = ~cr
    if nm.any():
        spr = t[spread_col].fillna(t["spr_obs"]).fillna(0).to_numpy() * spread_mult
        carry = np.where(cls == "metal", 0.03, 0.0)
        out[nm] = (spr / risk + carry * hold / 8760.0 * E / risk)[nm]
    return out

trades["costR"] = cost_R(trades)
trades["netR"] = trades.grossR - trades.costR

# ---------------------------------------------------------------- multiple-testing helpers
def holm(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p); adj = np.empty(n)
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, (n - r) * p[i]); adj[i] = min(1.0, run)
    return adj
def bh(p, by=False):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)[::-1]
    c = np.sum(1.0 / np.arange(1, n + 1)) if by else 1.0
    adj = np.empty(n); prev = 1.0
    for rank, i in zip(range(n, 0, -1), o):
        prev = min(prev, p[i] * n * c / rank); adj[i] = min(1.0, prev)
    return adj

# ---------------------------------------------------------------- per-cell table (FULL, IS, OOS) with base net
key = ["asset", "tf", "variant", "window"]
g = trades.groupby(key)
net = g.agg(net=("netR", "mean"), net_sd=("netR", "std"), cost=("costR", "mean"), win_net=("netR", lambda x: (x > 0).mean()),
            win_sum=("netR", lambda x: x[x > 0].sum()), loss_sum=("netR", lambda x: -x[x < 0].sum())).reset_index()
net["PF"] = net.win_sum / net.loss_sum
cells = cells.merge(net.drop(columns=["win_sum", "loss_sum"]), on=key, how="left")
cells["net_t"] = cells.net / (cells.net_sd / np.sqrt(cells.trades))
cells["net_p_pos"] = 1 - stats.t.cdf(cells.net_t, np.maximum(cells.trades - 1, 1))      # one-sided H0: net <= 0
for m in ("B0", "B1", "B2"):
    cells[f"edge_{m}"] = cells.gross - cells[f"{m}_mean"]
cells.to_csv(RES / f"cells_all_{TAG}.csv", index=False)
full = cells[(cells.window == "FULL")].copy()
F = full[full.trades >= MINT].copy()
P("cells (FULL):", len(full), "with >=30 trades:", len(F), "; assets:", full.asset.nunique())
P("cells with <30 trades:", int((full.trades < MINT).sum()))

# ---------------------------------------------------------------- F1: per-cell tests
rows = []
for m in ("B1", "B0", "B2"):
    p = F[f"{m}_p_two"].to_numpy()
    F[f"{m}_holm"] = holm(p); F[f"{m}_bh"] = bh(p); F[f"{m}_by"] = bh(p, by=True)
    rows.append(dict(bench=m, n_tests=len(F), expected_p05=0.05 * len(F), n_p05=int((p < 0.05).sum()),
                     n_p05_pos=int(((p < 0.05) & (F[f"edge_{m}"] > 0)).sum()), n_p05_neg=int(((p < 0.05) & (F[f"edge_{m}"] < 0)).sum()),
                     min_p=float(p.min()), n_holm=int((F[f"{m}_holm"] < 0.05).sum()), n_bh=int((F[f"{m}_bh"] < 0.05).sum()),
                     n_by=int((F[f"{m}_by"] < 0.05).sum()), min_bh_q=float(F[f"{m}_bh"].min())))
f1 = pd.DataFrame(rows); f1.to_csv(RES / f"F1_percell_tests_{TAG}.csv", index=False)
P("F1 per-cell tests\n", f1.round(4).to_string())
F.to_csv(RES / f"cells_FULL_tested_{TAG}.csv", index=False)
# by sample / class (B1)
rows = []
for (smp, cl), gg in F.groupby(["sample", "cls"]):
    p = gg.B1_p_two
    rows.append(dict(sample=smp, cls=cl, n=len(gg), n_p05=int((p < .05).sum()), expected=0.05 * len(gg),
                     n_pos=int(((p < .05) & (gg.edge_B1 > 0)).sum()), mean_edge=gg.edge_B1.mean(), median_edge=gg.edge_B1.median()))
pd.DataFrame(rows).to_csv(RES / f"F1_by_sample_class_{TAG}.csv", index=False)
P(pd.DataFrame(rows).round(4).to_string())

# ---------------------------------------------------------------- pooled inference (P4): month-cluster bootstrap
def cluster_boot(df, col, B=NBOOT, seed=1):
    """Ratio estimator sum(col)/n over trades, resampling calendar months (clusters)."""
    gm = df.groupby("month")[col].agg(["sum", "count"])
    S = gm["sum"].to_numpy(); N = gm["count"].to_numpy(float); M = len(S)
    est = S.sum() / N.sum()
    r = np.random.default_rng(seed)
    idx = r.integers(0, M, size=(B, M))
    bs = S[idx].sum(1) / N[idx].sum(1)
    se = bs.std(ddof=1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    p_boot = min(1.0, 2 * min((np.sum(bs >= 0) + 1) / (B + 1), (np.sum(bs <= 0) + 1) / (B + 1)))
    p_norm = 2 * (1 - stats.norm.cdf(abs(est / se))) if se > 0 else np.nan
    return dict(n=int(N.sum()), months=M, est=est, se=se, lo=lo, hi=hi, z=est / se if se > 0 else np.nan, p_boot=p_boot, p_norm=p_norm)

def with_excess(tr, bench="B1"):
    cm = cells[["asset", "tf", "variant", "window", f"{bench}_mean"]].rename(columns={f"{bench}_mean": "rm"})
    t = tr.merge(cm, on=key, how="left")
    t["exc"] = t.grossR - t.rm
    return t.dropna(subset=["exc"])

def groups_spec(t):
    t = t.copy(); t["all"] = "all"
    specs = [("all", ["all"]), ("variant", ["variant"]), ("tf", ["tf"]), ("variant_tf", ["variant", "tf"]), ("cls_variant", ["cls", "variant"]),
             ("sample_variant", ["sample", "variant"]), ("cls", ["cls"]), ("sample", ["sample"]), ("asset", ["asset"])]
    return t, specs

pool_rows = []
for window in ("FULL", "IS", "OOS"):
    for bench in ("B1", "B0", "B2"):
        if window != "FULL" and bench != "B1":
            continue
        t = with_excess(trades[trades.window == window].assign(cls=lambda d: d.asset.map(CLS), sample=lambda d: d.asset.map(SMP)), bench)
        t, specs = groups_spec(t)
        for name, cols in specs:
            for k, gg in t.groupby(cols):
                if len(gg) < 50:
                    continue
                k = k if isinstance(k, tuple) else (k,)
                r = cluster_boot(gg, "exc")
                rn = cluster_boot(gg, "netR", seed=2)
                rg = cluster_boot(gg, "grossR", seed=3)
                pool_rows.append(dict(window=window, bench=bench, grouping=name, group="|".join(map(str, k)),
                                      trades=r["n"], months=r["months"], edge=r["est"], edge_se=r["se"], edge_lo=r["lo"], edge_hi=r["hi"], edge_z=r["z"],
                                      edge_p_boot=r["p_boot"], edge_p_norm=r["p_norm"],
                                      gross=rg["est"], net=rn["est"], net_se=rn["se"], net_lo=rn["lo"], net_hi=rn["hi"],
                                      mean_cost=float(gg.costR.mean()), mde80=2.8016 * r["se"]))
pool = pd.DataFrame(pool_rows)
# F2: Holm over the 15 variant x timeframe pooled tests (FULL, B1)
m = (pool.window == "FULL") & (pool.bench == "B1") & (pool.grouping == "variant_tf")
pool.loc[m, "p_holm_F2"] = holm(pool.loc[m, "edge_p_norm"].to_numpy())
pool.to_csv(RES / f"pooled_edges_{TAG}.csv", index=False)
P("Pooled FULL B1 (all, variant, tf, class, sample):")
sel = pool[(pool.window == "FULL") & (pool.bench == "B1") & pool.grouping.isin(["all", "variant", "tf", "cls", "sample", "sample_variant", "cls_variant"])]
P(sel[["grouping", "group", "trades", "edge", "edge_se", "edge_lo", "edge_hi", "edge_p_boot", "gross", "net", "mean_cost", "mde80"]].round(4).to_string())
P("F2 (variant x tf, FULL B1):")
P(pool[m][["group", "trades", "edge", "edge_lo", "edge_hi", "edge_p_boot", "p_holm_F2", "net", "mde80"]].round(4).to_string())

# ---------------------------------------------------------------- cost sensitivity and break-even (P5)
rows = []
tf_full = trades[trades.window == "FULL"].copy()
tf_full["cls"] = tf_full.asset.map(CLS)
for cl in ("crypto", "metal"):
    sub = tf_full[tf_full.cls == cl]
    if len(sub) == 0:
        continue
    scen = []
    if cl == "crypto":
        scen = [(f"{b} bps/side", dict(crypto_bps=b)) for b in (0, 1, 2, 4, 7, 10)]
    else:
        scen = [("spread x0", dict(spread_mult=0.0)), ("spread x0.5", dict(spread_mult=0.5)), ("spread x1 (base, measured yearly median)", dict(spread_mult=1.0)),
                ("spread x2", dict(spread_mult=2.0)), ("v16 constant spread (USD 0.35 gold / 0.035 silver)", dict(spread_col="spr_obs"))]
    for var in core.VARIANTS + ["ALL"]:
        s2 = sub if var == "ALL" else sub[sub.variant == var]
        for nm, kw in scen:
            c = cost_R(s2, **kw); netv = s2.grossR.to_numpy() - c
            rows.append(dict(cls=cl, variant=var, scenario=nm, trades=len(s2), net=float(netv.mean()), gross=float(s2.grossR.mean()), cost=float(c.mean())))
sens = pd.DataFrame(rows); sens.to_csv(RES / f"cost_sensitivity_{TAG}.csv", index=False)
# break-even
rows = []
for (cl, var), s2 in tf_full.groupby(["cls", "variant"]):
    carry = np.where(cl == "metal", 0.03, np.where(cl == "crypto", 0.02, 0.0))
    carryR = float((carry * s2.hold_h / 8760.0 * s2.E / s2.risk).mean())
    gm = float(s2.grossR.mean())
    if cl == "crypto":
        denom = float((2e-4 * s2.E / s2.risk).mean())            # R per 1 bp per side
        be = (gm - carryR) / denom
        be7 = (gm + 0.07 - carryR) / denom
        rows.append(dict(cls=cl, variant=var, gross=gm, carryR=carryR, cost_R_per_bp=denom, breakeven_bps_per_side=be, breakeven_bps_if_gross_plus_0p07R=be7))
    else:
        sp = float((s2.spr_med.fillna(s2.spr_obs).fillna(0) / s2.risk).mean())
        rows.append(dict(cls=cl, variant=var, gross=gm, carryR=carryR, breakeven_spread_multiple=(gm - carryR) / sp if sp > 0 else np.nan,
                         breakeven_spread_multiple_if_gross_plus_0p07R=(gm + 0.07 - carryR) / sp if sp > 0 else np.nan, spreadR=sp))
pd.DataFrame(rows).to_csv(RES / f"breakeven_{TAG}.csv", index=False)
P("Break-even:\n", pd.DataFrame(rows).round(3).to_string())

# ---------------------------------------------------------------- net > 0: per-cell and pooled
Fn = F.copy(); Fn["net_bh"] = bh(Fn.net_p_pos.fillna(1).to_numpy())
P("Net-R positive cells (FULL, >=30 trades):", int((Fn.net > 0).sum()), "of", len(Fn), "; net p<0.05 one-sided:", int((Fn.net_p_pos < 0.05).sum()),
  "; BH q<0.05:", int((Fn.net_bh < 0.05).sum()), "; min BH q:", round(float(Fn.net_bh.min()), 3))
P(Fn.sort_values("net", ascending=False).head(12)[["asset", "tf", "variant", "trades", "gross", "net", "net_p_pos", "net_bh"]].round(4).to_string())
Fn.to_csv(RES / f"net_cells_{TAG}.csv", index=False)

# ---------------------------------------------------------------- win rates
w = F.win_net
P("Net win rate across FULL cells >=30 trades: min", round(w.min(), 3), "median", round(w.median(), 3), "max", round(w.max(), 3),
  "; share between 25% and 38%:", round(((w >= .25) & (w <= .38)).mean(), 3))

# ---------------------------------------------------------------- regimes (P7)
rg = reg.copy()
rows = []
t = trades[trades.window == "FULL"].copy()
t["cls"] = t.asset.map(CLS); t["sample"] = t.asset.map(SMP)
for scheme in ("year", "trend", "vol"):
    lab = t[scheme]
    bm = reg[reg.scheme == scheme][["asset", "tf", "variant", "bucket", "B1_mean"]].rename(columns={"B1_mean": "rm"})
    tt = t.assign(bucket=lab).merge(bm, on=["asset", "tf", "variant", "bucket"], how="left").dropna(subset=["rm"])
    tt["exc"] = tt.grossR - tt.rm
    for (var, b), gg in tt.groupby(["variant", "bucket"]):
        if len(gg) < 100 or (scheme != "year" and b < 0):
            continue
        r = cluster_boot(gg, "exc", B=2000, seed=5)
        rn = cluster_boot(gg, "netR", B=2000, seed=6)
        rows.append(dict(scheme=scheme, bucket=int(b), variant=var, trades=r["n"], edge=r["est"], se=r["se"], lo=r["lo"], hi=r["hi"], p=r["p_norm"], p_boot=r["p_boot"], net=rn["est"]))
rgt = pd.DataFrame(rows)
rgt["p_holm"] = holm(rgt.p.to_numpy()); rgt["p_bh"] = bh(rgt.p.to_numpy())
rgt.to_csv(RES / f"regimes_{TAG}.csv", index=False)
P("Regime tests (F3):", len(rgt), "; p<0.05:", int((rgt.p < .05).sum()), "(expected", round(0.05 * len(rgt), 1), "); Holm<0.05:", int((rgt.p_holm < .05).sum()),
  "; BH<0.05:", int((rgt.p_bh < .05).sum()))
P(rgt.sort_values("p").head(12).round(4).to_string())
# also pooled-by-variant regime summary (all variants pooled)
rows = []
for scheme in ("year", "trend", "vol"):
    lab = t[scheme]
    bm = reg[reg.scheme == scheme][["asset", "tf", "variant", "bucket", "B1_mean"]].rename(columns={"B1_mean": "rm"})
    tt = t.assign(bucket=lab).merge(bm, on=["asset", "tf", "variant", "bucket"], how="left").dropna(subset=["rm"])
    tt["exc"] = tt.grossR - tt.rm
    for b, gg in tt.groupby("bucket"):
        if len(gg) < 100 or (scheme != "year" and b < 0):
            continue
        r = cluster_boot(gg, "exc", B=2000, seed=7); rn = cluster_boot(gg, "netR", B=2000, seed=8)
        rows.append(dict(scheme=scheme, bucket=int(b), trades=r["n"], edge=r["est"], lo=r["lo"], hi=r["hi"], p=r["p_norm"], p_boot=r["p_boot"], net=rn["est"]))
pd.DataFrame(rows).to_csv(RES / f"regimes_pooled_{TAG}.csv", index=False)
P(pd.DataFrame(rows).round(4).to_string())

# ---------------------------------------------------------------- persistence (P8)
wide = cells[cells.window.isin(["IS", "OOS"]) & (cells.trades >= MINT)].pivot_table(index=["asset", "tf", "variant"], columns="window", values="edge_B1")
wide = wide.dropna()
if len(wide) > 3:
    rho, p = stats.spearmanr(wide.IS, wide.OOS)
    P("Persistence: cells", len(wide), "spearman", round(rho, 3), "p", round(p, 4), "same sign", round((np.sign(wide.IS) == np.sign(wide.OOS)).mean(), 3))
    json.dump(dict(cells=len(wide), spearman=rho, p=p, same_sign=float((np.sign(wide.IS) == np.sign(wide.OOS)).mean())), open(RES / f"persistence_{TAG}.json", "w"))

# ---------------------------------------------------------------- power curve (P6)
allr = pool[(pool.window == "FULL") & (pool.bench == "B1") & (pool.grouping == "all")].iloc[0]
P("Power: all-trades pooled SE", round(allr.edge_se, 4), "MDE80", round(allr.mde80, 4), "R per trade; win-rate shift at 2R:", round(allr.mde80 / 3 * 100, 2), "pp")
log.close()


# ---------------------------------------------------------------- B3 (post hoc): candle without level
log = open(RES / f"analysis_log_{TAG}.txt", "a")
b3f = sorted(CELLS.glob("*_b3.csv"))
if b3f:
    b3 = pd.concat([pd.read_csv(f) for f in b3f], ignore_index=True)
    b3["cls"] = b3.asset.map(CLS)
    b3t = b3[b3.trades >= MINT].copy()
    p = b3t.B3_p_two.to_numpy()
    b3t["holm"] = holm(p); b3t["bh"] = bh(p)
    b3t["edge_B3"] = b3t.gross - b3t.B3_mean
    b3t.to_csv(RES / f"B3_cells_{TAG}.csv", index=False)
    P("B3 (post hoc) per-cell:", len(b3t), "tests; p<0.05:", int((p < .05).sum()), "(expected", round(0.05 * len(b3t), 1), "); positive & p<.05:",
      int(((p < .05) & (b3t.edge_B3 > 0)).sum()), "; Holm<0.05:", int((b3t.holm < .05).sum()), "; BH<0.05:", int((b3t.bh < .05).sum()))
    tt = trades[trades.window == "FULL"].merge(b3[["asset", "tf", "variant", "B3_mean"]], on=["asset", "tf", "variant"], how="inner")
    tt["exc"] = tt.grossR - tt.B3_mean
    tt["cls"] = tt.asset.map(CLS); tt["sample"] = tt.asset.map(SMP); tt["all"] = "all"
    rows = []
    for name, cols in (("all", ["all"]), ("variant", ["variant"]), ("variant_tf", ["variant", "tf"]), ("cls_variant", ["cls", "variant"]), ("sample_variant", ["sample", "variant"])):
        for k, gg in tt.groupby(cols):
            if len(gg) < 50: continue
            k = k if isinstance(k, tuple) else (k,)
            r = cluster_boot(gg, "exc", seed=11)
            rows.append(dict(grouping=name, group="|".join(map(str, k)), trades=r["n"], edge_B3=r["est"], se=r["se"], lo=r["lo"], hi=r["hi"], p_norm=r["p_norm"], p_boot=r["p_boot"]))
    b3p = pd.DataFrame(rows); b3p.to_csv(RES / f"B3_pooled_{TAG}.csv", index=False)
    P(b3p[b3p.grouping.isin(["all", "variant", "cls_variant", "sample_variant"])].round(4).to_string())
log.close()


# ---------------------------------------------------------------- per-cell power (P6)
log = open(RES / f"analysis_log_{TAG}.txt", "a")
F["mde80_cell"] = 2.8016 * F.B1_sd
pc = F.groupby(["tf"]).agg(cells=("mde80_cell", "size"), median_trades=("trades", "median"), median_mde80=("mde80_cell", "median"), min_mde80=("mde80_cell", "min"), max_mde80=("mde80_cell", "max")).reset_index()
pc.to_csv(RES / f"power_per_cell_{TAG}.csv", index=False)
P("Per-cell minimum detectable gross edge (80% power):\n", pc.round(4).to_string())
log.close()
