"""Phase A: every configuration on PRE-HOLDOUT data only (the last 365 days are never loaded).
Walk-forward: pre-holdout bars split into 5 equal folds; fold 1 is IS-only. Fixed configs are
judged on folds 2-5 (WF-OOS). Selection processes (pick best config on folds < k, trade fold k)
give the honest 'data-mined' estimate. Outputs go to D:\\Malaysian-SNR\\phase2\\results\\A\\.
Usage: python p2_phaseA.py [workers]
"""
import sys, json, time, itertools, math, os
from pathlib import Path
from statistics import NormalDist
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead/code_copy")
import p2common as P

OUT = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead/scratch/p2A"); OUT.mkdir(parents=True, exist_ok=True)
ND = NormalDist()
LIM_EXITS = [(0, 1.0, 0.0), (0, 2.0, 0.0), (0, 3.0, 0.0), (1, 1.0, 0.0), (2, 2.0, 1.0), (3, 2.0, 0.0)]
ALONE_EXITS = [(0, 2.0, 0.0), (0, 1.0, 0.0), (2, 2.0, 1.0)]
MIN_SEL = 30


def stationary_boot_idx(T, B, mean_block, rng):
    idx = np.empty((B, T), np.int64)
    p = 1.0 / mean_block
    for b in range(B):
        i = rng.integers(T)
        for t in range(T):
            if t > 0 and rng.random() < p:
                i = rng.integers(T)
            elif t > 0:
                i = (i + 1) % T
            idx[b, t] = i
    return idx


def rc_spa(X, B=300, mean_block=10, seed=7):
    """White Reality Check and Hansen SPA (consistent) vs benchmark 0 on daily net-R series X (K x T)."""
    K, T = X.shape
    if K == 0 or T < 30:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    mu = X.mean(axis=1)
    idx = stationary_boot_idx(T, B, mean_block, rng)
    boot = np.empty((B, K), np.float32)
    for b in range(B):
        boot[b] = X[:, idx[b]].mean(axis=1)
    rt = math.sqrt(T)
    V_rc = rt * mu.max()
    p_rc = np.mean((rt * (boot - mu)).max(axis=1) >= V_rc)
    om = (rt * boot).std(axis=0); om[om <= 0] = np.inf
    V_spa = max((rt * mu / om).max(), 0.0)
    thr = -np.sqrt(om ** 2 / T * 2 * math.log(math.log(T)))
    gc = np.where(mu >= thr, mu, 0.0)
    Vb = np.maximum((rt * (boot - gc) / om).max(axis=1), 0.0)
    p_spa = np.mean(Vb >= V_spa)
    return float(p_rc), float(p_spa)


def dsr(sr, n, skew, kurt, N, V):
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014), per-trade Sharpe, N trials, V = var of SR over trials."""
    if n < 10 or not np.isfinite(sr) or N < 2 or not np.isfinite(V) or V <= 0:
        return np.nan
    g = 0.5772156649
    sr0 = math.sqrt(V) * ((1 - g) * ND.inv_cdf(1 - 1 / N) + g * ND.inv_cdf(1 - 1 / (N * math.e)))
    den = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if den <= 0:
        return np.nan
    return ND.cdf((sr - sr0) * math.sqrt(n - 1) / math.sqrt(den))


def run_cell(asset, tf):
    t0 = time.time()
    cell = P.Cell(asset, tf, "A")
    e = cell.edges; wf_lo = e[1]
    d0 = cell.end_days[wf_lo]; D = int(cell.end_days[-1] - d0 + 1)
    recs, daily, cfgs, seen = [], [], [], set()
    tr_cache = {}

    def ev(cfg, tag):
        name = P.cfg_name(cfg)
        if name in seen:
            return None
        seen.add(name)
        tr = cell.trades(cfg)
        net = tr[:, 7] - tr[:, 8] if len(tr) else np.zeros(0)
        fold = np.clip(np.searchsorted(e, tr[:, 0], side="right") - 1, 0, P.NFOLDS - 1) if len(tr) else np.zeros(0, int)
        rec = dict(asset=asset, tf=tf, name=name, tag=tag, kind=cfg["kind"], base=cfg.get("base", ""),
                   nfilt=len(cfg.get("filters", [])), filters="+".join(cfg.get("filters", [])), exit=P.xname(cfg["exit"]))
        for k in range(P.NFOLDS):
            mk = fold == k
            rec[f"n{k}"] = int(mk.sum()); rec[f"s{k}"] = float(net[mk].sum()); rec[f"g{k}"] = float(tr[mk, 7].sum()) if len(tr) else 0.0
        wf = fold >= 1
        x = net[wf]
        rec["wf_n"] = int(len(x)); rec["wf_netR"] = float(x.mean()) if len(x) else np.nan
        rec["wf_grossR"] = float(tr[wf, 7].mean()) if len(x) else np.nan
        rec["wf_win"] = float((x > 0).mean()) if len(x) else np.nan
        w, lo = x[x > 0].sum(), -x[x < 0].sum()
        rec["wf_PF"] = float(w / lo) if lo > 0 else np.nan
        t, p = P.tstat_p(x); rec["wf_t"] = t; rec["wf_p"] = p
        if len(x) > 2 and x.std() > 0:
            rec["sr_trade"] = float(x.mean() / x.std(ddof=1))
            rec["skew"] = float(pd.Series(x).skew()); rec["kurt"] = float(pd.Series(x).kurt() + 3)
        else:
            rec["sr_trade"] = np.nan; rec["skew"] = 0.0; rec["kurt"] = 3.0
        dv = np.zeros(D, np.float32)
        if wf.any():
            di = cell.end_days[tr[wf, 2].astype(int)] - d0
            np.add.at(dv, di, x.astype(np.float32))
        recs.append(rec); daily.append(dv); cfgs.append(cfg)
        return rec

    fnames = sorted(cell.F) + sorted(cell.levelF["V1"])
    D_ = P.DEFAULT_EXIT
    # 1 bases (+ wider buffer)
    for b in ("V0", "V1"):
        ev(dict(kind="mkt", base=b, filters=[], exit=D_), "base")
        ev(dict(kind="mkt", base=b, filters=[], exit=D_, buf=0.3), "base_buf")
    # 2 single filters
    singles = {}
    for b in ("V0", "V1"):
        for f in fnames:
            r = ev(dict(kind="mkt", base=b, filters=[f], exit=D_), "single")
            if r:
                singles[(b, f)] = r
    # rank singles on FOLD 1 ONLY (never OOS)
    def f1(r):
        return r["s0"] / r["n0"] if r["n0"] >= 20 else -np.inf
    rank = {b: sorted([f for f in fnames], key=lambda f: -f1(singles[(b, f)])) for b in ("V0", "V1")}
    # 3 all pairs, triples of fold-1 top 8
    for b in ("V0", "V1"):
        for f, g in itertools.combinations(fnames, 2):
            ev(dict(kind="mkt", base=b, filters=[f, g], exit=D_), "pair")
        for tri in itertools.combinations(rank[b][:8], 3):
            ev(dict(kind="mkt", base=b, filters=list(tri), exit=D_), "triple")
    # 4 exits on bases and fold-1 top-3 singles
    for b in ("V0", "V1"):
        for fl in [[]] + [[f] for f in rank[b][:3]]:
            for x in P.EXITS:
                ev(dict(kind="mkt", base=b, filters=fl, exit=x), "exit")
    # 5 limit / maker entries (missed-fill model eps), and + fold-1 top-3 STATE filters
    for b in ("V0", "V1"):
        for eps in (0.0, 0.05):
            for sl in (0.25, 0.5, 1.0):
                for x in LIM_EXITS:
                    ev(dict(kind="lim", base=b, filters=[], exit=x, eps=eps, sl_atr=sl), "limit")
        st = [f for f in rank[b] if f in P.STATE_FILTERS and f in cell.F][:3]
        for f in st:
            ev(dict(kind="lim", base=b, filters=[f], exit=D_, eps=0.05, sl_atr=0.5), "limit_filter")
    # 6 confluence ALONE (event triggers)
    for s in sorted(cell.S):
        for x in ALONE_EXITS:
            ev(dict(kind="alone", trigger=s, exit=x), "alone")

    R = pd.DataFrame(recs)
    R["n_configs_cell"] = len(R)
    X = np.vstack(daily) if daily else np.zeros((0, D), np.float32)

    # ---------------- multiple-testing inside the cell
    p_rc, p_spa = rc_spa(X[R.wf_n.to_numpy() > 0])
    R["cell_p_RC"] = p_rc; R["cell_p_SPA"] = p_spa
    V = np.nanvar(R.loc[R.wf_n >= 30, "sr_trade"].to_numpy()) if (R.wf_n >= 30).sum() > 2 else np.nan
    R["DSR"] = [dsr(sr, n, sk, ku, len(R), V) for sr, n, sk, ku in zip(R["sr_trade"], R["wf_n"], R["skew"], R["kurt"])]

    # ---------------- walk-forward SELECTION processes
    nk = R[[f"n{k}" for k in range(P.NFOLDS)]].to_numpy(); sk = R[[f"s{k}" for k in range(P.NFOLDS)]].to_numpy()
    gk = R[[f"g{k}" for k in range(P.NFOLDS)]].to_numpy()
    groups = {"all": np.ones(len(R), bool),
              "msnr_solo": (R.kind.isin(["mkt", "lim"]) & (R.nfilt == 0)).to_numpy(),
              "msnr_combo": (R.kind.isin(["mkt", "lim"]) & (R.nfilt > 0)).to_numpy(),
              "alone": (R.kind == "alone").to_numpy(),
              "msnr_base_fixed": (R.tag == "base").to_numpy() & (R.base == "V1").to_numpy()}
    sel = {}
    for gname, gm in groups.items():
        chosen, tot_n, tot_s, tot_g, trs, rnd = [], 0, 0.0, 0.0, [], []
        for k in range(1, P.NFOLDS):
            isn = nk[:, :k].sum(1); iss = sk[:, :k].sum(1)
            score = np.where(gm & (isn >= MIN_SEL), iss / np.maximum(isn, 1), -np.inf)
            if gname == "msnr_base_fixed":
                score = np.where(gm, 0.0, -np.inf)
            if not np.isfinite(score.max()):
                chosen.append(None); continue
            i = int(np.argmax(score)); chosen.append(R.name.iloc[i])
            tot_n += nk[i, k]; tot_s += sk[i, k]; tot_g += gk[i, k]
            tr = cell.trades(cfgs[i], e[k], e[k + 1])
            if len(tr):
                trs.append(tr)
                if len(tr) >= 5:
                    rn, rg = cell.random(cfgs[i], tr, e[k], e[k + 1], reps=200, seed=100 + k)
                    rnd.append((len(tr), rn))
        allt = np.vstack(trs) if trs else np.zeros((0, 12))
        cagr, mdd, sh = P.equity_stats(allt, cell) if len(allt) else (np.nan,) * 3
        if rnd:
            w = np.array([a for a, _ in rnd], float)
            Lm = min(len(r) for _, r in rnd)
            M = np.vstack([r[:Lm] for _, r in rnd])
            comb = (M * w[:, None]).sum(0) / w.sum()
            actual = tot_s / max(tot_n, 1)
            p_r = (np.sum(comb >= actual) + 1) / (len(comb) + 1); rmean = float(np.nanmean(comb))
        else:
            p_r, rmean = np.nan, np.nan
        net = allt[:, 7] - allt[:, 8] if len(allt) else np.zeros(0)
        t, p = P.tstat_p(net)
        isn = nk.sum(1); iss = sk.sum(1)
        fscore = np.where(groups[gname] & (isn >= MIN_SEL), iss / np.maximum(isn, 1), -np.inf)
        if gname == "msnr_base_fixed":
            fscore = np.where(groups[gname], 0.0, -np.inf)
        final = R.name.iloc[int(np.argmax(fscore))] if np.isfinite(fscore.max()) else None
        w_, lo_ = net[net > 0].sum(), -net[net < 0].sum()
        sel[gname] = dict(asset=asset, tf=tf, group=gname, chosen_per_fold=chosen, wf_n=int(tot_n),
                          wf_netR=tot_s / max(tot_n, 1) if tot_n else np.nan, wf_grossR=tot_g / max(tot_n, 1) if tot_n else np.nan,
                          wf_PF=float(w_ / lo_) if lo_ > 0 else np.nan, CAGR=cagr, MaxDD=mdd, Sharpe=sh,
                          rand_netR=rmean, p_vs_random=p_r, t=t, p=p, final_pick_for_holdout=final)

    # ---------------- random baselines for candidate fixed configs
    cand = set(R[R.tag == "base"].index)
    elig = R[(R.wf_n >= 30)]
    cand |= set(elig.sort_values("wf_netR", ascending=False).index[:15])
    for kd in ("alone", "lim"):
        cand |= set(elig[elig.kind == kd].sort_values("wf_netR", ascending=False).index[:3])
    for s in sel.values():
        if s["final_pick_for_holdout"] is not None:
            cand |= set(R.index[R.name == s["final_pick_for_holdout"]])
    R["rand_netR"] = np.nan; R["rand_grossR"] = np.nan; R["p_vs_random"] = np.nan; R["p_gross_vs_random"] = np.nan
    R["CAGR"] = np.nan; R["MaxDD"] = np.nan; R["Sharpe"] = np.nan; R["candidate"] = False
    for i in cand:
        cfg = cfgs[i]
        tr = cell.trades(cfg, wf_lo, cell.n)
        R.loc[i, "candidate"] = True
        if len(tr) < 5:
            continue
        rn, rg = cell.random(cfg, tr, wf_lo, cell.n, reps=200, seed=11 + i)
        a = R.loc[i, "wf_netR"]; g = R.loc[i, "wf_grossR"]
        R.loc[i, "rand_netR"] = np.nanmean(rn); R.loc[i, "rand_grossR"] = np.nanmean(rg)
        R.loc[i, "p_vs_random"] = (np.sum(rn >= a) + 1) / (np.sum(~np.isnan(rn)) + 1)
        R.loc[i, "p_gross_vs_random"] = (np.sum(rg >= g) + 1) / (np.sum(~np.isnan(rg)) + 1)
        R.loc[i, ["CAGR", "MaxDD", "Sharpe"]] = P.equity_stats(tr, cell)
    # ---------------- confluence ALONE as a regime: random entries inside the regime, V1 geometry
    base_cfg = cfgs[int(R.index[R.name == P.cfg_name(dict(kind="mkt", base="V1", filters=[], exit=D_))][0])]
    btr = cell.trades(base_cfg, wf_lo, cell.n)
    reg = []
    if len(btr) >= 5:
        cs = cell.cost
        for gname, g in cell.G.items():
            rn, rg = P.E2.random_baseline2(cell.o, cell.h, cell.l, cell.c, cell.a, g.astype(np.int64), 1, wf_lo, cell.n,
                                           len(btr), btr[:, 9].copy(), btr[:, 10].copy(), 0, 2.0, 0.0, cs["m_eabs"], cs["m_epct"],
                                           cs["tabs"], cs["tpct"], cs["sabs"], cs["spct"], cs["carry"], cell.bar_h, 200, 5)
            reg.append(dict(asset=asset, tf=tf, regime=gname, trades_per_rep=len(btr), netR=float(np.nanmean(rn)),
                            grossR=float(np.nanmean(rg)), netR_p95=float(np.nanpercentile(rn, 95))))
    # B&H on WF window
    c = cell.c; bars = cell.bars
    yrs = (bars.end.iloc[-1] - bars.index[wf_lo]).days / 365.25
    bh = dict(asset=asset, tf=tf, wf_start=str(bars.index[wf_lo].date()), wf_end=str(bars.end.iloc[-1].date()),
              hold_start=str(cell.hold_start.date()), BH_CAGR=(c[-1] / cell.o[wf_lo]) ** (1 / yrs) - 1,
              BH_MaxDD=float((pd.Series(c[wf_lo:]) / pd.Series(c[wf_lo:]).cummax() - 1).min()),
              n_configs=len(R), secs=round(time.time() - t0))
    tag = f"{asset.replace('=', '')}_{tf}"
    R.to_csv(OUT / f"configs_{tag}.csv", index=False)
    json.dump(sel, open(OUT / f"wfsel_{tag}.json", "w"), indent=1, default=float)
    json.dump({r: c_ for r, c_ in zip(R.name, cfgs)}, open(OUT / f"cfgs_{tag}.json", "w"), default=float)
    pd.DataFrame(reg).to_csv(OUT / f"regimes_{tag}.csv", index=False)
    json.dump(bh, open(OUT / f"bh_{tag}.json", "w"), default=float)
    return tag, len(R), bh["secs"]


if __name__ == "__main__":
    assert os.path.exists("D:/"), "D: offline - stop"
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    cells = sorted(P.CELLS, key=lambda x: {"15m": 3, "1h": 2, "4h": 1, "1d": 0}[x[1]])
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    if only:
        cells = [c for c in cells if f"{c[0]}_{c[1]}" in only]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_cell, a, t): (a, t) for a, t in cells}
        for f in as_completed(futs):
            try:
                print("done", f.result(), flush=True)
            except Exception as err:
                import traceback; print("FAILED", futs[f], repr(err), traceback.format_exc(), flush=True)
