PY=/c/Users/seans/AppData/Local/Programs/Python/Python313/python.exe
R=D:/Research-Publishing/02-malaysian-snr/rework-v3
for a in BTCUSDT ETHUSDT SOLUSDT; do
 $PY -I $R/code/run_asset.py $a --legacy-file D:/Malaysian-SNR/data/${a}_1h.parquet --tag legacy --reps 100 --no-regime
done
