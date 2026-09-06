import gc
import json
import os
import statistics
import timeit
from datetime import datetime, timezone
from typing import Callable, Optional


def _iqr(data: list) -> float:
    qs = statistics.quantiles(data, n=4)  # [Q1, Q2, Q3] — requires Python 3.8+
    return qs[2] - qs[0]


def get_bench_config(default_reps: int = 5, default_iters: int = 20) -> dict:
    """Read the standard benchmark env vars, falling back to the given defaults.

    Returns {"reps", "iters", "impl", "model"} — the values actually used must
    be recorded in the result JSON so every run is self-describing.
    """
    return {
        "reps": int(os.environ.get("BENCH_REPS", default_reps)),
        "iters": int(os.environ.get("BENCH_ITERS", default_iters)),
        "impl": os.environ.get("IMPL", "seq").lower(),
        "model": os.environ.get("MODEL", "baseline"),
    }


def run_benchmark(
    fn: Callable,
    reps: int = 5,
    iters: int = 20,
    warmup: int = 1,
    disable_gc: bool = False,
) -> dict:
    """
    Time fn using timeit.repeat and return summary statistics.

    Returns a dict with:
        median      – median per-call time in milliseconds
        mean        – arithmetic mean per-call time in milliseconds
        sd          – sample standard deviation in milliseconds
        iqr         – interquartile range (Q3 - Q1) in milliseconds
        elapsed_ms  – raw per-repeat times in milliseconds (length == reps)
        iterations  – reps
    """
    for _ in range(warmup):
        fn()

    gc_was_enabled = gc.isenabled()
    if disable_gc:
        gc.disable()
    try:
        raw = timeit.repeat(fn, repeat=reps, number=iters)
    finally:
        if disable_gc and gc_was_enabled:
            gc.enable()

    per_run_ms = [(t / iters) * 1000 for t in raw]
    return {
        "median": statistics.median(per_run_ms),
        "mean": statistics.mean(per_run_ms),
        "sd": statistics.stdev(per_run_ms) if len(per_run_ms) > 1 else 0,
        "iqr": _iqr(per_run_ms) if len(per_run_ms) > 1 else 0,
        "elapsed_ms": per_run_ms,
        "iterations": reps,
    }


def format_result(label: str, result: dict) -> str:
    return (
        f"{label} | mean {result['mean']:.2f} ms/run ± {result['sd']:.2f} SD"
        f" | median {result['median']:.2f} ms/run ± {result['iqr']:.2f} IQR"
        f" (n={result['iterations']})"
    )


def write_result(
    result: dict,
    algo: str,
    lang: str,
    impl: str,
    iters_per_rep: int,
    model: Optional[str] = None,
    params: Optional[dict] = None,
) -> None:
    """Write schema-v2 result JSON to BENCH_OUT env var path, if set."""
    out_path = os.environ.get("BENCH_OUT")
    if not out_path:
        return
    payload = {
        "schema_version": 2,
        "algo": algo,
        "lang": lang,
        "impl": impl,
        "model": model if model is not None else os.environ.get("MODEL", "baseline"),
        "elapsed_ms": result["elapsed_ms"],
        "mean": result["mean"],
        "sd": result["sd"],
        "median": result["median"],
        "iqr": result["iqr"],
        "reps": result["iterations"],
        "iters_per_rep": iters_per_rep,
        "params": params or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
