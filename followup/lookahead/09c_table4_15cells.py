"""Table 4 rows 9-10 of the paper on the 15 real-data cells (and the 18-cell reproduction).
Same logic as followup/lookahead/09b_summarise.py: p<0.05 counted over every phase-3 config in
results/phase3_configs_compact.parquet (no min-trade filter), with affected rows replaced by the 09 re-run outputs.
Read-only on the repo. Usage: python -I followup/lookahead/09c_table4_15cells.py [repo_root]"""
import sys, glob
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2])
SYN = "MCXGOLD_SYN"
R = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(ROOT / "followup/lookahead/limit_leak/*.csv")))], ignore_index=True)
P = pd.read_parquet(ROOT / "results/phase3_configs_compact.parquet")
P["idx"] = P.groupby(["asset", "ladder"]).cumcount()
print("parquet configs:", len(P), "| cells:", P.groupby(["asset", "ladder"]).ngroups)
print(P.groupby("asset").size().to_string())
print("re-run rows:", len(R), "| validated:", int(R.validated.sum()))

M = P.merge(R[["asset", "ladder", "idx", "conf", "story", "nL", "netL", "pL", "nC", "netC", "pC", "nLC", "netLC", "pLC"]],
            on=["asset", "ladder", "idx"], how="left", suffixes=("", "_r"))
assert len(M) == len(P)
lim = M.conf.eq("limit"); sim = M.story.eq("simple")
p_lag = np.where(lim, M.pL, M.wf_p)
p_cau = np.where(sim, M.pC, M.wf_p)
p_both = np.where(lim & sim, M.pLC, np.where(lim, M.pL, np.where(sim, M.pC, M.wf_p)))

def counts(mask, tag):
    print(f"\n## {tag}: configs {int(mask.sum())}, cells {M[mask].groupby(['asset','ladder']).ngroups}")
    print("  p<0.05 shipped:", int((M.wf_p[mask] < 0.05).sum()))
    print("  p<0.05 after limit-entry fix:", int((p_lag[mask] < 0.05).sum()))
    print("  p<0.05 after storyline fix:", int((p_cau[mask] < 0.05).sum()))
    print("  p<0.05 after both fixes:", int((p_both[mask] < 0.05).sum()))
    print("  configs with NaN shipped p:", int(M.wf_p[mask].isna().sum()))
    n_lag = np.where(lim, M.nL, M.wf_n); n_both = np.where(lim & sim, M.nLC, np.where(lim, M.nL, np.where(sim, M.nC, M.wf_n)))
    print("  smallest p (>=100 trades) shipped %.4g | after limit fix %.4g | after both %.4g" % (
        M.wf_p[mask & (M.wf_n >= 100).to_numpy()].min(), p_lag[mask & (n_lag >= 100)].min(), p_both[mask & (n_both >= 100)].min()))

counts(np.ones(len(M), bool), "all 18 cells")
counts(~M.asset.eq(SYN).to_numpy(), "15 real-data cells")

ab = "depth=3|gaps=0|story=td|conf=limit|stop=lvl|tgt=3R|rb=1|liq=0|miss=0|sess=0|xf="
a = R[R.name == ab]
for tag, x in (("18 cells", a), ("15 real cells", a[a.asset != SYN])):
    print(f"\n## canonical-with-limit-entry ({tag}, n={len(x)}): mean over cells shipped {x.net0.mean():+.4f} lagged {x.netL.mean():+.4f}; "
          f"trade-weighted shipped {(x.n0*x.net0).sum()/x.n0.sum():+.4f} lagged {(x.nL*x.netL).sum()/x.nL.sum():+.4f}; "
          f"cells positive shipped {int((x.net0>0).sum())} lagged {int((x.netL>0).sum())}")
# storyline fix does not apply (story=td), so 'both fixes' equals lagged for this row
print("canonical row story values:", a.story.unique(), "conf:", a.conf.unique())
