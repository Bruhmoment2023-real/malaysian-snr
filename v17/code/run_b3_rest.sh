PY=/c/Users/seans/AppData/Local/Programs/Python/Python313/python.exe
R=D:/Research-Publishing/02-malaysian-snr/rework-v3
w(){ for a in "$@"; do [ -f $R/results/cells/${a}_b3.csv ] || $PY -I $R/code/run_b3.py $a > $R/logs/b3_$a.log 2>&1; done; }
w DOGEUSDT LTCUSDT LINKUSDT XAGUSD &
w TRXUSDT DOTUSDT BTCUSDT XAUUSD &
w AVAXUSDT BCHUSDT &
wait
