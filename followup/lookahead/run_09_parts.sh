#!/bin/bash
cd /d/Research-Publishing/02-malaysian-snr/followup/lookahead
export NUMBA_CACHE_DIR=$(pwd)/.numba_cache PYTHONDONTWRITEBYTECODE=1
for A in BTCUSDT ETHUSDT SOLUSDT; do for P in limit simple; do
  [ -f limit_leak/${A}_4H-1H-15m-5m.$P.csv ] && continue
  s=$(date +%s)
  timeout 590 /d/Malaysian-SNR/.venv/Scripts/python.exe -B 09_limit_entry_leak.py $A 4H-1H-15m-5m $P > logs/09_${A}_4H-1H-15m-5m.$P.stdout.log 2> logs/09_${A}_4H-1H-15m-5m.$P.stderr.log
  echo "$A 5m part=$P exit=$? wall=$(( $(date +%s)-s ))s" >> logs/09_all.log
done; done; echo PARTSDONE >> logs/09_all.log
