#!/usr/bin/env python3
"""Aggregate all result JSONs under results/ into a research-ready summary.

Walks results/**/*.json, recomputes mean/sd/median/iqr from the raw
elapsed_ms (warning if the stored values disagree), joins each parallel row
to its baseline sequential row per algo x lang, and emits:
  - results/summary.csv  (one row per algo/lang/model/impl, with speedups)
  - results/summary.md   (paper-ready table grouped by algo)

Usage:
  python bench/aggregate.py            # write summary.csv + summary.md
  python bench/aggregate.py --verify   # only check stored stats vs raw, exit 1 on mismatch
"""

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.schema import iqr as _iqr  # noqa: E402  (canonical definition)

RESULTS_DIR = ROOT / "results"

CSV_FIELDS = [
    "algo", "lang", "model", "impl", "status", "reps", "iters_per_rep",
    "mean_ms", "sd_ms", "median_ms", "iqr_ms",
    "speedup_mean", "speedup_median", "detail", "params",
]


def load_results(verify=False):
    rows = []
    mismatches = []
    incomplete = []
    for path in sorted(RESULTS_DIR.rglob("*.json")):
        if path.name in ("run_meta.json", "failures.json"):
            continue
        # Output of a run that failed after writing BENCH_OUT (see run.py's
        # quarantine_result); kept for diagnosis, never a measurement.
        if path.name.endswith(".failed.json"):
            continue
        if "archive" in path.relative_to(RESULTS_DIR).parts:
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            print(f"warning: skipping unreadable {path}: {e}", file=sys.stderr)
            continue
        if "elapsed_ms" not in data:
            continue

        ident = {
            "algo": data.get("algo", "?"),
            "lang": data.get("lang", "?"),
            "model": data.get("model", "unknown"),
            "impl": data.get("impl", "?"),
            "params": json.dumps(data.get("params", {}), separators=(",", ":")),
        }

        elapsed = data["elapsed_ms"]
        if not elapsed:
            # A "did not finish" sentinel: no samples to average, but the file
            # says why it did not finish and that is the whole point of it.
            # Carried through as a row so the reason reaches the summary
            # instead of being silently dropped (it used to abort the run).
            incomplete.append({
                **ident,
                "status": data.get("status", "no_samples"),
                "detail": data.get("detail") or data.get("note", ""),
                "reps": data.get("reps", 0),
                "iters_per_rep": data.get("iters_per_rep", ""),
                "mean_ms": None, "sd_ms": None, "median_ms": None, "iqr_ms": None,
                "source": str(path.relative_to(ROOT)),
            })
            continue
        mean = statistics.mean(elapsed)
        sd = statistics.stdev(elapsed) if len(elapsed) > 1 else 0.0
        median = statistics.median(elapsed)
        iqr = _iqr(elapsed) if len(elapsed) > 1 else 0.0

        # Cross-check stored stats against the raw samples.
        for name, recomputed in (("mean", mean), ("median", median)):
            stored = data.get(name)
            if stored is not None and abs(stored - recomputed) > max(1e-6, 1e-3 * abs(recomputed)):
                mismatches.append((str(path.relative_to(ROOT)), name, stored, recomputed))

        rows.append({
            **ident,
            "status": "ok",
            "detail": "",
            "reps": data.get("reps", len(elapsed)),
            "iters_per_rep": data.get("iters_per_rep", ""),
            "mean_ms": mean,
            "sd_ms": sd,
            "median_ms": median,
            "iqr_ms": iqr,
            "source": str(path.relative_to(ROOT)),
        })

    if incomplete:
        print(f"note: {len(incomplete)} combo(s) produced no samples:", file=sys.stderr)
        for r in incomplete:
            print(f"  {r['algo']}/{r['lang']} {r['model']}/{r['impl']}: "
                  f"{r['status']} — {r['detail'] or 'no reason recorded'}", file=sys.stderr)
    if mismatches:
        print(f"warning: {len(mismatches)} stored stat(s) disagree with raw elapsed_ms:",
              file=sys.stderr)
        for p, name, stored, recomputed in mismatches:
            print(f"  {p}: {name} stored={stored} recomputed={recomputed}", file=sys.stderr)
    if verify:
        sys.exit(1 if mismatches else 0)

    return rows + incomplete


def add_speedups(rows):
    """Join each row to its baseline seq row (same algo+lang) for speedup.

    The denominator must be the *baseline* sequential run. `--impl seq` is a
    supported combo for any model, so keying on impl alone let a model-authored
    seq result overwrite the real baseline and rescale every speedup in that
    algo x lang cell.
    """
    baseline = {}
    for r in rows:
        if r["impl"] != "seq" or r["model"] != "baseline" or r["status"] != "ok":
            continue
        key = (r["algo"], r["lang"])
        if key in baseline:
            print(f"warning: two baseline seq results for {key[0]}/{key[1]} "
                  f"({baseline[key]['source']}, {r['source']}); using the first",
                  file=sys.stderr)
            continue
        baseline[key] = r
    for r in rows:
        base = baseline.get((r["algo"], r["lang"]))
        r["speedup_mean"] = ""
        r["speedup_median"] = ""
        if not base or r["status"] != "ok":
            continue
        if r["mean_ms"] > 0 and base["mean_ms"] > 0:
            r["speedup_mean"] = base["mean_ms"] / r["mean_ms"]
        if r["median_ms"] > 0 and base["median_ms"] > 0:
            r["speedup_median"] = base["median_ms"] / r["median_ms"]
    return rows


def write_csv(rows, path):
    rows = sorted(rows, key=lambda r: (r["algo"], r["lang"], r["model"], r["impl"]))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            out = {k: r.get(k, "") for k in CSV_FIELDS}
            for k in ("mean_ms", "sd_ms", "median_ms", "iqr_ms", "speedup_mean", "speedup_median"):
                if isinstance(out[k], float):
                    out[k] = f"{out[k]:.4f}"
            w.writerow(out)


def _num(v, suffix=""):
    return f"{v:.2f}{suffix}" if isinstance(v, float) else "—"


def write_markdown(rows, path):
    rows = sorted(rows, key=lambda r: (r["algo"], r["lang"], r["model"], r["impl"]))
    algos = sorted({r["algo"] for r in rows})
    lines = ["# Benchmark summary", ""]
    for algo in algos:
        lines.append(f"## {algo}")
        lines.append("")
        lines.append("| lang | model | impl | mean (ms) | SD | median (ms) | IQR | speedup (mean) |")
        lines.append("|------|-------|------|-----------|----|-------------|-----|----------------|")
        for r in rows:
            if r["algo"] != algo:
                continue
            lines.append(
                f"| {r['lang']} | {r['model']} | {r['impl']} | "
                f"{_num(r['mean_ms'])} | {_num(r['sd_ms'])} | "
                f"{_num(r['median_ms'])} | {_num(r['iqr_ms'])} | "
                f"{_num(r['speedup_mean'], 'x')} |"
            )
        lines.append("")

    failed = [r for r in rows if r["status"] != "ok"]
    if failed:
        lines.append("## Combos with no measurement")
        lines.append("")
        lines.append("| algo | lang | model | impl | status | detail |")
        lines.append("|------|------|-------|------|--------|--------|")
        for r in failed:
            detail = (r["detail"] or "—").replace("|", "\\|")
            lines.append(
                f"| {r['algo']} | {r['lang']} | {r['model']} | {r['impl']} | "
                f"{r['status']} | {detail} |"
            )
        lines.append("")
    path.write_text("\n".join(lines))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--verify", action="store_true",
                   help="only check stored stats vs raw elapsed_ms; exit 1 on mismatch")
    args = p.parse_args()

    if not RESULTS_DIR.exists():
        print(f"no results dir at {RESULTS_DIR}", file=sys.stderr)
        sys.exit(1)

    rows = load_results(verify=args.verify)
    if not rows:
        print("no result JSONs found", file=sys.stderr)
        sys.exit(1)

    rows = add_speedups(rows)
    write_csv(rows, RESULTS_DIR / "summary.csv")
    write_markdown(rows, RESULTS_DIR / "summary.md")
    print(f"wrote {RESULTS_DIR / 'summary.csv'} and summary.md ({len(rows)} rows)")


if __name__ == "__main__":
    main()
