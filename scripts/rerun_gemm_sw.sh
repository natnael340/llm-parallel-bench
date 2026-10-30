#!/usr/bin/env bash
# Re-runs GEMM and Smith-Waterman at the methodology setting (5 reps x 20 iters, 1 warmup).
# Usage: scripts/rerun_gemm_sw.sh compiled|python-gemm|python-sw|aggregate
# A finished combo is skipped on restart, so after an interruption just run the same phase again.
set -uo pipefail
cd "$(dirname "$0")/.."
source ~/.cargo/env
PY=.venv/bin/python
phase=${1:?usage: $0 compiled|python-gemm|python-sw|aggregate}
mkdir -p results/logs
log=results/logs/rerun_${phase}_$(date +%Y%m%d_%H%M).log

{
  echo "== $phase  $(date)  commit $(git rev-parse --short HEAD)"
  uptime
  ps -eo pcpu,comm --sort=-pcpu | head -6
  case $phase in
    # ~5 h. Longest combos: SW Rust GPT-5 ~1.7 h, SW Java GPT-5 ~1 h.
    compiled)    $PY bench/run.py matrix --algo gemm,smith-waterman --skip-lang python --timeout 10800 ;;
    # ~4.5 h. Claude is left out: it has no result and the thesis reports it as not finishing in 1 h.
    python-gemm) $PY bench/run.py matrix --algo gemm --lang python --model baseline,gpt-5,gemini-2-5-pro --timeout 43200 ;;
    # ~23 h. Claude alone is ~13.3 h, above the manifest's 12 h limit, hence 18 h.
    python-sw)   $PY bench/run.py matrix --algo smith-waterman --lang python --timeout 64800 ;;
    aggregate)   $PY bench/aggregate.py --verify && $PY bench/aggregate.py ;;
    *) echo "unknown phase: $phase"; exit 2 ;;
  esac
  echo "== exit $?  $(date)"
} 2>&1 | tee "$log"
