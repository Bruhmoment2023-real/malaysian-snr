PY=/c/Users/seans/AppData/Local/Programs/Python/Python313/python.exe
R=D:/Research-Publishing/02-malaysian-snr/rework-v3
for a in XAUUSD XAGUSD; do $PY -I $R/code/run_asset.py $a > $R/logs/run_$a.log 2>&1; done
