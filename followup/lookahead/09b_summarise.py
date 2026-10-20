"""Summarise limit_leak/*.csv (output of 09_limit_entry_leak.py) against the reported phase-3 numbers.
Writes limit_leak_summary.md-style text to stdout and CSVs next to it. Uses only the stored results parquet and the 09 outputs."""
import sys, glob
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200); pd.set_option("display.max_colwidth", 95)
R = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(HERE / "limit_leak" / "*.csv")))], ignore_index=True)
cells = R.groupby(["asset", "ladder"]).size().reset_index(name="configs")
print("cells with results:", len(cells)); print(cells.to_string(index=False))
print("validation: configs reproduced exactly from the stored parquet:", int(R.validated.sum()), "of", len(R))
real = R[R.asset != "MCXGOLD_SYN"]

def block(df, tag):
    print(f"\n### {tag}: {len(df)} configs, {df.groupby(['asset','ladder']).ngroups} cells")
    L = df[df.conf == "limit"]
    if len(L):
        big = L[(L.n0 >= 100) & (L.nL >= 100)]
        print(f"LIMIT-ENTRY LAG: configs {len(L)}; with >=100 WF trades in both versions {len(big)}")
        d = big.netL - big.net0
        print(f"  mean WF net R (>=100 trades): shipped {big.net0.mean():+.4f}  lagged {big.netL.mean():+.4f}  mean change {d.mean():+.4f}  median {d.median():+.4f}  share lower {np.mean(d < 0):.2f}")
        print(f"  mean WF gross R             : shipped {big.gross0.mean():+.4f}  lagged {big.grossL.mean():+.4f}")
        print(f"  trade count change (mean n): {big.n0.mean():.0f} -> {big.nL.mean():.0f}")
        print(f"  best shipped WF net R among them: {big.net0.max():+.4f}   best lagged: {big.netL.max():+.4f};  # with net>0: shipped {int((big.net0 > 0).sum())}, lagged {int((big.netL > 0).sum())}")
        print(f"  smallest p (net>0): shipped {big.p0.min():.4g}  lagged {big.pL.min():.4g}")
    S = df[df.story == "simple"]
    if len(S):
        big = S[(S.n0 >= 100) & (S.nC >= 100)]
        d = big.netC - big.net0
        print(f"CAUSAL STORYLINE (story=simple, all confirmations): configs {len(S)}; >=100 trades both {len(big)}")
        print(f"  mean WF net R: shipped {big.net0.mean():+.4f}  causal {big.netC.mean():+.4f}  mean change {d.mean():+.4f}  median {d.median():+.4f}  share higher {np.mean(d > 0):.2f}")
        print(f"  best WF net R: shipped {big.net0.max():+.4f}  causal {big.netC.max():+.4f};  # net>0: shipped {int((big.net0 > 0).sum())}, causal {int((big.netC > 0).sum())};  smallest p {big.p0.min():.4g} -> {big.pC.min():.4g}")
        LS = big[big.conf == "limit"]
        if len(LS) and "nLC" in LS:
            print(f"  limit AND simple ({len(LS)} configs): net shipped {LS.net0.mean():+.4f}  lag-only {LS.netL.mean():+.4f}  causal-only {LS.netC.mean():+.4f}  both {LS.netLC.mean():+.4f}")

block(real, "15 real-data cells")
block(R, "all 18 cells incl. synthetic MCX proxy")
for a in sorted(real.asset.unique()):
    for l in sorted(real.ladder.unique()):
        x = real[(real.asset == a) & (real.ladder == l)]
        if len(x):
            L = x[(x.conf == "limit") & (x.n0 >= 100) & (x.nL >= 100)]
            S = x[(x.story == "simple") & (x.n0 >= 100) & (x.nC >= 100)]
            print(f"{a:8s} {l:13s} limit: best shipped {L.net0.max():+.3f} -> lagged-version-of-that-config {L.loc[L.net0.idxmax(), 'netL']:+.3f}; mean change {np.mean(L.netL - L.net0):+.3f} | simple: mean change {np.mean(S.netC - S.net0):+.4f}" if len(L) and len(S) else f"{a} {l}: insufficient")

# --- the specific objects named in the audit
print("\n### F9 target: XAUUSD weekly ladder, limit + story=simple, >=100 WF trades (shipped -> lagged -> causal story -> both)")
x = R[(R.asset == "XAUUSD") & (R.ladder == "W-D-4H-1H") & (R.conf == "limit") & (R.story == "simple") & (R.n0 >= 100)].sort_values("net0", ascending=False)
print(x[["name", "n0", "net0", "nL", "netL", "nC", "netC", "nLC", "netLC", "p0", "pL"]].head(8).to_string(index=False))
print("--- the audit F9 group: same cell, >=400 WF trades (shipped -> lagged -> causal -> both)")
y = x[x.n0 >= 400].sort_values("net0", ascending=False)
print(y[["name", "n0", "net0", "nL", "netL", "nC", "netC", "nLC", "netLC", "p0", "pL"]].head(12).to_string(index=False))
x.to_csv(HERE / "limit_leak_xau_weekly_limit_simple.csv", index=False)

# --- ablation row of table 6
ab = "depth=3|gaps=0|story=td|conf=limit|stop=lvl|tgt=3R|rb=1|liq=0|miss=0|sess=0|xf="
a = R[R.name == ab]
print("\n### Table 6 ablation row (canonical but limit entry):", len(a), "cells")
print(a[["asset", "ladder", "n0", "net0", "nL", "netL", "stored_n", "stored_net"]].to_string(index=False))
print("trade-weighted WF net R: shipped %+.4f  lagged %+.4f ; mean over cells: shipped %+.4f lagged %+.4f; cells with positive WF: shipped %d lagged %d" % (
    (a.n0 * a.net0).sum() / a.n0.sum(), (a.nL * a.netL).sum() / a.nL.sum(), a.net0.mean(), a.netL.mean(), int((a.net0 > 0).sum()), int((a.netL > 0).sum())))

# --- Table 5 style counts, whole family: replace affected rows, recompute
P = pd.read_parquet(r"D:/Research-Publishing/02-malaysian-snr/results/phase3_configs_compact.parquet")
P["idx"] = P.groupby(["asset", "ladder"]).cumcount()
for tag, col_n, col_net, col_p, only in (("lagged limit entries", "nL", "netL", "pL", "limit"), ("causal storyline (simple)", "nC", "netC", "pC", "simple"), ("both", None, None, None, "both")):
    Q = P.copy()
    m = R.set_index(["asset", "ladder", "idx"])
    key = pd.MultiIndex.from_frame(Q[["asset", "ladder", "idx"]])
    new_n = Q.wf_n.to_numpy().copy(); new_net = Q.wf_netR.to_numpy().copy(); new_p = Q.wf_p.to_numpy().copy()
    for pos, k in enumerate(key):
        if k not in m.index:
            continue
        r = m.loc[k]
        if only == "limit" and r.conf == "limit":
            new_n[pos], new_net[pos], new_p[pos] = r.nL, r.netL, r.pL
        elif only == "simple" and r.story == "simple":
            new_n[pos], new_net[pos], new_p[pos] = r.nC, r.netC, r.pC
        elif only == "both":
            if r.conf == "limit" and r.story == "simple":
                new_n[pos], new_net[pos], new_p[pos] = r.nLC, r.netLC, r.pLC
            elif r.conf == "limit":
                new_n[pos], new_net[pos], new_p[pos] = r.nL, r.netL, r.pL
            elif r.story == "simple":
                new_n[pos], new_net[pos], new_p[pos] = r.nC, r.netC, r.pC
    Q["n_new"], Q["net_new"], Q["p_new"] = new_n, new_net, new_p
    ok = ~Q.asset.eq("MCXGOLD_SYN") if len(cells) < 18 else np.ones(len(Q), bool)
    def bh(p):
        p = np.where(np.isnan(p), 1.0, p); o = np.argsort(p); n = len(p); q = np.empty(n); ranked = p[o] * n / (np.arange(n) + 1)
        q[o] = np.minimum.accumulate(ranked[::-1])[::-1]; return np.minimum(q, 1.0)
    q_old, q_new = bh(Q.wf_p.to_numpy()), bh(Q.p_new.to_numpy())
    big_o, big_n = Q.wf_n >= 100, Q.n_new >= 100
    print(f"\n### Table-5 style counts, phase 3 family ({len(Q)} configs; {len(cells)} cells have been re-run) - {tag}")
    print("  p<0.05:            shipped", int((Q.wf_p < 0.05).sum()), "  after", int((Q.p_new < 0.05).sum()))
    print("  BH q<0.10 (all):   shipped", int((q_old < 0.10).sum()), "  after", int((q_new < 0.10).sum()))
    print("  BH q<0.10 (>=100 trades): shipped", int(((q_old < 0.10) & big_o).sum()), "  after", int(((q_new < 0.10) & big_n).sum()))
    print("  max WF net R (>=100 trades): shipped %+.4f  after %+.4f ;  # configs net>0 (>=100 trades): shipped %d after %d" % (Q.loc[big_o, "wf_netR"].max(), Q.loc[big_n, "net_new"].max(), int((Q.loc[big_o, "wf_netR"] > 0).sum()), int((Q.loc[big_n, "net_new"] > 0).sum())))
    print("  smallest p (>=100 trades): shipped %.4g after %.4g" % (Q.loc[big_o, "wf_p"].min(), Q.loc[big_n, "p_new"].min()))
