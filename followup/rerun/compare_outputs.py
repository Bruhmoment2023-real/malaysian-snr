"""Compare the re-run outputs (followup/rerun/results) with the pack's stored outputs (results/). Read-only on both
except for writing compare_outputs.csv next to this file."""
import hashlib, sys
from pathlib import Path
import numpy as np, pandas as pd

A = Path(r"D:/Research-Publishing/02-malaysian-snr/results")
B = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/rerun/results")
HERE = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/rerun")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frame_diff(a, b):
    if list(a.columns) != list(b.columns):
        return f"columns differ: {sorted(set(a.columns) ^ set(b.columns))}", None
    if a.shape != b.shape:
        return f"shape differs: {a.shape} vs {b.shape}", None
    num = a.select_dtypes("number").columns
    oth = [c for c in a.columns if c not in num]
    mx = 0.0
    for c in num:
        x, y = a[c].to_numpy(float), b[c].to_numpy(float)
        if (np.isnan(x) != np.isnan(y)).any():
            return f"NaN pattern differs in {c}", None
        d = np.nanmax(np.abs(x - y)) if np.isfinite(x).any() else 0.0
        mx = max(mx, float(d))
    nonnum = sum(int((a[c].astype(str).to_numpy() != b[c].astype(str).to_numpy()).sum()) for c in oth)
    return f"numeric max abs diff {mx:.3g}; non-numeric cells differing {nonnum}", (mx, nonnum)


rows = []
names = sorted({p.name for p in A.iterdir()} | {p.name for p in B.iterdir()})
for n in names:
    pa, pb = A / n, B / n
    r = dict(file=n, in_original=pa.exists(), in_rerun=pb.exists(), size_original=pa.stat().st_size if pa.exists() else None,
             size_rerun=pb.stat().st_size if pb.exists() else None, byte_identical=None, detail="")
    if pa.exists() and pb.exists():
        r["sha256_original"], r["sha256_rerun"] = sha(pa), sha(pb)
        r["byte_identical"] = r["sha256_original"] == r["sha256_rerun"]
        if not r["byte_identical"]:
            if n.endswith(".csv"):
                r["detail"], _ = frame_diff(pd.read_csv(pa), pd.read_csv(pb))
            elif n.endswith(".parquet"):
                r["detail"], _ = frame_diff(pd.read_parquet(pa).reset_index(), pd.read_parquet(pb).reset_index())
            elif n.endswith(".png"):
                from PIL import Image
                x, y = np.asarray(Image.open(pa).convert("RGBA")), np.asarray(Image.open(pb).convert("RGBA"))
                r["detail"] = (f"pixels: shape {x.shape} vs {y.shape}; " + (f"differing pixels {int((x != y).any(axis=-1).sum())} of {x.shape[0] * x.shape[1]}" if x.shape == y.shape else "size differs"))
            else:
                r["detail"] = "text differs"
    elif pa.exists():
        r["detail"] = "not produced by the six scripts as files (original was captured console output)" if n.endswith("_log.txt") else "MISSING in re-run"
    rows.append(r)
R = pd.DataFrame(rows)
R.to_csv(HERE / "compare_outputs.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 90)
print(R[["file", "in_original", "in_rerun", "byte_identical", "detail"]].to_string(index=False))
print("byte-identical:", int((R.byte_identical == True).sum()), "of", int((R.in_original & R.in_rerun).sum()), "files present in both")

# console logs: compare stored logs with the re-run stdout, line by line
for stored, new in (("reproduce_log.txt", "01_reproduce_headlines.stdout.log"), ("robustness_R1_log.txt", "02_intrabar_resolution_check.stdout.log")):
    a = [l.rstrip() for l in (A / stored).read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    b = [l.rstrip() for l in (HERE / "logs" / new).read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    sa, sb = set(a), set(b)
    print(f"\n{stored} vs {new}: {len(a)} vs {len(b)} non-empty lines; lines only in stored {len(sa - sb)}; only in re-run {len(sb - sa)}")
    for l in sorted(sa - sb)[:12]: print("  stored only:", l[:230])
    for l in sorted(sb - sa)[:12]: print("  re-run only:", l[:230])
