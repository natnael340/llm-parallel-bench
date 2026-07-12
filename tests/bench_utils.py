import gc
import json
import os
import statistics
import timeit
from typing import Callable


def _iqr(data: list) -> float:
    qs = statistics.quantiles(data, n=4)  # [Q1, Q2, Q3] — requires Python 3.8+
    return qs[2] - qs[0]


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
        "iqr": _iqr(per_run_ms),
        "elapsed_ms": per_run_ms,
        "iterations": reps,
    }


def format_result(label: str, result: dict) -> str:
    return (
        f"{label} | {result['median']:.2f} ms/run ± {result['iqr']:.2f} IQR"
        f" (n={result['iterations']})"
    )


def write_result(
    result: dict,
    algo: str,
    lang: str,
    impl: str,
    iters_per_rep: int,
) -> None:
    """Write result JSON to BENCH_OUT env var path, if set."""
    out_path = os.environ.get("BENCH_OUT")
    if not out_path:
        return
    payload = {
        "algo": algo,
        "lang": lang,
        "impl": impl,
        "elapsed_ms": result["elapsed_ms"],
        "median": result["median"],
        "iqr": result["iqr"],
        "reps": result["iterations"],
        "iters_per_rep": iters_per_rep,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
