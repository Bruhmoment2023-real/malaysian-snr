"""Table builders for the v17 manuscript and online appendix (pure functions of the result CSVs)."""
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(r"D:/Research-Publishing/02-malaysian-snr/rework-v3"); RES = ROOT / "results"
V16 = Path(r"D:/Research-Publishing/02-malaysian-snr/results")
VN = {"V0_raw": "V0 literal", "V1_plain": "V1 obvious levels", "V2_story": "V2 storyline", "V3_QM_story": "V3 Quasimodo", "V4_HTFlvl_story": "V4 higher-timeframe levels"}
TFN = {"1h": "1 hour", "4h": "4 hour", "1d": "1 day"}
MINUS = "\u2212"


def f(x, d=3, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace("-", MINUS)


def pf(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "n/a"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def n0(x):
    return f"{int(round(x)):,}"


def pooled():
    return pd.read_csv(RES / "pooled_edges_new.csv")


def table_pooled_variant_tf(window="FULL"):
    p = pooled(); p = p[(p.window == window) & (p.bench == "B1") & (p.grouping == "variant_tf")].copy()
    rows = []
    for tf in ("1h", "4h", "1d"):
        for v in VN:
            r = p[p.group == f"{v}|{tf}"]
            if r.empty:
                continue
            r = r.iloc[0]
            rows.append([TFN[tf], VN[v], n0(r.trades), f(r.gross, 3, True), f(r.edge, 3, True), f"{f(r.edge_lo, 3, True)} to {f(r.edge_hi, 3, True)}", pf(r.p_holm_F2) if window == "FULL" else pf(r.edge_p_norm),
                         f(r.mean_cost, 3), f(r.net, 3, True), f(r.mde80, 3)])
    hdr = ["Timeframe", "Variant", "Trades", "Gross R", "Edge over random (B1)", "95% CI", "p (Holm)" if window == "FULL" else "p", "Mean cost R", "Net R", "Min. detectable edge"]
    return hdr, rows


def table_groups(grouping, window="FULL", bench="B1"):
    p = pooled(); p = p[(p.window == window) & (p.bench == bench) & (p.grouping == grouping)]
    rows = []
    for _, r in p.iterrows():
        g = r.group.replace("V0_raw", "V0").replace("V1_plain", "V1").replace("V2_story", "V2").replace("V3_QM_story", "V3").replace("V4_HTFlvl_story", "V4")
        rows.append([g.replace("|", ", "), n0(r.trades), f(r.gross, 3, True), f(r.edge, 3, True), f"{f(r.edge_lo, 3, True)} to {f(r.edge_hi, 3, True)}", pf(r.edge_p_norm), f(r.net, 3, True), f(r.mde80, 3)])
    return ["Group", "Trades", "Gross R", "Edge (B1)", "95% CI", "p", "Net R", "Min. detectable edge"], rows


def table_f1():
    d = pd.read_csv(RES / "F1_percell_tests_new.csv")
    names = {"B1": "B1 direction-matched (primary)", "B0": "B0 coin-flip (earlier design)", "B2": "B2 + volatility-matched"}
    rows = []
    for _, r in d.iterrows():
        rows.append([names[r.bench], int(r.n_tests), f"{r.expected_p05:.1f}", f"{int(r.n_p05)} ({int(r.n_p05_pos)} positive, {int(r.n_p05_neg)} negative)", int(r.n_holm), int(r.n_bh), int(r.n_by), f(r.min_bh_q, 3)])
    return ["Benchmark", "Cell tests", "Expected p<0.05", "Observed p<0.05", "Holm", "BH", "BY", "Smallest BH q"], rows


def table_cost():
    s = pd.read_csv(RES / "cost_sensitivity_new.csv")
    out = []
    for cl in ("crypto", "metal"):
        q = s[(s.cls == cl) & (s.variant == "ALL")]
        for _, r in q.iterrows():
            out.append([cl, r.scenario, n0(r.trades), f(r.gross, 3, True), f(r.cost, 3), f(r.net, 3, True)])
    return ["Market", "Cost scenario", "Trades", "Gross R", "Cost R", "Net R"], out


def table_breakeven():
    b = pd.read_csv(RES / "breakeven_new.csv")
    rows = []
    for _, r in b.iterrows():
        if r.cls == "crypto":
            rows.append(["crypto", VN[r.variant], f(r.gross, 3, True), f(r.breakeven_bps_per_side, 2, True), f(r.breakeven_bps_if_gross_plus_0p07R, 2, True)])
        else:
            rows.append(["gold and silver", VN[r.variant], f(r.gross, 3, True), f(r.breakeven_spread_multiple, 2, True) + " x spread", f(r.breakeven_spread_multiple_if_gross_plus_0p07R, 2, True) + " x spread"])
    return ["Market", "Variant", "Gross R", "Break-even cost per side (bps) or spread multiple", "Same if gross R were 0.07 higher"], rows


def table_regime_pooled():
    r = pd.read_csv(RES / "regimes_pooled_new.csv")
    rows = []
    lab = {("trend", 1): "Trailing 90-day return > 0", ("trend", 0): "Trailing 90-day return <= 0", ("vol", 1): "ATR/price above its 1-year median", ("vol", 0): "ATR/price at or below its 1-year median"}
    for _, x in r.iterrows():
        nm = lab.get((x.scheme, x.bucket), f"Year {int(x.bucket)}")
        rows.append([nm, n0(x.trades), f(x.edge, 3, True), f"{f(x.lo, 3, True)} to {f(x.hi, 3, True)}", pf(x.p), f(x.net, 3, True)])
    return ["Regime (all variants pooled)", "Trades", "Edge over regime-matched random", "95% CI", "p", "Net R"], rows


def table_b3():
    f3 = RES / "B3_pooled_new.csv"
    if not f3.exists():
        return None
    b = pd.read_csv(f3); b = b[b.grouping.isin(["all", "variant"])]
    rows = []
    for _, r in b.iterrows():
        g = VN.get(r.group, "All variants")
        rows.append([g, n0(r.trades), f(r.edge_B3, 3, True), f"{f(r.lo, 3, True)} to {f(r.hi, 3, True)}", pf(r.p_norm)])
    return ["Group", "Trades", "Edge over rejection-candle random (B3)", "95% CI", "p"], rows


def table_data():
    c = pd.read_csv(RES / "cells_all_new.csv")
    c = c[(c.window == "FULL") & (c.tf == "1h") & (c.variant == "V0_raw")]
    import sys
    sys.path.insert(0, str(ROOT / "code"))
    cls = {"BTCUSDT": "legacy", "ETHUSDT": "legacy", "SOLUSDT": "legacy", "PAXGUSDT": "legacy", "XAUUSD": "legacy", "XAGUSD": "legacy"}
    rows = []
    for _, r in c.iterrows():
        kind = "gold spot (bid)" if r.asset == "XAUUSD" else "silver spot (bid)" if r.asset == "XAGUSD" else ("gold token" if r.asset == "PAXGUSDT" else "crypto")
        rows.append([r.asset.replace("USDT", "") if r.asset.endswith("USDT") else r.asset, kind, "re-test" if r.asset in cls else "confirmatory (new)", r.start, r.end])
    return ["Asset", "Type", "Role", "First bar used", "Last bar used"], rows
