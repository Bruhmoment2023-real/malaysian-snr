"""Paper-ready figures (PNG, 200 dpi) and remaining tables, built ONLY from stored result files and from the outputs of
01_reproduce_headlines.py and 02_intrabar_resolution_check.py. READ-ONLY on D:/Malaysian-SNR.
Run (about 1 min, after scripts 01 and 02):
  D:\\Malaysian-SNR\\.venv\\Scripts\\python.exe -B D:\\Research-Publishing\\02-malaysian-snr\\code\\04_figures_and_tables.py
"""
import json, glob, os
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = Path(r"D:/Malaysian-SNR"); OUT = Path(r"D:/Research-Publishing/02-malaysian-snr/results")
assert os.path.exists("D:/"), "D: offline"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 100})
VLAB = {"V0_raw": "V0 literal 2-candle", "V1_plain": "V1 pivot levels", "V2_story": "V2 + storyline", "V3_QM_story": "V3 Quasimodo", "V4_HTFlvl_story": "V4 higher-TF levels"}
TFS = ["1d", "4h", "1h"]

oos = pd.read_csv(SRC / "results" / "key_table_default_OOS.csv"); ins = pd.read_csv(SRC / "results" / "key_table_default_IS.csv")
pt = pd.read_csv(OUT / "table2_phase1_pooled_by_tf_variant.csv")

# ---- Fig 1: gross edge vs matched random entries, pooled, IS and OOS
fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
for ax, per in zip(axes, ("IS", "OOS")):
    d = pt[pt.period == per].copy(); d["edge"] = d.gross_R - d.rand_gross_R; d["se"] = (d.edge / d.z_gross_vs_random).abs()
    d["tf"] = pd.Categorical(d.tf, TFS); d = d.sort_values(["tf", "variant"]).reset_index(drop=True)
    y = np.arange(len(d))[::-1]
    col = d.tf.map({"1d": "#1b6ca8", "4h": "#3a9d5d", "1h": "#c0392b"})
    ax.errorbar(d.edge, y, xerr=1.96 * d.se, fmt="none", ecolor="grey", lw=1, capsize=2)
    ax.scatter(d.edge, y, c=col, s=28, zorder=3)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels([f"{t}  {VLAB[v]}" for t, v in zip(d.tf, d.variant)], fontsize=7.5)
    for yy, n in zip(y, d.trades): ax.text(0.44, yy + 0.3, f"n={n:,}", fontsize=6, va="center", ha="right", color="grey")
    ax.set_title(f"{'In-sample (first 60%)' if per == 'IS' else 'Out-of-sample (last 40%)'}")
    ax.set_xlim(-0.75, 0.45)
fig.suptitle("Figure 1. MSNR levels versus random entries with the same stop/target geometry (phase 1, before costs, pooled over assets)", fontsize=9.5)
fig.supxlabel("Gross R per trade: strategy minus matched random entries (95% interval)", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "fig1_gross_edge_vs_random.png", dpi=200); plt.close(fig)

# ---- Fig 2: where the loss comes from: gross vs cost, by timeframe and variant (OOS)
d = pt[pt.period == "OOS"].copy(); d["tf"] = pd.Categorical(d.tf, TFS); d = d.sort_values(["tf", "variant"]).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9, 4.2)); x = np.arange(len(d))
ax.bar(x, d.gross_R, color="#7f8c8d", label="gross R per trade (before costs)")
ax.bar(x, -d.avg_cost_R, bottom=d.gross_R, color="#c0392b", alpha=0.85, label="trading cost in R")
ax.scatter(x, d.net_R, color="k", zorder=3, s=14, label="net R per trade")
ax.scatter(x, d.rand_gross_R, marker="_", color="#1b6ca8", s=120, zorder=4, label="random entries, gross")
ax.axhline(0, color="k", lw=0.8); ax.set_xticks(x); ax.set_xticklabels([f"{t}\n{v.split('_')[0]}" for t, v in zip(d.tf, d.variant)], fontsize=7.5)
ax.set_ylabel("R per trade"); ax.legend(fontsize=7.5, loc="lower left")
ax.set_title("Figure 2. Out-of-sample result per trade split into gross outcome and cost (phase 1, default 2R target)", fontsize=9.5)
fig.tight_layout(); fig.savefig(OUT / "fig2_gross_vs_cost.png", dpi=200); plt.close(fig)

# ---- Fig 3: win rates against the break-even rate
big = oos[oos.trades >= 30]
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.hist(big.win_rate * 100, bins=np.arange(16, 44, 2), color="#7f8c8d", edgecolor="white")
ax.axvline(100 / 3, color="#c0392b", lw=1.5, label="break-even before costs at a 2R target (33.3%)")
ax.axvline(80, color="#1b6ca8", lw=1.2, ls="--")
ax.set_xlim(14, 86); ax.text(80, ax.get_ylim()[1] * 0.9, "claimed\n80-90%", ha="center", va="top", fontsize=8, color="#1b6ca8")
ax.set_xlabel("Win rate after costs, % (out-of-sample cells with at least 30 trades)"); ax.set_ylabel("number of asset/timeframe/variant cells")
ax.legend(fontsize=7.5, loc="upper center"); ax.set_title(f"Figure 3. Measured win rates in {len(big)} out-of-sample cells (median {big.win_rate.median() * 100:.1f}%)", fontsize=9.5)
fig.tight_layout(); fig.savefig(OUT / "fig3_win_rates.png", dpi=200); plt.close(fig)

# ---- Fig 4: does a cell's in-sample edge over random persist out of sample?
m = ins.merge(oos, on=["asset", "tf", "variant"], suffixes=("_is", "_oos")).dropna(subset=["gross_edge_vs_random_R_is", "gross_edge_vs_random_R_oos"])
m = m[(m.trades_is >= 30) & (m.trades_oos >= 30)]
rho = m.gross_edge_vs_random_R_is.corr(m.gross_edge_vs_random_R_oos, method="spearman")
fig, ax = plt.subplots(figsize=(5.2, 4.6))
for tf, c in (("1d", "#1b6ca8"), ("4h", "#3a9d5d"), ("1h", "#c0392b")):
    k = m[m.tf == tf]; ax.scatter(k.gross_edge_vs_random_R_is, k.gross_edge_vs_random_R_oos, s=18, c=c, label=tf, alpha=0.8)
ax.axhline(0, color="k", lw=0.6); ax.axvline(0, color="k", lw=0.6)
ax.set_xlabel("In-sample gross edge over random (R)"); ax.set_ylabel("Out-of-sample gross edge over random (R)"); ax.legend(title="timeframe", fontsize=8)
ax.set_title(f"Figure 4. Cell-level edge over random: first 60% vs last 40%\n(n={len(m)} cells, >=30 trades in both halves; Spearman rho={rho:.2f}; cells not independent)", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "fig4_is_vs_oos_edge.png", dpi=200); plt.close(fig)
pd.DataFrame([dict(cells=len(m), spearman_rho=rho, pearson_r=m.gross_edge_vs_random_R_is.corr(m.gross_edge_vs_random_R_oos),
                   same_sign_share=float((np.sign(m.gross_edge_vs_random_R_is) == np.sign(m.gross_edge_vs_random_R_oos)).mean()))]).to_csv(OUT / "fig4_stats.csv", index=False)

# ---- Fig 5: canonical top-down method by cell (phase 3)
can = pd.read_csv(OUT / "table4_phase3_canonical_by_cell.csv")
lad = ["W-D-4H-1H", "D-4H-1H-15m", "4H-1H-15m-5m"]; can["ladder"] = pd.Categorical(can.ladder, lad)
can = can.sort_values(["ladder", "asset"]).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(10, 4.4)); x = np.arange(len(can)); syn = can.asset.eq("MCXGOLD_SYN")
ax.bar(x - 0.2, can.wf_grossR, 0.4, color=np.where(syn, "#d5d8dc", "#7f8c8d"), label="gross R per trade")
ax.bar(x + 0.2, can.wf_netR, 0.4, color=np.where(syn, "#f5b7b1", "#c0392b"), label="net R per trade")
ax.scatter(x + 0.2, can.rand_netR, marker="_", s=110, color="k", zorder=4, label="random entries, net")
ax.axhline(0, color="k", lw=0.8); ax.set_xticks(x)
ax.set_xticklabels([f"{a.replace('USDT', '').replace('MCXGOLD_SYN', 'MCX*')}\nn={n}" for a, n in zip(can.asset, can.wf_n)], fontsize=7)
for i, l in enumerate(lad):
    ax.text(i * 6 + 2.5, ax.get_ylim()[1] * 0.97, f"ladder {l}", ha="center", va="top", fontsize=8.5)
    if i: ax.axvline(i * 6 - 0.5, color="grey", lw=0.6, ls=":")
ax.set_ylabel("R per trade (walk-forward)"); ax.legend(fontsize=7.5, loc="lower left")
ax.set_title("Figure 5. Canonical top-down MSNR by asset and timeframe ladder (phase 3). *MCX = synthetic proxy, shown pale, excluded from pooled figures", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "fig5_canonical_by_cell.png", dpi=200); plt.close(fig)

# ---- Fig 6: cumulative R of the canonical method, real-data cells
T = pd.read_parquet(OUT / "phase3_canonical_trades_tidy.parquet"); T = T[T.asset != "MCXGOLD_SYN"].sort_values("exit")
fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=False)
for ax, l in zip(axes, lad):
    k = T[T.ladder == l]
    ax.plot(k.exit, k.grossR.cumsum(), color="#7f8c8d", lw=1, label="gross")
    ax.plot(k.exit, k.netR.cumsum(), color="#c0392b", lw=1, label="net of costs")
    hs = k.exit[k.hold].min()
    if pd.notna(hs): ax.axvline(hs, color="k", ls="--", lw=0.7); ax.text(hs, ax.get_ylim()[0], " holdout", fontsize=7, va="bottom")
    ax.axhline(0, color="k", lw=0.6); ax.set_title(f"{l}  (n={len(k):,})", fontsize=9); ax.tick_params(axis="x", labelsize=7)
axes[0].set_ylabel("cumulative R (5 real instruments pooled)"); axes[0].legend(fontsize=7.5)
fig.suptitle("Figure 6. Cumulative result of the canonical top-down method, in units of risk (phase 3)", fontsize=9.5)
fig.tight_layout(); fig.savefig(OUT / "fig6_canonical_cumulative_R.png", dpi=200); plt.close(fig)

# ---- Fig 7: p-value distributions of the searched configurations
a2 = pd.read_parquet(OUT / "phase2_configs_compact.parquet"); a3 = pd.read_parquet(OUT / "phase3_configs_compact.parquet")
fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
for ax, a, nm in ((axes[0], a2, "Phase 2: 22,640 MSNR + confluence configurations"), (axes[1], a3, "Phase 3: 94,068 top-down MSNR configurations")):
    p = a.wf_p.dropna(); ax.hist(p, bins=20, range=(0, 1), color="#7f8c8d", edgecolor="white")
    ax.axhline(len(p) / 20, color="#1b6ca8", ls="--", lw=1, label="flat line expected if every rule had zero net edge")
    ax.set_xlabel("one-sided p-value for 'net R per trade > 0' (walk-forward)"); ax.set_ylabel("configurations"); ax.set_title(nm, fontsize=9)
    ax.text(0.03, 0.82, f"p<0.05: {(p < 0.05).sum():,} observed\n{0.05 * len(p):,.0f} expected by chance", transform=ax.transAxes, fontsize=7.5)
    ax.legend(fontsize=7, loc="upper center")
fig.suptitle("Figure 7. The searched variants are not a noisy mix of winners and losers: almost all are reliably negative after costs", fontsize=9.5)
fig.tight_layout(); fig.savefig(OUT / "fig7_pvalue_histograms.png", dpi=200); plt.close(fig)

# ---- Fig 8: robustness R1, intrabar resolution
f8 = OUT / "robustness_R1_intrabar_pooled.csv"
if f8.exists():
    r = pd.read_csv(f8); r = r[(r.period.isin(["IS", "OOS"])) & r.variant.isin(["V0_raw", "V1_plain"]) & r.tf.isin(["1h", "4h"])]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), sharey=True)
    for ax, k in zip(axes, ("coarse", "5m")):
        lab = [f"{t} {v.split('_')[0]} {p}" for t, v, p in zip(r.tf, r.variant, r.period)]; x = np.arange(len(r))
        ax.bar(x - 0.2, r.strat_gross_coarse if k == "coarse" else r.strat_gross_5m, 0.4, color="#c0392b", label="MSNR entries")
        ax.bar(x + 0.2, r[f"rand_gross_{k}"], 0.4, color="#1b6ca8", label="random entries")
        ax.axhline(0, color="k", lw=0.8); ax.set_xticks(x); ax.set_xticklabels(lab, rotation=60, fontsize=7, ha="right")
        ax.set_title("stop/target order decided on the trade bar (stop first)" if k == "coarse" else "order resolved on 5-minute bars", fontsize=9)
        for xi, z in zip(x, r[f"z_{k}"]): ax.text(xi, 0.045, f"z={z:+.1f}", ha="center", fontsize=6.5)
    axes[0].set_ylabel("gross R per trade (BTC, ETH, SOL pooled)"); axes[0].legend(fontsize=7.5, loc="lower left"); axes[0].set_ylim(-0.11, 0.06)
    fig.suptitle("Figure 8. Robustness: the 'stop first' rule lowers both strategy and benchmark by 0.03-0.07 R; the gap between them barely moves", fontsize=9.5)
    fig.tight_layout(); fig.savefig(OUT / "fig8_intrabar_resolution.png", dpi=200); plt.close(fig)

# ---- Table 1b: phase-3 data windows
rows = []
for f in sorted(glob.glob(str(SRC / "phase3" / "results" / "A3" / "*.json"))):
    a = json.load(open(f))["bh"]; b = json.load(open(f.replace("A3", "B3")))["bh"]
    rows.append(dict(asset=a["asset"], ladder=a["ladder"], wf_start=a["wf_start"][:10], holdout_start=b["hold_start"][:10], holdout_end=b["hold_end"][:10],
                     configs_evaluated=a["n_configs"], BH_CAGR_wf=round(a["BH_CAGR"], 4), BH_return_holdout=round(b["BH_hold_return"], 4)))
pd.DataFrame(rows).to_csv(OUT / "table1b_phase3_data_windows.csv", index=False)

# ---- Table 7: cost assumptions as coded
pd.DataFrame([
    dict(phase="1", instrument="BTC/ETH/SOL (Binance spot bars)", entry_cost="0.07% of price", exit_cost="0.07% of price", carry_per_year="2%", source="backtest/run_all.py ASSETS"),
    dict(phase="1", instrument="PAXG (Binance)", entry_cost="0.10%", exit_cost="0.10%", carry_per_year="2%", source="backtest/run_all.py ASSETS"),
    dict(phase="1", instrument="Gold futures GC=F (Yahoo)", entry_cost="$0.40 per oz round trip, charged once", exit_cost="-", carry_per_year="3%", source="backtest/run_all.py ASSETS"),
    dict(phase="1", instrument="Silver futures SI=F (Yahoo)", entry_cost="$0.04 per oz round trip", exit_cost="-", carry_per_year="3%", source="backtest/run_all.py ASSETS"),
    dict(phase="2-3", instrument="BTC/ETH/SOL", entry_cost="market 0.07%; limit 0.02%", exit_cost="target 0.02%; stop 0.07%", carry_per_year="2%", source="phase2/p2common.py CRYPTO; phase3/p3common.py CRYPTO"),
    dict(phase="2", instrument="PAXG", entry_cost="market 0.15%; limit 0.075%", exit_cost="target 0.075%; stop 0.15%", carry_per_year="2%", source="phase2/p2common.py PAXG"),
    dict(phase="2-3", instrument="Gold (GC=F in phase 2; XAUUSD bid bars in phase 3)", entry_cost="market $0.35; limit $0.30", exit_cost="target $0; stop $0.05", carry_per_year="3%", source="p2common.py GOLD; p3common.py XAU"),
    dict(phase="2-3", instrument="Silver (SI=F; XAGUSD bid bars)", entry_cost="market $0.035; limit $0.030", exit_cost="target $0; stop $0.005", carry_per_year="3%", source="p2common.py SILV; p3common.py XAG"),
    dict(phase="3", instrument="Synthetic MCX gold proxy (exclude from paper)", entry_cost="0.0136%", exit_cost="target 0.0086%; stop 0.0186%", carry_per_year="0%", source="phase3/p3common.py MCX"),
]).to_csv(OUT / "table7_cost_assumptions_as_coded.csv", index=False)
print("figures and tables written to", OUT)
