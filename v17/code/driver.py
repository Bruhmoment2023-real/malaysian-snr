"""Run run_asset.py for every asset whose parquet exists and whose results are missing; 3 workers, BelowNormal. Exits when all done."""
import subprocess, time, sys
from pathlib import Path
sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/rework-v3/code")
import core
PY = r"C:\Users\seans\AppData\Local\Programs\Python\Python313\python.exe"
ASSETS = core.CRYPTO_LEGACY + core.CRYPTO_NEW + core.METALS + core.FX
want = sys.argv[1:] or ASSETS
def ready(a):
    f = core.PQ / (f"{a}_1h.parquet" if core.ASSET_CLASS[a] == "crypto" else f"{a}_duka_1h.parquet")
    return f.exists()
def done(a): return (core.ROOT / "results" / "cells" / f"{a}_new_trades.parquet").exists()
running = {}
while True:
    for a, p in list(running.items()):
        if p.poll() is not None:
            print(a, "exit", p.returncode, flush=True); del running[a]
    todo = [a for a in want if not done(a) and a not in running and ready(a)]
    while todo and len(running) < 3:
        a = todo.pop(0)
        running[a] = subprocess.Popen([PY, "-I", r"D:\Research-Publishing\02-malaysian-snr\rework-v3\code\run_asset.py", a],
                                      stdout=open(rf"D:\Research-Publishing\02-malaysian-snr\rework-v3\logs\run_{a}.log", "w"), stderr=subprocess.STDOUT)
        print("start", a, flush=True)
    if not running and all(done(a) or not ready(a) and False for a in want) :
        break
    if not running and not [a for a in want if not done(a)]:
        break
    time.sleep(30)
print("driver finished")
