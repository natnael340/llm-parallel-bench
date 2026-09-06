#!/usr/bin/env python3
"""Plug-and-play benchmark runner.

Stages the selected implementation (baseline or an LLM model's code) into a
fixed staging directory, generates the entry-point adapter, builds the harness
against it, and runs the benchmark with the standard env contract
(IMPL, MODEL, BENCH_OUT, BENCH_REPS, BENCH_ITERS).

Zero-interference guarantees: all staging/compilation completes before the
benchmark process starts; the benchmark is launched as a single subprocess
awaited with a blocking wait (0% runner CPU); benchmarks never run in
parallel. Use --exec to replace the runner process entirely, or --print-cmd
to get the bare command.

Usage:
  python bench/run.py run --algo bfs --lang go --model gpt-5 --impl par
  python bench/run.py matrix [--algo bfs,sccs] [--skip-lang rust] [--smoke]
  python bench/run.py list
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench import recipes, schema  # noqa: E402

MANIFEST_DIR = ROOT / "bench" / "manifests"
RESULTS_DIR = ROOT / "results"
BUILD_DIR = ROOT / "bench" / "build"
DEFAULT_TIMEOUT_S = 1800


@dataclass
class Ctx:
    root: Path
    algo: str
    lang: str
    model: str
    impl: str
    manifest: dict
    variant: dict
    harness_dir: Path
    staging_dir: Path
    bin_dir: Path
    out_path: Path


def load_manifest(algo: str, lang: str) -> dict:
    path = MANIFEST_DIR / algo / f"{lang}.json"
    if not path.is_file():
        raise FileNotFoundError(f"no manifest for {algo}/{lang} ({path})")
    return json.loads(path.read_text())


def iter_manifests():
    for algo_dir in sorted(MANIFEST_DIR.iterdir()):
        if not algo_dir.is_dir():
            continue
        for mf in sorted(algo_dir.glob("*.json")):
            yield algo_dir.name, mf.stem, json.loads(mf.read_text())


def make_ctx(algo: str, lang: str, model: str, impl: str, manifest: dict) -> Ctx:
    variant_key = f"{model}/{impl}"
    variants = manifest.get("variants", {})
    if variant_key not in variants:
        raise KeyError(
            f"variant {variant_key!r} not in manifest {algo}/{lang} "
            f"(available: {', '.join(sorted(variants))})"
        )
    harness_dir = ROOT / manifest["harness"]
    if lang == "rust":
        staging_dir = ROOT / "bench" / "rust" / "src" / "staged"
    else:
        staging_dir = harness_dir / "staging"
    return Ctx(
        root=ROOT,
        algo=algo,
        lang=lang,
        model=model,
        impl=impl,
        manifest=manifest,
        variant=variants[variant_key],
        harness_dir=harness_dir,
        staging_dir=staging_dir,
        bin_dir=BUILD_DIR / algo / lang,
        out_path=RESULTS_DIR / algo / lang / f"{model}_{impl}.json",
    )


def bench_env(ctx: Ctx, reps: int, iters: int, out_path: Path) -> dict:
    env = dict(os.environ)
    env.update(
        IMPL=ctx.impl,
        MODEL=ctx.model,
        BENCH_OUT=str(out_path),
        BENCH_REPS=str(reps),
        BENCH_ITERS=str(iters),
    )
    for k, v in ctx.manifest.get("env", {}).items():
        env[k] = str(ROOT / v) if isinstance(v, str) and v.startswith("./") else str(v)
    return env


def run_captured(argv, cwd, timeout=600, env=None):
    return subprocess.run(
        argv, cwd=str(cwd), env=env, timeout=timeout,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


class CombRunError(Exception):
    def __init__(self, stage, message, output=""):
        super().__init__(message)
        self.stage = stage
        self.output = output


def _report_quarantine(dest) -> None:
    if dest is not None:
        print(f"   kept the failing run's output at {dest.relative_to(ROOT)}")


def quarantine_result(out_path: Path) -> "Path | None":
    """Move aside a result JSON written by a run that then failed.

    Several harnesses run their timed section even after a correctness failure
    and write BENCH_OUT before exiting non-zero. Such a file must not stay at
    out_path -- cmd_matrix treats anything there as a completed run and skips
    it -- but it is still the best evidence of what the failing run did, so it
    is kept alongside as <name>.failed.json rather than deleted. aggregate.py
    ignores that suffix.
    """
    if not out_path.exists():
        return None
    dest = out_path.with_suffix(".failed.json")
    dest.unlink(missing_ok=True)
    out_path.rename(dest)
    return dest


def stage_and_build(ctx: Ctx, verbose: bool = False) -> None:
    recipe = recipes.get(ctx.lang)
    recipe.stage(ctx)
    ctx.bin_dir.mkdir(parents=True, exist_ok=True)
    for argv, cwd in recipe.build_cmds(ctx):
        if verbose:
            print(f"  [build] {' '.join(map(str, argv))}")
        proc = run_captured(argv, cwd)
        if proc.returncode != 0:
            raise CombRunError("build", f"build failed (rc={proc.returncode})", proc.stdout)


def combo_reps_iters(ctx: Ctx, reps=None, iters=None, smoke=False):
    if smoke:
        return 1, 1
    r = reps if reps is not None else ctx.manifest.get("default_reps", 5)
    i = iters if iters is not None else ctx.manifest.get("default_iters", 20)
    return r, i


def run_combo(ctx: Ctx, reps=None, iters=None, timeout=None, smoke=False,
              print_cmd=False, exec_mode=False, verbose=True) -> dict:
    label = f"{ctx.algo}/{ctx.lang} {ctx.model}/{ctx.impl}"
    reps, iters = combo_reps_iters(ctx, reps, iters, smoke)
    timeout = timeout or ctx.manifest.get("timeout_s", DEFAULT_TIMEOUT_S)

    print(f"== {label} (reps={reps}, iters={iters})")
    stage_and_build(ctx, verbose=verbose)

    out_path = ctx.bin_dir / "smoke_result.json" if smoke else ctx.out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    recipe = recipes.get(ctx.lang)
    argv, cwd = recipe.run_cmd(ctx)
    env = bench_env(ctx, reps, iters, out_path)

    if print_cmd:
        # Includes the manifest's own env block (e.g. SW_INPUT); without it the
        # printed command silently benchmarks nothing.
        names = ["IMPL", "MODEL", "BENCH_OUT", "BENCH_REPS", "BENCH_ITERS"]
        names += [k for k in ctx.manifest.get("env", {}) if k not in names]
        env_vars = " ".join(f"{k}={env[k]}" for k in names)
        print(f"cd {cwd} && {env_vars} {' '.join(map(str, argv))}")
        return {}

    # Drop any previous result only once we are committed to running. Deleting
    # earlier means a flag that never runs anything (--print-cmd) destroys a
    # measurement, and a run that fails leaves the old file behind for
    # cmd_matrix to mistake for a completed result.
    out_path.unlink(missing_ok=True)

    if exec_mode:
        # Replace the runner process entirely: nothing else is alive during
        # measurement. Result JSON lands at BENCH_OUT.
        os.chdir(str(cwd))
        os.execvpe(argv[0], [str(a) for a in argv], env)

    start = time.time()
    try:
        proc = run_captured(argv, cwd, timeout=timeout, env=env)
    except BaseException:
        _report_quarantine(quarantine_result(out_path))
        raise
    elapsed = time.time() - start
    if proc.returncode != 0:
        _report_quarantine(quarantine_result(out_path))
        raise CombRunError("run", f"benchmark failed (rc={proc.returncode})", proc.stdout)

    expect = {
        "algo": ctx.algo, "lang": ctx.lang, "impl": ctx.impl,
        "model": ctx.model, "reps": reps, "iters_per_rep": iters,
    }
    try:
        data = schema.load_and_validate(out_path, expect)
    except schema.SchemaError as e:
        _report_quarantine(quarantine_result(out_path))
        raise CombRunError("validate", str(e), proc.stdout)

    stat = (f"mean {data['mean']:.2f} ms ± {data['sd']:.2f} SD | "
            f"median {data['median']:.2f} ms ± {data['iqr']:.2f} IQR")
    print(f"   ok in {elapsed:.0f}s: {stat}")
    if verbose and proc.stdout.strip():
        tail = proc.stdout.strip().splitlines()[-8:]
        for line in tail:
            print(f"   | {line}")
    return data


def write_run_meta():
    RESULTS_DIR.mkdir(exist_ok=True)
    meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
    }
    (RESULTS_DIR / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n")


def record_failure(ctx: Ctx, err: CombRunError):
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / "failures.json"
    failures = json.loads(path.read_text()) if path.exists() else []
    failures.append({
        "algo": ctx.algo, "lang": ctx.lang, "model": ctx.model, "impl": ctx.impl,
        "stage": err.stage, "error": str(err),
        "output_tail": err.output.strip().splitlines()[-30:],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    path.write_text(json.dumps(failures, indent=2) + "\n")


def parse_filter(value):
    return set(value.split(",")) if value else None


def cmd_run(args):
    manifest = load_manifest(args.algo, args.lang)
    ctx = make_ctx(args.algo, args.lang, args.model, args.impl, manifest)
    write_run_meta()
    try:
        run_combo(ctx, reps=args.reps, iters=args.iters, timeout=args.timeout,
                  smoke=args.smoke, print_cmd=args.print_cmd, exec_mode=getattr(args, "exec"))
    except CombRunError as e:
        print(f"FAILED [{e.stage}] {e}", file=sys.stderr)
        if e.output:
            print(e.output[-4000:], file=sys.stderr)
        # Single runs used to leave no trace on disk; only matrix logged them.
        record_failure(ctx, e)
        print(f"recorded in {(RESULTS_DIR / 'failures.json')}", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("FAILED [timeout]", file=sys.stderr)
        record_failure(ctx, CombRunError("timeout", f"exceeded {args.timeout or DEFAULT_TIMEOUT_S}s"))
        sys.exit(1)


def cmd_matrix(args):
    only_algo = parse_filter(args.algo)
    only_lang = parse_filter(args.lang)
    skip_lang = parse_filter(args.skip_lang) or set()
    only_model = parse_filter(args.model)
    only_impl = parse_filter(args.impl)

    write_run_meta()
    ran = skipped = failed = 0
    for algo, lang, manifest in iter_manifests():
        if only_algo and algo not in only_algo:
            continue
        if (only_lang and lang not in only_lang) or lang in skip_lang:
            continue
        for variant_key in manifest.get("variants", {}):
            model, impl = variant_key.rsplit("/", 1)
            if only_model and model not in only_model:
                continue
            if only_impl and impl not in only_impl:
                continue
            ctx = make_ctx(algo, lang, model, impl, manifest)
            if not args.smoke and not args.force and ctx.out_path.exists():
                print(f"-- {algo}/{lang} {variant_key}: result exists, skipping (use --force)")
                skipped += 1
                continue
            try:
                run_combo(ctx, reps=args.reps, iters=args.iters,
                          timeout=args.timeout, smoke=args.smoke)
                ran += 1
            except CombRunError as e:
                print(f"   FAILED [{e.stage}] {e}")
                if e.output:
                    for line in e.output.strip().splitlines()[-10:]:
                        print(f"   ! {line}")
                record_failure(ctx, e)
                failed += 1
            except subprocess.TimeoutExpired:
                print("   FAILED [timeout]")
                record_failure(ctx, CombRunError("timeout", "timed out"))
                failed += 1
    print(f"\nmatrix done: {ran} ran, {skipped} skipped, {failed} failed")
    if failed:
        print(f"failure details: {RESULTS_DIR / 'failures.json'}")
        sys.exit(1)


def cmd_list(args):
    for algo, lang, manifest in iter_manifests():
        variants = ", ".join(sorted(manifest.get("variants", {})))
        print(f"{algo:16s} {lang:8s} reps={manifest.get('default_reps', 5)}x"
              f"{manifest.get('default_iters', 20):<4d} {variants}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("run", help="run one algo/lang/model/impl combo")
    pr.add_argument("--algo", required=True)
    pr.add_argument("--lang", required=True)
    pr.add_argument("--model", default="baseline")
    pr.add_argument("--impl", default=None, choices=[None, "seq", "par"])
    pr.add_argument("--reps", type=int)
    pr.add_argument("--iters", type=int)
    pr.add_argument("--timeout", type=int)
    pr.add_argument("--smoke", action="store_true", help="reps=1 iters=1, don't persist result")
    pr.add_argument("--print-cmd", action="store_true", help="stage+build, print the bare run command")
    pr.add_argument("--exec", action="store_true", help="stage+build, then exec the benchmark (replaces runner)")
    pr.set_defaults(func=cmd_run)

    pm = sub.add_parser("matrix", help="run all (or filtered) combos from manifests")
    pm.add_argument("--algo", help="comma-separated filter")
    pm.add_argument("--lang", help="comma-separated filter")
    pm.add_argument("--skip-lang", help="comma-separated exclusion")
    pm.add_argument("--model", help="comma-separated filter")
    pm.add_argument("--impl", help="comma-separated filter (seq,par)")
    pm.add_argument("--reps", type=int)
    pm.add_argument("--iters", type=int)
    pm.add_argument("--timeout", type=int)
    pm.add_argument("--smoke", action="store_true")
    pm.add_argument("--force", action="store_true", help="re-run combos whose result JSON exists")
    pm.set_defaults(func=cmd_matrix)

    pl = sub.add_parser("list", help="list runnable combos")
    pl.set_defaults(func=cmd_list)

    args = p.parse_args()
    if args.cmd == "run" and args.impl is None:
        args.impl = "seq" if args.model == "baseline" else "par"
    args.func(args)


if __name__ == "__main__":
    main()
