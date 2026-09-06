"""Validation for the schema-v2 benchmark result JSON.

Schema (all languages, all algorithms):
{
  "schema_version": 2,
  "algo": "bfs", "lang": "go", "impl": "par", "model": "gpt-5",
  "elapsed_ms": [...], "mean": 12.24, "sd": 0.11, "median": 12.2, "iqr": 0.15,
  "reps": 5, "iters_per_rep": 20,
  "params": {...}, "timestamp": "2026-07-12T10:00:00Z"
}
"""

import json
import statistics
from pathlib import Path

REQUIRED_FIELDS = {
    "algo": str,
    "lang": str,
    "impl": str,
    "elapsed_ms": list,
    "mean": (int, float),
    "sd": (int, float),
    "median": (int, float),
    "iqr": (int, float),
    "reps": int,
    "iters_per_rep": int,
}

V2_FIELDS = {
    "schema_version": int,
    "model": str,
    "params": dict,
    "timestamp": str,
}

KNOWN_LANGS = {"python", "go", "cpp", "java", "csharp", "rust"}
KNOWN_IMPLS = {"seq", "par"}


class SchemaError(Exception):
    pass


def iqr(elapsed) -> float:
    """Canonical interquartile range for this project.

    Every language harness reimplements this; the definition lives here so
    there is exactly one answer to compare them against. Uses Python's
    exclusive, interpolated quantiles -- the five non-Python harnesses used to
    use truncated nearest-rank indexing and disagreed on identical samples.
    """
    qs = statistics.quantiles(sorted(elapsed), n=4)
    return qs[2] - qs[0]


def validate(data: dict, expect: dict = None) -> None:
    """Raise SchemaError if `data` is not a valid v2 result.

    `expect` may pin specific field values (e.g. {"algo": "bfs", "reps": 5}).
    """
    for field, typ in {**REQUIRED_FIELDS, **V2_FIELDS}.items():
        if field not in data:
            raise SchemaError(f"missing field: {field}")
        if not isinstance(data[field], typ):
            raise SchemaError(f"field {field} has type {type(data[field]).__name__}")

    if data["lang"] not in KNOWN_LANGS:
        raise SchemaError(f"unknown lang: {data['lang']}")
    if data["impl"] not in KNOWN_IMPLS:
        raise SchemaError(f"unknown impl: {data['impl']}")

    elapsed = data["elapsed_ms"]
    if len(elapsed) != data["reps"]:
        raise SchemaError(f"len(elapsed_ms)={len(elapsed)} != reps={data['reps']}")
    if not all(isinstance(v, (int, float)) and v >= 0 for v in elapsed):
        raise SchemaError("elapsed_ms must be non-negative numbers")

    # Cross-check stored stats against the raw samples. iqr is included so a
    # harness using a different quantile definition is caught at the run that
    # produced it, rather than silently contradicting summary.csv later.
    if len(elapsed) > 1:
        for name, recomputed in (
            ("mean", statistics.mean(elapsed)),
            ("median", statistics.median(elapsed)),
            ("iqr", iqr(elapsed)),
        ):
            if abs(recomputed - data[name]) > max(1e-6, 1e-3 * abs(recomputed)):
                raise SchemaError(
                    f"stored {name} {data[name]} != recomputed {recomputed}")

    if expect:
        for k, v in expect.items():
            if data.get(k) != v:
                raise SchemaError(f"expected {k}={v!r}, got {data.get(k)!r}")


def load_and_validate(path: Path, expect: dict = None) -> dict:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise SchemaError(f"cannot read result JSON {path}: {e}")
    validate(data, expect)
    return data
