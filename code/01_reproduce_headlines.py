"""Recompute headline numbers of the Malaysian-SNR study directly from stored result files.
READ-ONLY on D:/Malaysian-SNR. Writes only to D:/Research-Publishing/02-malaysian-snr/results.
Run:  D:\\Malaysian-SNR\\.venv\\Scripts\\python.exe -B D:\\Research-Publishing\\02-malaysian-snr\\code\\01_reproduce_headlines.py
Runtime: about 1-2 minutes (reads a 56 MB and a 12 MB CSV from a USB disk).
"""
import json, zlib, glob, os
from pathlib import Path
import numpy as np, pandas as pd

SRC = Path(r"D:/Malaysian-SNR")
OUT = Path(r"D:/Research-Publishing/02-malaysian-snr/results"); OUT.mkdir(parents=True, exist_ok=True)
assert os.path.exists("D:/"), "D: offline"
rows = []


def rec(phase, item, reported, recomputed, source, note=""):
    rows.append(dict(phase=phase, item=item, reported=reported, recomputed=recomputed, source_file=source, note=note))
    print(f"[{phase}] {item}: reported={reported} recomputed={recomputed} {note}", flush=True)


def bh_q(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p); q = np.empty(n)
    c = p[o] * n / np.arange(1, n + 1); c = np.minimum.accumulate(c[::-1])[::-1]; q[o] = np.minimum(c, 1.0)
    return q


# ---------------------------------------------------------------- PHASE 1
R1 = SRC / "results"
oos = pd.read_csv(R1 / "key_table_default_OOS.csv"); ins = pd.read_csv(R1 / "key_table_default_IS.csv")
full = pd.read_csv(R1 / "key_table_default_FULL.csv"); pooled = pd.read_csv(R1 / "pooled_by_tf_variant.csv")
tr = pd.read_csv(R1 / "trades_default_full.csv")
rec("P1", "trades in trades_default_full.csv", "n/a", len(tr), "trades_default_full.csv")

# (a) cell-level FULL table from the raw trades
g = tr.groupby(["asset", "tf", "variant"]).agg(trades=("netR", "size"), avg_R=("netR", "mean"), gross=("grossR", "mean"),
                                                 win=("netR", lambda x: (x > 0).mean()), long_share=("dir", lambda x: (x > 0).mean())).reset_index()
m = full.merge(g, on=["asset", "tf", "variant"], suffixes=("_rep", "_re"), how="outer")
m["d_trades"] = m.trades_rep - m.trades_re; m["d_avgR"] = (m.avg_R_rep - m.avg_R_re).abs()
m["d_gross"] = (m.gross_avg_R - m.gross).abs()
rec("P1", "FULL-period cells: n cells", len(full), len(g), "key_table_default_FULL.csv vs trades", "cells compared")
rec("P1", "FULL-period cells: max |trade-count diff|", 0, float(m.d_trades.abs().max()), "same")
rec("P1", "FULL-period cells: max |net avg R diff|", 0, round(float(m.d_avgR.max()), 5), "same", "CSV rounded to 4 dp / 6 sig figs")
rec("P1", "FULL-period cells: max |gross avg R diff|", 0, round(float(m.d_gross.max()), 5), "same")
m.to_csv(OUT / "check_phase1_full_cells_vs_trades.csv", index=False)

# (b) headline counts
rec("P1", "OOS cells total", 95, len(oos), "key_table_default_OOS.csv")
rec("P1", "OOS cells losing money (avg_R<0)", 84, int((oos.avg_R < 0).sum()), "same", f"zero-trade/NaN cells: {int(oos.avg_R.isna().sum())}; avg_R>0: {int((oos.avg_R > 0).sum())}")
big = oos[oos.trades >= 30]
rec("P1", "OOS cells with >=30 trades", 73, len(big), "same")
rec("P1", "OOS cells >=30 trades and net positive", 4, int((big.avg_R > 0).sum()), "same",
    "; ".join(f"{a} {t} {v} {r:+.3f} (n={n})" for a, t, v, r, n in big[big.avg_R > 0][["asset", "tf", "variant", "avg_R", "trades"]].itertuples(index=False)))
hasp = oos.dropna(subset=["p_gross_vs_random"])
rec("P1", "OOS cells with a random baseline", 89, len(hasp), "same")
rec("P1", "OOS cells gross beating random at p<0.05 (one-sided)", 3, int((hasp.p_gross_vs_random < 0.05).sum()), "same",
    f"expected by chance {0.05 * len(hasp):.2f}; BH min q = {bh_q(hasp.p_gross_vs_random).min():.3f}")
rec("P1", "OOS cells gross WORSE than random at p>0.95", "n/a", int((hasp.p_gross_vs_random > 0.95).sum()), "same", "lower tail, same expectation")
rec("P1", "OOS win-rate range, cells >=30 trades", "25-38%", f"{big.win_rate.min():.3f}-{big.win_rate.max():.3f}", "same",
    f"median {big.win_rate.median():.3f}; share within 0.25-0.38: {((big.win_rate >= 0.25) & (big.win_rate <= 0.38)).mean():.2f}")

# (c) pooled table recomputed from cells
def zpool(x):
    x = x.dropna(subset=["rand_gross_R", "rand_gross_sd"])
    den = np.sqrt((x.trades ** 2 * x.rand_gross_sd ** 2).sum())
    return (x.trades * (x.gross_avg_R - x.rand_gross_R)).sum() / den if den > 0 else np.nan

pt = []
for per, df in (("IS", ins), ("OOS", oos)):
    for (tf, v), x in df.groupby(["tf", "variant"]):
        w = x.trades.clip(lower=1e-9)
        xx = x.dropna(subset=["rand_gross_R"])
        pt.append(dict(period=per, tf=tf, variant=v, trades=int(x.trades.sum()), n_cells=int((x.trades > 0).sum()),
                       net_R=np.average(x.avg_R.fillna(0), weights=w), gross_R=np.average(x.gross_avg_R.fillna(0), weights=w),
                       rand_gross_R=np.average(x.rand_gross_R.fillna(0), weights=w), z_gross_vs_random=zpool(x),
                       win_rate=np.average(x.win_rate.fillna(0), weights=w), avg_cost_R=np.average(x.avg_cost_R.fillna(0), weights=w),
                       cells_net_pos=int((x.avg_R > 0).sum()), cells_beat_random_p05=int((x.p_gross_vs_random < 0.05).sum())))
pt = pd.DataFrame(pt)
pt["tf"] = pd.Categorical(pt.tf, ["1d", "4h", "1h"]); pt = pt.sort_values(["period", "tf", "variant"]).reset_index(drop=True)
pt.round(4).to_csv(OUT / "table2_phase1_pooled_by_tf_variant.csv", index=False)
chk = pt.merge(pooled[pooled.which == "default"], on=["period", "tf", "variant"], suffixes=("", "_stored"))
rec("P1", "pooled table: max |net R diff| vs stored", 0, round(float((chk.net_R - chk.wavg_R).abs().max()), 5), "pooled_by_tf_variant.csv")
rec("P1", "pooled table: max |z diff| vs stored", 0, round(float((chk.z_gross_vs_random - chk.pooled_gross_edge_z).abs().max()), 4), "same")
for tf, v, rep_net, rep_z in (("1h", "V0_raw", -0.680, 2.60), ("1h", "V2_story", -0.582, 0.06), ("4h", "V3_QM_story", -0.495, -2.39), ("1d", "V3_QM_story", -0.573, -2.26), ("1d", "V1_plain", -0.095, 0.45)):
    r = pt[(pt.period == "OOS") & (pt.tf == tf) & (pt.variant == v)].iloc[0]
    rec("P1", f"OOS pooled {tf} {v} net R / z", f"{rep_net} / {rep_z}", f"{r.net_R:.3f} / {r.z_gross_vs_random:.2f}", "key_table_default_OOS.csv", f"n={r.trades}")
r = pt[(pt.period == "IS") & (pt.tf == "1h") & (pt.variant == "V0_raw")].iloc[0]
rec("P1", "IS pooled 1h V0 z vs random", 7.3, round(r.z_gross_vs_random, 2), "key_table_default_IS.csv", f"gross edge {r.gross_R - r.rand_gross_R:+.4f} R, cost {r.avg_cost_R:.3f} R")
r = pt[(pt.period == "OOS") & (pt.tf == "1h") & (pt.variant == "V0_raw")].iloc[0]
rec("P1", "OOS pooled 1h V0 gross edge vs random (R) and avg cost (R)", "+0.03..+0.06 / 0.4-0.7", f"{r.gross_R - r.rand_gross_R:+.4f} / {r.avg_cost_R:.3f}", "key_table_default_OOS.csv")
x = oos[(oos.asset == "GC=F_D2011") & (oos.variant == "V1_plain")].iloc[0]
rec("P1", "Gold daily OOS V1: net R / trades / PF", "+0.095 / 130 / 1.15", f"{x.avg_R:+.3f} / {int(x.trades)} / {x.PF:.2f}", "key_table_default_OOS.csv", f"p_gross_vs_random={x.p_gross_vs_random:.3f}")
x = ins[(ins.asset == "GC=F_D2011") & (ins.variant == "V1_plain")].iloc[0]
rec("P1", "Gold daily IS V1: net R", -0.30, round(x.avg_R, 3), "key_table_default_IS.csv", f"n={int(x.trades)}")
# all-variant pooled, OOS
rec("P1", "ALL OOS trades pooled: n / net R / gross R / random gross R", "n/a",
    f"{int(oos.trades.sum())} / {np.average(oos.avg_R.fillna(0), weights=oos.trades):.4f} / {np.average(oos.gross_avg_R.fillna(0), weights=oos.trades):.4f} / "
    f"{np.average(hasp.rand_gross_R, weights=hasp.trades):.4f}", "key_table_default_OOS.csv", f"overall z vs random {zpool(oos):.2f}")
# long share (benchmark direction match)
ls = tr.groupby("variant").dir.apply(lambda x: (x > 0).mean()).round(4).to_dict()
rec("P1", "share of LONG trades by variant (full period)", "not reported", json.dumps(ls), "trades_default_full.csv", "random benchmark uses 50/50 for V0/V1")
lsc = tr[tr.variant.isin(["V0_raw", "V1_plain"])].groupby(["asset", "tf", "variant"]).dir.apply(lambda x: (x > 0).mean())
rec("P1", "V0/V1 per-cell long share min-max", "not reported", f"{lsc.min():.3f}-{lsc.max():.3f}", "trades_default_full.csv")
# data inventory
inv = full.groupby(["asset", "tf"]).agg(start=("start", "first"), end=("end", "first")).reset_index()
inv = inv.merge(oos.groupby(["asset", "tf"]).agg(oos_start=("start", "first"), BH_CAGR_oos=("BH_CAGR", "first")).reset_index(), on=["asset", "tf"])
inv.to_csv(OUT / "table1a_phase1_data_inventory.csv", index=False)
# per-cell paper table
cell = oos[["asset", "tf", "variant", "start", "end", "trades", "win_rate", "avg_R", "gross_avg_R", "avg_cost_R", "PF", "rand_gross_R", "rand_gross_sd", "p_gross_vs_random", "CAGR", "BH_CAGR"]].copy()
cell = cell.merge(ins[["asset", "tf", "variant", "trades", "avg_R", "gross_avg_R"]], on=["asset", "tf", "variant"], suffixes=("", "_IS"))
cell.to_csv(OUT / "table3_phase1_cells_OOS.csv", index=False)

# ---------------------------------------------------------------- PHASE 2
R2 = SRC / "phase2" / "results"
a2 = pd.read_csv(R2 / "all_configs_phaseA.csv", low_memory=False)
rec("P2", "configs", 22640, len(a2), "all_configs_phaseA.csv")
rec("P2", "configs with one-sided t-test p<0.05", 138, int((a2.wf_p < 0.05).sum()), "same", f"expected under global null {0.05 * len(a2):.0f}")
rec("P2", "configs with stored q_BH<0.10", 3, int((a2.q_BH < 0.10).sum()), "same",
    "; ".join(f"{r.cell} n={int(r.wf_n)}" for r in a2[a2.q_BH < 0.10].itertuples()))
q = bh_q(a2.wf_p.fillna(1.0).to_numpy())
rec("P2", "configs with recomputed global BH q<0.10", 3, int((q < 0.10).sum()), "same", f"max |q diff| vs stored {np.nanmax(np.abs(q - a2.q_BH.to_numpy())):.4f}")
rec("P2", "BH survivors that also have >=100 WF trades", 0, int(((q < 0.10) & (a2.wf_n >= 100)).sum()), "same")
rec("P2", "configs with DSR>0.95", 0, int((a2.DSR > 0.95).sum()), "same", f"max DSR {a2.DSR.max():.4f}")
rec("P2", "min Reality-Check p / min SPA p over 20 cells", "none significant", f"{a2.cell_p_RC.min():.3f} / {a2.cell_p_SPA.min():.3f}", "same")
rec("P2", "configs meeting all six criteria (WIN)", 0, int(a2.WIN.astype(str).eq('True').sum()), "same", "criteria histogram " + json.dumps(a2.criteria_met.value_counts().sort_index().to_dict()))
b = a2[(a2.tag == "base") & (a2.base == "V1")]
rec("P2", "MSNR solo fixed V1 2R: WF trades / net R", "66,274 / -0.519", f"{int(b.wf_n.sum())} / {np.average(b.wf_netR, weights=b.wf_n):.3f}", "same")
rec("P2", "MSNR solo fixed V1 2R: holdout trades / net R", "13,079 / -0.599", f"{int(b.hold_n.sum())} / {np.average(b.hold_netR.fillna(0), weights=b.hold_n.fillna(0)):.3f}", "same")
rec("P2", "MSNR solo fixed V1 2R: WF gross R / random gross R", "not reported", f"{np.average(b.wf_grossR, weights=b.wf_n):.4f} / {np.average(b.rand_grossR, weights=b.wf_n):.4f}", "same",
    f"cells gross-beating random p<0.05: {int((b.p_gross_vs_random < 0.05).sum())}/20")
b[["asset", "tf", "wf_n", "wf_netR", "wf_grossR", "wf_win", "rand_netR", "rand_grossR", "p_vs_random", "p_gross_vs_random", "hold_n", "hold_netR", "hold_grossR"]].to_csv(OUT / "table3b_phase2_V1_fixed_by_cell.csv", index=False)

# ---------------------------------------------------------------- PHASE 3
R3 = SRC / "phase3" / "results"
a3 = pd.read_csv(R3 / "msnr_all_configs.csv", low_memory=False)
rec("P3", "MSNR configs", 94068, len(a3), "msnr_all_configs.csv")
rec("P3", "criteria histogram", "0:7720 1:77974 2:5990 3:2325 4:55 5:4", json.dumps(a3.criteria_met.value_counts().sort_index().to_dict()), "same")
rec("P3", "configs passing all six", 0, int(a3.WIN.astype(str).eq('True').sum()), "same")
q3 = bh_q(a3.wf_p.fillna(1.0).to_numpy())
rec("P3", "configs with p<0.05 (one-sided t)", "not reported", int((a3.wf_p < 0.05).sum()), "same", f"expected under global null {0.05 * len(a3):.0f}")
rec("P3", "min BH q (stored / recomputed global)", "~1", f"{a3.q_BH.min():.4f} / {q3.min():.4f}", "same", f"configs q<0.10 stored {int((a3.q_BH < 0.10).sum())}, recomputed {int((q3 < 0.10).sum())}")
rec("P3", "BH survivors with >=100 WF trades", 0, int(((q3 < 0.10) & (a3.wf_n >= 100)).sum()), "same")
rec("P3", "max DSR (all) / max DSR (>=100 trades)", "~0", f"{a3.DSR.max():.4f} / {a3.loc[a3.wf_n >= 100, 'DSR'].max():.4f}", "same")
rec("P3", "min RC p / min SPA p over 18 cells", "not reported", f"{a3.cell_p_RC.min():.3f} / {a3.cell_p_SPA.min():.3f}", "same")
noMCX = a3[a3.asset != "MCXGOLD_SYN"]; qn = bh_q(noMCX.wf_p.fillna(1.0).to_numpy())
rec("P3", "excluding synthetic MCX proxy: configs / p<0.05 / BH q<0.10 / max DSR(>=100tr)", "n/a",
    f"{len(noMCX)} / {int((noMCX.wf_p < 0.05).sum())} / {int((qn < 0.10).sum())} / {noMCX.loc[noMCX.wf_n >= 100, 'DSR'].max():.4f}", "same")
can = pd.read_csv(R3 / "msnr_canonical_by_cell.csv")
rec("P3", "canonical pooled WF: trades / net R (trade-weighted)", "9,155 / -0.496", f"{int(can.wf_n.sum())} / {np.average(can.wf_netR, weights=can.wf_n):.3f}", "msnr_canonical_by_cell.csv",
    f"gross {np.average(can.wf_grossR, weights=can.wf_n):+.4f}; unweighted cell mean net {can.wf_netR.mean():.3f}")
rec("P3", "canonical pooled holdout: trades / net R", "1,262 / -0.325", f"{int(can.hold_n.sum())} / {np.average(can.hold_netR, weights=can.hold_n):.3f}", "same")
rec("P3", "canonical cells WF-positive / beating random p<0.05", "2 / 1", f"{int((can.wf_netR > 0).sum())} / {int((can.p_vs_random < 0.05).sum())}", "same")
c15 = can[can.asset != "MCXGOLD_SYN"]
rec("P3", "canonical, 15 real-data cells only: WF trades / net / gross", "n/a", f"{int(c15.wf_n.sum())} / {np.average(c15.wf_netR, weights=c15.wf_n):.3f} / {np.average(c15.wf_grossR, weights=c15.wf_n):+.4f}", "same",
    f"holdout {int(c15.hold_n.sum())} / {np.average(c15.hold_netR, weights=c15.hold_n):.3f}; cells WF-pos {int((c15.wf_netR > 0).sum())}")
c15x = c15[c15.asset != "XAGUSD"]
rec("P3", "canonical, excl. MCX proxy and silver: WF trades / net / gross", "n/a", f"{int(c15x.wf_n.sum())} / {np.average(c15x.wf_netR, weights=c15x.wf_n):.3f} / {np.average(c15x.wf_grossR, weights=c15x.wf_n):+.4f}", "same", "silver's cost per trade dominates the pooled figure")
can.to_csv(OUT / "table4_phase3_canonical_by_cell.csv", index=False)

# independent recomputation from the stored canonical TRADE arrays (phase B: WF start -> end of data)
CANON = "depth=3|gaps=0|story=td|conf=either|stop=zone|tgt=3R|rb=1|liq=0|miss=0|sess=0|xf="
crc = zlib.crc32(CANON.encode()) % 10 ** 8
tt = []
for f in sorted(glob.glob(str(R3 / "B3" / f"trades_*_{crc}.npy"))):
    tag = os.path.basename(f)[len("trades_"):-len(f"_{crc}.npy")]
    asset, ladder = tag.rsplit("_", 1)
    t = np.load(f); ex = np.load(f.replace("trades_", "exits_"))
    hs = pd.Timestamp(json.load(open(R3 / "B3" / f"{tag}.json"))["bh"]["hold_start"]).tz_convert(None)
    d = pd.DataFrame(dict(asset=asset, ladder=ladder, exit=pd.to_datetime(ex), dir=t[:, 3], grossR=t[:, 7], costR=t[:, 8], tgtR=t[:, 10], kind=t[:, 11]))
    d["netR"] = d.grossR - d.costR; d["hold"] = d.exit >= hs
    tt.append(d)
T = pd.concat(tt, ignore_index=True)
T.to_parquet(OUT / "phase3_canonical_trades_tidy.parquet")
rec("P3", "canonical trade arrays found (cells)", 18, T.groupby(["asset", "ladder"]).ngroups, "B3/trades_*.npy", f"crc {crc}")
w = T[~T.hold]; h = T[T.hold]
rec("P3", "canonical from raw trades, exit before holdout: n / net R / gross R", "9,155 / -0.496", f"{len(w)} / {w.netR.mean():.3f} / {w.grossR.mean():+.4f}", "B3/trades_*.npy",
    "continuous run split by exit time; phase A ran fold-by-fold, so counts differ slightly")
rec("P3", "canonical from raw trades, exit in holdout: n / net R", "1,262 / -0.325", f"{len(h)} / {h.netR.mean():.3f}", "same")
rec("P3", "canonical WF win rate / break-even win rate at 3R", "not reported", f"{(w.grossR > 0).mean():.3f} / 0.250", "same", f"TP-hit share {w.kind.mean():.3f}")
rec("P3", "canonical WF long share", "not reported", round(float((w.dir > 0).mean()), 3), "same")
se = w.netR.std(ddof=1) / np.sqrt(len(w))
rec("P3", "canonical WF net R: mean, 95% CI (iid trades)", "n/a", f"{w.netR.mean():.3f} [{w.netR.mean() - 1.96 * se:.3f}, {w.netR.mean() + 1.96 * se:.3f}]", "same")
seg = w.grossR.std(ddof=1) / np.sqrt(len(w))
rec("P3", "canonical WF GROSS R: mean, 95% CI (iid trades)", "n/a", f"{w.grossR.mean():.3f} [{w.grossR.mean() - 1.96 * seg:.3f}, {w.grossR.mean() + 1.96 * seg:.3f}]", "same")
w15 = w[w.asset != "MCXGOLD_SYN"]; seg = w15.grossR.std(ddof=1) / np.sqrt(len(w15))
rec("P3", "canonical WF GROSS R, 15 real cells: mean, 95% CI", "n/a", f"{w15.grossR.mean():.3f} [{w15.grossR.mean() - 1.96 * seg:.3f}, {w15.grossR.mean() + 1.96 * seg:.3f}] n={len(w15)}", "same")
abl = pd.read_csv(R3 / "msnr_ablations.csv")
rec("P3", "best ablation mean WF net R (>=18 cells)", -0.22, round(float(abl[abl.cells == 18].mean_wf_netR.max()), 3), "msnr_ablations.csv", "the -0.216 row covers only 3 cells (gap levels, MCX proxy)")
abl.to_csv(OUT / "table6_phase3_ablations.csv", index=False)

# multiple-testing summary table
mt = pd.DataFrame([
    dict(study="Phase 2: MSNR x 31 confluences x exits (20 cells)", configs=len(a2), p_lt_05=int((a2.wf_p < 0.05).sum()), expected_p_lt_05=round(0.05 * len(a2)),
         bh_q_lt_10=int((q < 0.10).sum()), bh_q_lt_10_min100trades=int(((q < 0.10) & (a2.wf_n >= 100)).sum()), max_DSR=a2.DSR.max(), max_DSR_min100=a2.loc[a2.wf_n >= 100, "DSR"].max(),
         min_RC_p=a2.cell_p_RC.min(), min_SPA_p=a2.cell_p_SPA.min(), all_six=0),
    dict(study="Phase 3: top-down MSNR (18 cells incl. 3 synthetic)", configs=len(a3), p_lt_05=int((a3.wf_p < 0.05).sum()), expected_p_lt_05=round(0.05 * len(a3)),
         bh_q_lt_10=int((q3 < 0.10).sum()), bh_q_lt_10_min100trades=int(((q3 < 0.10) & (a3.wf_n >= 100)).sum()), max_DSR=a3.DSR.max(), max_DSR_min100=a3.loc[a3.wf_n >= 100, "DSR"].max(),
         min_RC_p=a3.cell_p_RC.min(), min_SPA_p=a3.cell_p_SPA.min(), all_six=0),
    dict(study="Phase 3 excluding synthetic MCX proxy (15 cells)", configs=len(noMCX), p_lt_05=int((noMCX.wf_p < 0.05).sum()), expected_p_lt_05=round(0.05 * len(noMCX)),
         bh_q_lt_10=int((qn < 0.10).sum()), bh_q_lt_10_min100trades=int(((qn < 0.10) & (noMCX.wf_n >= 100)).sum()), max_DSR=noMCX.DSR.max(), max_DSR_min100=noMCX.loc[noMCX.wf_n >= 100, "DSR"].max(),
         min_RC_p=noMCX.cell_p_RC.min(), min_SPA_p=noMCX.cell_p_SPA.min(), all_six=0)])
mt.round(4).to_csv(OUT / "table5_multiple_testing_summary.csv", index=False)
# compact p-value / t dumps for figures
a3[["asset", "ladder", "wf_n", "wf_netR", "wf_grossR", "wf_t", "wf_p", "DSR", "q_BH", "criteria_met"]].to_parquet(OUT / "phase3_configs_compact.parquet")
a2[["asset", "tf", "kind", "wf_n", "wf_netR", "wf_grossR", "wf_t", "wf_p", "DSR", "q_BH", "criteria_met"]].to_parquet(OUT / "phase2_configs_compact.parquet")

pd.DataFrame(rows).to_csv(OUT / "reproduction_check.csv", index=False)
print("WROTE", OUT / "reproduction_check.csv", len(rows), "rows")
