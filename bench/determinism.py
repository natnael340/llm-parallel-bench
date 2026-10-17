#!/usr/bin/env python3
"""Determinism sweep: rerun each parallel variant under varied scheduling
conditions and check its output against itself and the baseline sequential run.

Usage:
  python bench/determinism.py sweep [--algo bfs] [--lang go] [--model gpt-5] [--sweep cores,load]
  python bench/determinism.py report
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import struct
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench import recipes  # noqa: E402
from bench.run import (  # noqa: E402
    BUILD_DIR, RESULTS_DIR, CombRunError, bench_env, iter_manifests, make_ctx,
    parse_filter, run_captured, stage_and_build,
)

OUT_DIR = RESULTS_DIR / "determinism"
DUMP_DIR = BUILD_DIR / "determinism"
NCPU = os.cpu_count()
RACE_LANGS = {"go", "cpp"}
SPIN = {"cpu": "while True: pass",
        "mem": "a = bytearray(64 << 20)\nwhile True: b = bytes(a)"}
SCHED = {"normal": [], "nice19": ["nice", "-n", "19"],
         "batch": ["chrt", "--batch", "0"], "idle": ["chrt", "--idle", "0"]}


@dataclass(frozen=True)
class Condition:
    sweep: str
    cores: int
    threads: int
    load: str = "none"
    load_procs: int = 0
    sched: str = "normal"
    race: bool = False

    @property
    def name(self):
        parts = [f"c{self.cores}", f"t{self.threads}"]
        if self.load_procs:
            parts.append(f"{self.load}x{self.load_procs}")
        if self.sched != "normal":
            parts.append(self.sched)
        if self.race:
            parts.append("race")
        return "-".join(parts)

    def key(self):
        return (self.cores, self.threads, self.load, self.load_procs, self.sched, self.race)


def conditions(sweeps):
    conds = [Condition("cores", k, k) for k in (1, 2, 4, 8, NCPU)]
    conds += [Condition("threads", 4, t) for t in (1, 2, 4, 8, 16, 32)]
    conds += [Condition("load", 4, 4, kind, n) for kind, n in (("cpu", 4), ("cpu", 8), ("mem", 8))]
    conds += [Condition("priority", 4, 4, "cpu", 2, s) for s in ("nice19", "batch", "idle")]
    conds += [Condition("race", k, k, race=True) for k in (NCPU, 2)]
    seen, out = set(), []
    for c in conds:
        if c.sweep in sweeps and c.key() not in seen:
            seen.add(c.key())
            out.append(c)
    return out


def thread_env(threads):
    return {k: str(threads) for k in ("GOMAXPROCS", "OMP_NUM_THREADS", "RAYON_NUM_THREADS",
                                      "DOTNET_PROCESSOR_COUNT", "BENCH_CPU_COUNT")}


def build(ctx, race):
    if not race:
        stage_and_build(ctx)
        return
    recipe = recipes.get(ctx.lang)
    recipe.stage(ctx)
    for argv, cwd in recipe.build_cmds(ctx, race=True):
        proc = run_captured(argv, cwd)
        if proc.returncode != 0:
            raise CombRunError("build", f"race build failed (rc={proc.returncode})", proc.stdout)


def start_load(cond):
    mask = f"0-{cond.cores - 1}"
    procs = [subprocess.Popen(["taskset", "-c", mask, sys.executable, "-c", SPIN[cond.load]])
             for _ in range(cond.load_procs)]
    if procs:
        time.sleep(1)
    return procs


def stop_load(procs):
    for p in procs:
        p.kill()
    for p in procs:
        p.wait()


def parse_dump(path):
    meta, body = {}, []
    for line in path.read_text().splitlines():
        if line.startswith("# "):
            k, _, v = line[2:].partition(" ")
            meta[k] = v
        else:
            body.append(line)
    return meta, body


def canonical(algo, body):
    """Output in a form where only meaningful differences remain."""
    if algo != "sccs":
        return body
    sccs = sorted(" ".join(map(str, sorted(map(int, l.split()[1:])))) for l in body if l[0] == "S")
    edges = sorted((tuple(map(int, l.split()[1:])) for l in body if l[0] == "E"))
    return [f"S {s}" for s in sccs] + [f"E {u} {v}" for u, v in edges]


def baseline_view(algo, canon):
    """The part of the canonical output that must equal the baseline's."""
    if algo == "sccs":
        return [l for l in canon if l[0] == "S"]
    return canon


def sha(lines):
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def gemm_diff(a, b):
    def floats(lines):
        return [struct.unpack(">d", bytes.fromhex(x))[0] for l in lines for x in l.split()]
    fa, fb = floats(a), floats(b)
    if len(fa) != len(fb):
        return {"shape_mismatch": True}
    abs_d = max((abs(x - y) for x, y in zip(fa, fb)), default=0.0)
    rel_d = max((abs(x - y) / max(abs(y), 1e-300) for x, y in zip(fa, fb)), default=0.0)
    return {"max_abs_diff": abs_d, "max_rel_diff": rel_d}


RACE_RE = re.compile(r"WARNING: (?:DATA RACE|ThreadSanitizer: data race)")
LOC_RE = re.compile(r"\S+\.(?:go|cpp|hpp|h|cc):\d+")


def count_races(output):
    reports = RACE_RE.split(output)[1:]
    unique = {tuple(LOC_RE.findall(r.split("\n\n")[0])[:4]) for r in reports}
    return len(reports), len(unique)


def run_once(ctx, cond, dump_path, timeout):
    argv, cwd = recipes.get(ctx.lang).run_cmd(ctx)
    if ctx.lang == "java":
        argv = [argv[0], f"-XX:ActiveProcessorCount={cond.threads}", *argv[1:]]
    # gcc 11 TSan can't handle WSL2's mmap randomisation; running without ASLR avoids it.
    no_aslr = ["setarch", "-R"] if cond.race else []
    argv = [*no_aslr, "taskset", "-c", f"0-{cond.cores - 1}", *SCHED[cond.sched], *argv]
    env = bench_env(ctx, 1, 1, ctx.bin_dir / "unused_result.json")
    env.update(thread_env(cond.threads), BENCH_DIGEST_OUT=str(dump_path),
               GORACE="halt_on_error=0", TSAN_OPTIONS="halt_on_error=0 exitcode=0")
    dump_path.unlink(missing_ok=True)

    load = start_load(cond)
    start = datetime.now()
    try:
        proc = run_captured(argv, cwd, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"outcome": "timeout"}
    finally:
        stop_load(load)
    rec = {"rc": proc.returncode, "wall_s": round((datetime.now() - start).total_seconds(), 2)}
    if cond.race:
        rec["race_reports"], rec["races_unique"] = count_races(proc.stdout)
    if proc.returncode != 0 or not dump_path.exists():
        rec["output_tail"] = proc.stdout.strip().splitlines()[-15:]
    if not dump_path.exists():
        rec["outcome"] = "fail"
        return rec
    meta, body = parse_dump(dump_path)
    canon = canonical(ctx.algo, body)
    rec.update(outcome="ok", detected=meta, raw_sha=sha(body), canon_sha=sha(canon))
    rec["_canon"] = canon
    return rec


def reference(algo, lang, manifest, timeout, force):
    """Baseline sequential output, cached across sweeps."""
    path = DUMP_DIR / algo / lang / "baseline_seq.txt"
    if path.exists() and not force:
        return canonical(algo, parse_dump(path)[1])
    ctx = make_ctx(algo, lang, "baseline", "seq", manifest)
    build(ctx, race=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = run_once(ctx, Condition("cores", NCPU, NCPU), path, timeout)
    if rec["outcome"] != "ok":
        raise CombRunError("baseline", f"baseline seq {rec['outcome']}", "\n".join(rec.get("output_tail", [])))
    return rec["_canon"]


def sweep_variant(ctx, conds, runs, ref, timeout):
    dump_dir = DUMP_DIR / ctx.algo / ctx.lang / ctx.model
    dump_dir.mkdir(parents=True, exist_ok=True)
    records, first_canon, first_raw, divergence = [], None, None, None
    built_race = None
    for cond in conds:
        if cond.race and ctx.lang not in RACE_LANGS:
            continue
        if built_race is not cond.race:
            build(ctx, cond.race)
            built_race = cond.race
        for rep in range(1, runs + 1):
            dump = dump_dir / f"{cond.name}_r{rep}.txt"
            rec = {"condition": cond.name, "sweep": cond.sweep, "rep": rep,
                   **run_once(ctx, cond, dump, timeout)}
            print(f"   {cond.name:20s} r{rep}: {rec['outcome']}"
                  + (f" races={rec['races_unique']}" if rec.get("race_reports") else ""))
            canon = rec.pop("_canon", None)
            if canon is not None:
                if first_canon is None:
                    first_canon, first_raw = canon, rec["raw_sha"]
                    dump.rename(dump_dir / "first.txt")
                elif rec["canon_sha"] != sha(first_canon) and divergence is None:
                    divergence = cond.name
                    dump.rename(dump_dir / "divergent.txt")
                else:
                    dump.unlink()
            records.append(rec)
            if rec["outcome"] == "timeout":
                break
        if not records or records[0]["outcome"] == "timeout":
            break

    ok = [r for r in records if r["outcome"] == "ok"]
    verdict = {
        "runs_ok": len(ok),
        "runs_failed": sum(r["outcome"] == "fail" for r in records),
        "runs_timeout": sum(r["outcome"] == "timeout" for r in records),
        "runs_tests_failed": sum(r["outcome"] == "ok" and r["rc"] != 0 and not r.get("race_reports")
                                 for r in records),
        "deterministic": len({r["canon_sha"] for r in ok}) == 1 if ok else None,
        "raw_order_stable": len({r["raw_sha"] for r in ok}) == 1 if ok else None,
        "first_divergence": divergence,
        "races_unique": max((r.get("races_unique", 0) for r in records), default=0),
        "matches_baseline": None,
    }
    if first_canon is not None:
        verdict["matches_baseline"] = baseline_view(ctx.algo, first_canon) == baseline_view(ctx.algo, ref)
        if ctx.algo == "gemm" and not verdict["matches_baseline"]:
            verdict.update(gemm_diff(first_canon, ref))
    if ctx.lang == "cpp":
        flags = ctx.manifest.get("cxxflags", []) + ctx.variant.get("cxxflags", [])
        verdict["openmp_tsan_false_positives_possible"] = "-fopenmp" in flags
    threads_sweep = {tuple(sorted(r["detected"].items())) for r in ok if r["sweep"] == "threads"}
    verdict["threads_override_effective"] = len(threads_sweep) > 1 if threads_sweep else None
    return verdict, records


def cmd_sweep(args):
    sweeps = parse_filter(args.sweep) or {"cores", "threads", "load", "priority", "race"}
    only_algo, only_lang, only_model = map(parse_filter, (args.algo, args.lang, args.model))
    conds = conditions(sweeps)
    meta = {"timestamp": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(),
            "cpu_count": NCPU, "runs_per_condition": args.runs,
            "conditions": [{"name": c.name, **asdict(c)} for c in conds]}
    failed = 0
    for algo, lang, manifest in iter_manifests():
        if (only_algo and algo not in only_algo) or (only_lang and lang not in only_lang):
            continue
        pars = [k.rsplit("/", 1)[0] for k in manifest["variants"] if k.endswith("/par")]
        pars = [m for m in pars if not only_model or m in only_model]
        todo = [m for m in pars if args.force or not (OUT_DIR / algo / lang / f"{m}_par.json").exists()]
        if not todo:
            continue
        try:
            ref = reference(algo, lang, manifest, args.timeout, args.force)
        except CombRunError as e:
            print(f"!! {algo}/{lang} baseline: {e}\n{e.output[-2000:]}")
            failed += 1
            continue
        for model in todo:
            ctx = make_ctx(algo, lang, model, "par", manifest)
            print(f"== {algo}/{lang} {model}/par")
            try:
                verdict, records = sweep_variant(ctx, conds, args.runs, ref, args.timeout)
            except CombRunError as e:
                verdict, records = {"build_failed": str(e), "output_tail": e.output.splitlines()[-15:]}, []
                failed += 1
            out = OUT_DIR / algo / lang / f"{model}_par.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"algo": algo, "lang": lang, "model": model, "verdict": verdict,
                                       "runs": records, "meta": meta}, indent=2) + "\n")
            print(f"   verdict: {json.dumps(verdict)}")
    cmd_report(args)
    sys.exit(1 if failed else 0)


def fmt(v):
    return {True: "yes", False: "NO", None: "–"}[v] if v is None or isinstance(v, bool) else v


def cmd_report(_args):
    rows = []
    for path in sorted(OUT_DIR.glob("*/*/*_par.json")):
        d = json.loads(path.read_text())
        v = d["verdict"]
        rows.append({"algo": d["algo"], "lang": d["lang"], "model": d["model"],
                     "status": "build failed" if "build_failed" in v else "ran",
                     **{k: v.get(k) for k in ("deterministic", "matches_baseline", "first_divergence",
                                               "raw_order_stable", "races_unique", "runs_ok",
                                               "runs_failed", "runs_tests_failed", "runs_timeout",
                                               "threads_override_effective", "max_abs_diff")}})
    if not rows:
        print("no determinism results yet")
        return
    with open(OUT_DIR / "summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    cols = list(rows[0])
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(fmt(r[c])) for c in cols) + " |" for r in rows]
    (OUT_DIR / "summary.md").write_text("# Determinism sweep\n\n" + "\n".join(lines) + "\n")
    print(f"wrote {OUT_DIR / 'summary.csv'} and summary.md ({len(rows)} rows)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("sweep", help="run the determinism sweep")
    ps.add_argument("--algo")
    ps.add_argument("--lang")
    ps.add_argument("--model")
    ps.add_argument("--sweep", help="comma-separated: cores,threads,load,priority,race")
    ps.add_argument("--runs", type=int, default=3)
    ps.add_argument("--timeout", type=int, default=1800, help="per-run seconds")
    ps.add_argument("--force", action="store_true", help="redo variants with existing results")
    ps.set_defaults(func=cmd_sweep)
    sub.add_parser("report", help="rebuild summary from result JSONs").set_defaults(func=cmd_report)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
