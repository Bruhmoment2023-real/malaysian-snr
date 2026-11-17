PY=/c/Users/seans/AppData/Local/Programs/Python/Python313/python.exe
R=D:/Research-Publishing/02-malaysian-snr/rework-v3
run(){ for a in "$@"; do while [ ! -f $R/data/parquet/${a}_1h.parquet ] && [ ! -f $R/data/parquet/${a}_duka_1h.parquet ]; do sleep 30; done
  [ -f $R/results/cells/${a}_new_trades.parquet ] || $PY -I $R/code/run_asset.py $a > $R/logs/run_$a.log 2>&1; done; }
run BTCUSDT SOLUSDT ADAUSDT LTCUSDT TRXUSDT AVAXUSDT XAUUSD &
run ETHUSDT PAXGUSDT BNBUSDT DOGEUSDT LINKUSDT BCHUSDT XAGUSD &
run XRPUSDT DOTUSDT &
wait
