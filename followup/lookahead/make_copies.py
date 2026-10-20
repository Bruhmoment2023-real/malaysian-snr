"""Copy the phase-1/2/3 engine files from D:/Malaysian-SNR (read-only) into followup/lookahead/code_copy and redirect
(a) every module search path to the copy folder and (b) every OUTPUT folder to followup/lookahead/scratch.
Data paths still point at D:/Malaysian-SNR (read only). Records SHA-256 of each original and the lines changed."""
import hashlib, json
from pathlib import Path

SRC = Path(r"D:/Malaysian-SNR"); HERE = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead")
DST = HERE / "code_copy"; DST.mkdir(parents=True, exist_ok=True); (HERE / "scratch").mkdir(exist_ok=True)
CP = "D:/Research-Publishing/02-malaysian-snr/followup/lookahead/code_copy"
SC = "D:/Research-Publishing/02-malaysian-snr/followup/lookahead/scratch"
FILES = {"backtest/msnr.py": [], "phase2/engine2.py": [], "phase2/indicators.py": [], "phase3/topdown.py": [],
         "phase2/p2common.py": [('sys.path.insert(0, r"D:/Malaysian-SNR/backtest"); sys.path.insert(0, r"D:/Malaysian-SNR/phase2")', f'sys.path.insert(0, r"{CP}")')],
         "phase2/p2_phaseA.py": [('sys.path.insert(0, r"D:/Malaysian-SNR/phase2")', f'sys.path.insert(0, r"{CP}")'),
                                 ('OUT = Path(r"D:/Malaysian-SNR/phase2/results/A")', f'OUT = Path(r"{SC}/p2A")')],
         "phase3/p3common.py": [('sys.path.insert(0, str(ROOT / "backtest")); sys.path.insert(0, str(ROOT / "phase2")); sys.path.insert(0, str(ROOT / "phase3"))', f'sys.path.insert(0, r"{CP}")')],
         "phase3/p3_msnr.py": [('sys.path.insert(0, r"D:/Malaysian-SNR/phase3")', f'sys.path.insert(0, r"{CP}")'),
                               ('RES = C.ROOT / "phase3" / "results"', f'RES = Path(r"{SC}/p3")')]}
log = {}
for rel, reps in FILES.items():
    b = (SRC / rel).read_bytes(); t = b.decode("utf-8")
    for old, new in reps:
        assert t.count(old) == 1, (rel, old, t.count(old))
        t = t.replace(old, new)
    assert "D:/Malaysian-SNR/phase" not in t.replace('ROOT = Path(r"D:/Malaysian-SNR")', "") or rel in ("phase2/p2_phaseA.py",), rel
    (DST / Path(rel).name).write_bytes(t.encode("utf-8"))
    log[rel] = dict(sha256_original=hashlib.sha256(b).hexdigest(), replacements=[dict(old=o, new=n) for o, n in reps])
    print(rel, "->", Path(rel).name, len(reps), "line(s) changed")
(HERE / "code_copy_manifest.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
