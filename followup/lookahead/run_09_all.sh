#!/bin/bash
# one cell at a time, each limited to 580 s wall
cd /d/Research-Publishing/02-malaysian-snr/followup/lookahead
export NUMBA_CACHE_DIR=$(pwd)/.numba_cache PYTHONDONTWRITEBYTECODE=1
for L in W-D-4H-1H D-4H-1H-15m 4H-1H-15m-5m; do
 for A in XAUUSD XAGUSD BTCUSDT ETHUSDT SOLUSDT MCXGOLD_SYN; do
  [ -f limit_leak/${A}_${L}.csv ] && continue
  s=$(date +%s)
  timeout 580 /d/Malaysian-SNR/.venv/Scripts/python.exe -B 09_limit_entry_leak.py $A $L > logs/09_${A}_${L}.stdout.log 2> logs/09_${A}_${L}.stderr.log
  echo "$A $L exit=$? wall=$(( $(date +%s)-s ))s" >> logs/09_all.log
 done
done
echo ALLDONE >> logs/09_all.log
