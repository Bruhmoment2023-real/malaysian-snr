"""All figures of the v17 paper, regenerated from code at 600 dpi (PNG) + PDF vector copies. Inputs: results/*.csv written by analysis.py,
and the v16 stored result files (for the intrabar check, the canonical top-down method and the 116,708-variant search, which are not re-run)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from scipy import stats

ROOT = Path(r"D:/Research-Publishing/02-malaysian-snr/rework-v3"); RES = ROOT / "results"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
V16 = Path(r"D:/Research-Publishing/02-malaysian-snr/results")
DPI = 600
plt.rcParams.update({"font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "legend.fontsize": 7, "font.family": "DejaVu Sans",
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.4})
VN = {"V0_raw": "V0 literal", "V1_plain": "V1 obvious", "V2_story": "V2 storyline", "V3_QM_story": "V3 Quasimodo", "V4_HTFlvl_story": "V4 HTF levels"}
COL = {"V0_raw": "#1f4e79", "V1_plain": "#c55a11", "V2_story": "#548235", "V3_QM_story": "#7030a0", "V4_HTFlvl_story": "#7f7f7f"}


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print("saved", name, flush=True)


def fig1_schematic():
    """Fig 1: schematic of the level rules (illustrative prices, not data)."""
    fig, ax = plt.subplots(figsize=(6.2, 3.1))
    ax.grid(False)
    # candles: (open, close, high, low)
    cs = [(10, 12, 12.3, 9.8), (12, 11.2, 12.4, 11.0), (11.2, 10.6, 11.4, 10.4), (10.6, 11.7, 11.9, 10.5), (11.7, 12.35, 12.8, 11.6),
          (12.35, 12.15, 12.5, 11.9), (12.15, 13.1, 13.3, 12.0), (13.1, 13.6, 13.9, 13.0), (13.6, 12.9, 13.7, 12.6), (12.9, 12.5, 13.05, 12.3),
          (12.5, 12.9, 13.0, 12.4), (12.9, 13.7, 13.9, 12.8)]
    for i, (o, c, h, l) in enumerate(cs):
        col = "#2e7d32" if c > o else "#c62828"
        ax.plot([i, i], [l, h], color="k", lw=0.8, zorder=2)
        ax.add_patch(plt.Rectangle((i - 0.28, min(o, c)), 0.56, abs(c - o), facecolor=col, edgecolor="k", lw=0.6, zorder=3))
    lvl = 12.0
    ax.axhline(lvl, xmin=0.08, xmax=0.99, color="#1f4e79", lw=1.0, ls="--")
    ax.annotate("A-level (resistance): close of\nthe last bullish candle\nbefore a bearish one", xy=(1, 12.0), xytext=(-0.5, 13.4), fontsize=6,
                arrowprops=dict(arrowstyle="->", lw=0.6))
    ax.annotate("first retest (wick touches,\nclose below): short at\nnext open", xy=(5, 12.5), xytext=(3.2, 14.4), fontsize=6, arrowprops=dict(arrowstyle="->", lw=0.6))
    ax.annotate("body closes through:\nlevel flips to support (fresh again)", xy=(6, 13.1), xytext=(4.2, 9.2), fontsize=6, arrowprops=dict(arrowstyle="->", lw=0.6))
    ax.annotate("retest from above:\nlong at next open", xy=(9, 12.3), xytext=(8.2, 10.2), fontsize=6, arrowprops=dict(arrowstyle="->", lw=0.6))
    ax.set_xlim(-0.8, 11.8); ax.set_ylim(8.8, 15.2); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    save(fig, "fig1_level_schematic")


def fig2_intrabar():
    d = pd.read_csv(V16 / "robustness_R1_intrabar_pooled.csv")
    d = d[(d.period == "FULL") & d.edge_coarse.notna() & d.variant.isin(["V0_raw", "V1_plain"])]
    fig, axs = plt.subplots(1, 2, figsize=(6.2, 2.6), sharey=True)
    for ax, (vv, ttl) in zip(axs, (("V0_raw", "V0 literal"), ("V1_plain", "V1 obvious levels"))):
        g = d[d.variant == vv].set_index("tf").loc[["1h", "4h", "1d"]]
        x = np.arange(len(g)); w = 0.36
        ax.bar(x - w / 2, g.strat_gross_coarse, w, label="strategy, stop-first rule", color="#1f4e79")
        ax.bar(x + w / 2, g.strat_gross_5m, w, label="strategy, 5-minute resolution", color="#9dc3e6")
        ax.scatter(x - w / 2, g.rand_gross_coarse, marker="_", s=120, color="k", zorder=5, label="matched random, stop-first")
        ax.scatter(x + w / 2, g.rand_gross_5m, marker="_", s=120, color="#c00000", zorder=5, label="matched random, 5-minute")
        ax.set_xticks(x); ax.set_xticklabels(g.index); ax.set_title(ttl); ax.axhline(0, color="k", lw=0.5)
    axs[0].set_ylabel("Gross R per trade (BTC, ETH, SOL pooled)"); axs[0].legend(loc="lower left", fontsize=6)
    save(fig, "fig2_intrabar_resolution")


def fig3_edge():
    p = pd.read_csv(RES / "pooled_edges_new.csv")
    p = p[(p.bench == "B1") & (p.grouping == "variant_tf")]
    fig, axs = plt.subplots(1, 3, figsize=(6.4, 2.7), sharey=True)
    for ax, win in zip(axs, ("IS", "OOS", "FULL")):
        q = p[p.window == win]
        for i, tf in enumerate(("1h", "4h", "1d")):
            for j, v in enumerate(COL):
                r = q[q.group == f"{v}|{tf}"]
                if r.empty:
                    continue
                r = r.iloc[0]; x = i + (j - 2) * 0.15
                ax.errorbar(x, r.edge, yerr=[[r.edge - r.edge_lo], [r.edge_hi - r.edge]], fmt="o", ms=3, color=COL[v], lw=0.9, capsize=1.5,
                            label=VN[v] if i == 0 else None)
        ax.axhline(0, color="k", lw=0.6); ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["1h", "4h", "1d"])
        ax.set_title({"IS": "first 60% of bars", "OOS": "last 40% of bars", "FULL": "all bars"}[win])
    axs[0].set_ylabel("Edge over matched random (gross R per trade)", fontsize=6.5); axs[0].legend(fontsize=6, loc="lower left")
    save(fig, "fig3_edge_vs_random")


def fig4_cost():
    p = pd.read_csv(RES / "pooled_edges_new.csv")
    p = p[(p.bench == "B1") & (p.grouping == "variant_tf") & (p.window == "OOS")]
    fig, axs = plt.subplots(1, 3, figsize=(6.4, 2.6), sharey=True)
    for ax, tf in zip(axs, ("1h", "4h", "1d")):
        q = p[p.group.str.endswith("|" + tf)].copy(); q["v"] = q.group.str.split("|").str[0]
        q = q.set_index("v").reindex(list(COL))
        x = np.arange(len(q))
        ax.bar(x, q.gross, color="#9dc3e6", label="gross")
        ax.bar(x, -q.mean_cost, bottom=q.gross, color="#c55a11", label="cost")
        ax.scatter(x, q.net, color="k", s=10, zorder=5, label="net")
        ax.set_xticks(x); ax.set_xticklabels(["V0", "V1", "V2", "V3", "V4"]); ax.set_title(tf); ax.axhline(0, color="k", lw=0.5)
    axs[0].set_ylabel("R per trade, last 40% of bars"); axs[0].legend(fontsize=6)
    save(fig, "fig6_gross_vs_cost")


def fig5_canonical():
    t = pd.read_parquet(V16 / "phase3_canonical_trades_tidy.parquet")
    t = t[~t.asset.str.startswith("MCX")].sort_values("exit")
    fig, ax = plt.subplots(figsize=(6.2, 2.8))
    for lad, c in zip(sorted(t.ladder.unique()), ("#1f4e79", "#c55a11", "#548235")):
        s = t[t.ladder == lad]
        ax.plot(s.exit, s.netR.cumsum(), lw=0.9, color=c, label=f"{lad} (net)")
        ax.plot(s.exit, s.grossR.cumsum(), lw=0.7, color=c, ls=":", label=f"{lad} (gross)")
    ax.set_ylabel("Cumulative R (sum over trades)"); ax.legend(fontsize=6, ncol=2); ax.axhline(0, color="k", lw=0.5)
    save(fig, "fig8_canonical_cumulative")


def fig6_forest():
    c = pd.read_csv(RES / "cells_FULL_tested_new.csv")
    c = c[c.variant.isin(["V0_raw", "V1_plain"])]
    order = c.groupby("asset").edge_B1.mean().sort_values().index
    fig, axs = plt.subplots(1, 2, figsize=(6.4, 3.4), sharey=True)
    for ax, v in zip(axs, ("V0_raw", "V1_plain")):
        q = c[c.variant == v]
        for tf, m in zip(("1h", "4h", "1d"), ("o", "s", "^")):
            qq = q[q.tf == tf]
            y = [list(order).index(a) for a in qq.asset]
            se = qq.B1_sd.to_numpy()
            ax.errorbar(qq.edge_B1, np.array(y) + {"1h": -0.2, "4h": 0, "1d": 0.2}[tf], xerr=1.96 * se, fmt=m, ms=2.5, lw=0.6, label=tf)
        ax.axvline(0, color="k", lw=0.6); ax.set_title(VN[v]); ax.set_xlabel("Gross edge over matched random (R per trade)")
        ax.set_yticks(range(len(order))); ax.set_yticklabels([a.replace("USDT", "") for a in order])
    axs[0].legend(fontsize=6, loc="lower right")
    save(fig, "fig4_edge_by_asset")


def fig7_years():
    r = pd.read_csv(RES / "regimes_new.csv")
    r = r[r.scheme == "year"]
    fig, axs = plt.subplots(1, 2, figsize=(6.4, 2.7), sharey=False)
    for ax, v in zip(axs, ("V0_raw", "V1_plain")):
        q = r[r.variant == v].sort_values("bucket")
        ax.errorbar(q.bucket, q.edge, yerr=[q.edge - q.lo, q.hi - q.edge], fmt="o-", ms=3, lw=0.8, capsize=1.5, color=COL[v])
        ax.axhline(0, color="k", lw=0.6); ax.set_title(VN[v] + ", all assets and timeframes"); ax.set_xlabel("signal year")
    axs[0].set_ylabel("Gross edge over matched random\n(random entries drawn from the same year)")
    save(fig, "fig5_edge_by_year")


def fig8_cost_sens():
    s = pd.read_csv(RES / "cost_sensitivity_new.csv")
    s = s[s.cls == "crypto"]
    fig, ax = plt.subplots(figsize=(4.2, 2.6))
    for v in list(COL) + ["ALL"]:
        q = s[s.variant == v]
        x = q.scenario.str.extract(r"([\d.]+)")[0].astype(float)
        ax.plot(x, q.net, marker="o", ms=3, lw=0.9, color=COL.get(v, "k"), label=VN.get(v, "all variants"))
    ax.axhline(0, color="k", lw=0.5); ax.set_xlabel("Cost per side (basis points of price), crypto"); ax.set_ylabel("Net R per trade (all bars)")
    ax.legend(fontsize=6)
    save(fig, "fig7_cost_sensitivity")


def fig9_power():
    p = pd.read_csv(RES / "pooled_edges_new.csv")
    a = p[(p.window == "FULL") & (p.bench == "B1") & (p.grouping == "all")].iloc[0]
    v = p[(p.window == "FULL") & (p.bench == "B1") & (p.grouping == "variant")]
    fig, ax = plt.subplots(figsize=(4.2, 2.6))
    d = np.linspace(0, 0.12, 200)
    for _, r in v.iterrows():
        pw = 1 - stats.norm.cdf(1.96 - d / r.edge_se) + stats.norm.cdf(-1.96 - d / r.edge_se)
        ax.plot(d, pw, lw=0.9, color=COL.get(r.group), label=VN.get(r.group, r.group))
    ax.axhline(0.8, color="k", lw=0.5, ls="--"); ax.set_xlabel("True gross edge over random (R per trade)"); ax.set_ylabel("Power (5% two-sided)")
    ax.legend(fontsize=6)
    save(fig, "figA4_power_curves")


def figA1_winrates():
    c = pd.read_csv(RES / "cells_FULL_tested_new.csv")
    fig, ax = plt.subplots(figsize=(4.8, 2.6))
    ax.hist(c.win_net * 100, bins=np.arange(15, 75, 2.5), color="#9dc3e6", edgecolor="w")
    ax.axvline(100 / 3, color="r", lw=1); ax.axvspan(70, 90, color="orange", alpha=0.25)
    ax.set_xlabel("Win rate after costs (%), cells with at least 30 trades"); ax.set_ylabel("Cells")
    save(fig, "figA1_win_rates")


def figA2_pvalues():
    c = pd.read_csv(RES / "cells_FULL_tested_new.csv")
    fig, axs = plt.subplots(1, 3, figsize=(6.4, 2.3), sharey=True)
    for ax, m in zip(axs, ("B0", "B1", "B2")):
        ax.hist(c[f"{m}_p_two"], bins=np.linspace(0, 1, 11), color="#9dc3e6", edgecolor="w"); ax.axhline(len(c) / 10, color="r", lw=0.8, ls="--")
        ax.set_title({"B0": "B0 (v16 benchmark)", "B1": "B1 (primary)", "B2": "B2 (+ volatility)"}[m]); ax.set_xlabel("two-sided p, gross edge")
    axs[0].set_ylabel("Cells")
    save(fig, "figA2_cell_pvalues")


def figA3_search_p():
    fig, axs = plt.subplots(1, 2, figsize=(6.4, 2.4), sharey=False)
    for ax, (f, ttl) in zip(axs, (("phase2_configs_compact.parquet", "Phase 2 (22,640 configurations)"), ("phase3_configs_compact.parquet", "Phase 3 (94,068 configurations)"))):
        d = pd.read_parquet(V16 / f)
        ax.hist(d.wf_p.dropna(), bins=np.linspace(0, 1, 21), color="#9dc3e6", edgecolor="w"); ax.set_title(ttl); ax.set_xlabel("one-sided p, net R per trade > 0")
        ax.axhline(len(d) / 20, color="r", lw=0.8, ls="--")
    axs[0].set_ylabel("Configurations")
    save(fig, "figA3_search_pvalues")


def figA4_spreads():
    f = RES / "duka_spread_by_year.csv"
    if not f.exists():
        return
    s = pd.read_csv(f)
    fig, axs = plt.subplots(1, 2, figsize=(6.0, 2.3))
    for ax, a in zip(axs, ("XAUUSD", "XAGUSD")):
        q = s[s.asset == a]
        ax.plot(q.year, q.median_usd, "o-", ms=3, lw=0.9, color="#1f4e79", label="Dukascopy median (June)")
        ax.axhline({"XAUUSD": 0.35, "XAGUSD": 0.035}[a], color="r", ls="--", lw=0.8, label="v16 constant")
        ax.set_title(a); ax.set_ylabel("USD per ounce"); ax.set_xlabel("year")
    axs[0].legend(fontsize=6)
    save(fig, "figA5_metal_spreads")


if __name__ == "__main__":
    which = sys.argv[1:] or ["1", "2", "3", "4", "5", "6", "7", "8", "9", "A1", "A2", "A3", "A4"]
    fn = {"1": fig1_schematic, "2": fig2_intrabar, "3": fig3_edge, "4": fig4_cost, "5": fig5_canonical, "6": fig6_forest, "7": fig7_years, "8": fig8_cost_sens,
          "9": fig9_power, "A1": figA1_winrates, "A2": figA2_pvalues, "A3": figA3_search_p, "A4": figA4_spreads}
    for w in which:
        fn[w]()
