PY=/c/Users/seans/AppData/Local/Programs/Python/Python313/python.exe
R=D:/Research-Publishing/02-malaysian-snr/rework-v3
$PY -I $R/code/trunc_test.py BTCUSDT XRPUSDT XAUUSD > $R/logs/trunc.log 2>&1
for a in "$@"; do [ -f $R/results/cells/${a}_b3.csv ] || $PY -I $R/code/run_b3.py $a > $R/logs/b3_$a.log 2>&1; done
