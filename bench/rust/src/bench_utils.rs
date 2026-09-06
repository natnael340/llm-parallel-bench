//! Shared benchmark harness for all Rust benchmarks. Mirrors
//! tests/bench_utils.py: reps x iters timing with warmup, median/IQR and
//! mean/SD statistics, and the schema-v2 JSON result format.

use std::env;
use std::fs;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

pub struct BenchResult {
    pub elapsed_ms: Vec<f64>,
    pub median: f64,
    pub iqr: f64,
    pub mean: f64,
    pub sd: f64,
    pub reps: usize,
    pub iters: usize,
}

// --- env helpers: the standard benchmark env contract ---

fn env_int(name: &str, def: usize) -> usize {
    env::var(name).ok().and_then(|v| v.parse().ok()).unwrap_or(def)
}

pub fn reps(def: usize) -> usize {
    env_int("BENCH_REPS", def)
}
pub fn iters(def: usize) -> usize {
    env_int("BENCH_ITERS", def)
}
pub fn impl_name() -> String {
    env::var("IMPL").unwrap_or_else(|_| "seq".to_string())
}
pub fn model() -> String {
    env::var("MODEL").unwrap_or_else(|_| "baseline".to_string())
}
pub fn out_path() -> String {
    env::var("BENCH_OUT").unwrap_or_default()
}

// --- statistics ---

fn median(vals: &[f64]) -> f64 {
    let mut s = vals.to_vec();
    s.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = s.len();
    if n % 2 == 0 {
        (s[n / 2 - 1] + s[n / 2]) / 2.0
    } else {
        s[n / 2]
    }
}

/// Interquartile range using the same definition as Python's
/// `statistics.quantiles(data, n=4)` (exclusive, interpolated), so the
/// dispersion figure is comparable across all six languages and matches what
/// bench/aggregate.py recomputes. The previous truncated nearest-rank indexing
/// disagreed with the Python harness on identical samples.
fn iqr(vals: &[f64]) -> f64 {
    let mut s = vals.to_vec();
    s.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = s.len();
    if n < 2 {
        return 0.0;
    }
    const NQ: usize = 4;
    let m = n + 1;
    let mut q = [0.0f64; 3];
    for i in 1..=3 {
        let j = (i * m / NQ).clamp(1, n - 1);
        // Signed: the clamp above can make j*NQ exceed i*m (n = 2), and usize
        // subtraction would underflow to a huge value instead of going negative.
        let delta = (i * m) as f64 - (j * NQ) as f64;
        q[i - 1] = (s[j - 1] * (NQ as f64 - delta) + s[j] * delta) / NQ as f64;
    }
    q[2] - q[0]
}

fn mean(vals: &[f64]) -> f64 {
    vals.iter().sum::<f64>() / vals.len() as f64
}

fn sd(vals: &[f64]) -> f64 {
    if vals.len() < 2 {
        return 0.0;
    }
    let m = mean(vals);
    let sq: f64 = vals.iter().map(|v| (v - m) * (v - m)).sum();
    (sq / (vals.len() - 1) as f64).sqrt()
}

/// Runs `warmup` untimed calls, then `reps` timed blocks of `iters` calls
/// each, recording per-block mean time per call in milliseconds.
pub fn run_benchmark<F: FnMut()>(mut f: F, reps: usize, iters: usize, warmup: usize) -> BenchResult {
    for _ in 0..warmup {
        f();
    }
    let mut per_run_ms = Vec::with_capacity(reps);
    for _ in 0..reps {
        let start = Instant::now();
        for _ in 0..iters {
            f();
        }
        let elapsed = start.elapsed().as_secs_f64() * 1000.0;
        per_run_ms.push(elapsed / iters as f64);
    }
    BenchResult {
        median: median(&per_run_ms),
        iqr: iqr(&per_run_ms),
        mean: mean(&per_run_ms),
        sd: sd(&per_run_ms),
        elapsed_ms: per_run_ms,
        reps,
        iters,
    }
}

pub fn format_result(label: &str, r: &BenchResult) -> String {
    format!(
        "{} | mean {:.2} ms/run ± {:.2} SD | median {:.2} ms/run ± {:.2} IQR (n={})",
        label, r.mean, r.sd, r.median, r.iqr, r.reps
    )
}

/// Minimal JSON string escaping. Values reaching the result file come from the
/// environment (MODEL, IMPL) and from callers, so they are not guaranteed to be
/// JSON-safe; an unescaped quote or backslash silently produced a file the
/// runner then failed to parse.
fn json_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

/// Current UTC time as an ISO-8601 string, matching the other five harnesses.
/// Implemented from the epoch directly (civil-from-days) to avoid adding a
/// date dependency to the benchmark crate.
fn timestamp_utc() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);
    let (days, rem) = (secs.div_euclid(86_400), secs.rem_euclid(86_400));
    let (hh, mm, ss) = (rem / 3600, (rem % 3600) / 60, rem % 60);

    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{:04}-{:02}-{:02}T{:02}:{:02}:{:02}+00:00", y, m, d, hh, mm, ss)
}

/// Writes the schema-v2 JSON result to BENCH_OUT (no-op if empty).
/// `params_json` is a pre-rendered JSON object, e.g. r#"{"graph_size": 2000}"#.
pub fn write_result(r: &BenchResult, algo: &str, impl_str: &str, params_json: &str) {
    let path = out_path();
    if path.is_empty() {
        return;
    }
    let params = if params_json.is_empty() { "{}" } else { params_json };
    // NaN/Infinity are not valid JSON; they arise only from a degenerate run
    // (reps = 0 makes mean 0/0), and writing them produces a file the runner
    // cannot parse, with no hint as to the cause.
    for (name, v) in [("mean", r.mean), ("sd", r.sd), ("median", r.median), ("iqr", r.iqr)] {
        if !v.is_finite() {
            eprintln!("bench: refusing to write non-finite {} ({}); check BENCH_REPS/BENCH_ITERS", name, v);
            std::process::exit(2);
        }
    }
    let elapsed: Vec<String> = r.elapsed_ms.iter().map(|v| format!("{}", v)).collect();
    let json = format!(
        "{{\n  \"schema_version\": 2,\n  \"algo\": \"{}\",\n  \"lang\": \"rust\",\n  \"impl\": \"{}\",\n  \"model\": \"{}\",\n  \"elapsed_ms\": [{}],\n  \"mean\": {},\n  \"sd\": {},\n  \"median\": {},\n  \"iqr\": {},\n  \"reps\": {},\n  \"iters_per_rep\": {},\n  \"params\": {},\n  \"timestamp\": \"{}\"\n}}\n",
        json_escape(algo), json_escape(impl_str), json_escape(&model()), elapsed.join(", "),
        r.mean, r.sd, r.median, r.iqr, r.reps, r.iters, params, timestamp_utc()
    );
    // A discarded write error meant a failed write left the previous result in
    // place, which the runner would then read as if this run had produced it.
    if let Err(e) = fs::write(&path, json) {
        eprintln!("bench: cannot write result to {}: {}", path, e);
        std::process::exit(2);
    }
}

