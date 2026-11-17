PY=/c/Users/seans/AppData/Local/Programs/Python/Python313/python.exe
R=D:/Research-Publishing/02-malaysian-snr/rework-v3
for a in ETHUSDT SOLUSDT PAXGUSDT BNBUSDT XRPUSDT ADAUSDT DOGEUSDT LTCUSDT LINKUSDT TRXUSDT DOTUSDT AVAXUSDT BCHUSDT; do
  while [ ! -f $R/data/parquet/${a}_5m.parquet ]; do sleep 30; done
  [ -f $R/results/cells/${a}_5m_trades.parquet ] || $PY -I $R/code/rewalk5m.py $a > $R/logs/rw5_$a.log 2>&1
done
echo 5MDONE > $R/logs/rw5.done
