# fast_gemm_sweep.py
import gc, time, random, itertools, csv, math, statistics as stats
from typing import List, Tuple, Optional

# ==== your GEMM import ====
from baselines.gemm.python.gemm_seq import gemm  # use the optimized version you wrote; or your current gemm

# ---- helpers ----
def make_random_matrix(r: int, c: int, seed=0) -> List[List[float]]:
    rng = random.Random(seed)
    return [[rng.uniform(-1.0, 1.0) for _ in range(c)] for _ in range(r)]

def gflops(m,n,k,seconds): return (2.0*m*n*k)/(seconds*1e9)

def time_avg_per_run(fn, min_wall=0.6, warmup=1) -> float:
    """Run fn repeatedly until total wall >= min_wall. Return avg seconds/run."""
    for _ in range(warmup):
        fn()
    total = 0.0
    runs = 0
    gc_enabled = gc.isenabled()
    try:
        gc.disable()
        t0 = time.perf_counter()
        while total < min_wall:
            t1 = time.perf_counter()
            fn()
            runs += 1
            total = time.perf_counter() - t0
    finally:
        if gc_enabled:
            gc.enable()
    return total / max(runs, 1)

def eval_config(A, B, MB, NB, KB, repeats=3, min_wall=0.6):
    """Return (avg_ms, sd_ms, gflops_val) for this tile triplet."""
    samples = []
    for _ in range(repeats):
        avg = time_avg_per_run(lambda: gemm(A, B, 1.0, None, 0.0, MB, NB, KB), min_wall=min_wall, warmup=1)
        samples.append(avg)
    avg_s = sum(samples) / len(samples)
    sd_s = stats.pstdev(samples)  # population sd across repeats
    m = len(A); k = len(A[0]); n = len(B[0])
    return avg_s*1000.0, sd_s*1000.0, gflops(m, n, k, avg_s)

# ---- staged sweep ----
def staged_sweep(m=512, n=512, k=512,
                 kb_list=(16,32,48,64,96,128),
                 coarse=(8,16,32,48,64),
                 step_refine=8,
                 top_kb=2, top_mb_nb=5,
                 repeats=3, min_wall=0.6,
                 csv_path="gemm_sweep_staged.csv",
                 seedA=1, seedB=2):
    A = make_random_matrix(m, k, seed=seedA)
    B = make_random_matrix(k, n, seed=seedB)

    rows = []

    # Stage 1: scan KB with MB=NB=32
    kb_scores = []
    for KB in kb_list:
        avg_ms, sd_ms, flops = eval_config(A, B, MB=32, NB=32, KB=KB, repeats=repeats, min_wall=min_wall)
        rows.append(dict(stage=1, MB=32, NB=32, KB=KB, avg_ms=avg_ms, sd_ms=sd_ms, gflops=flops))
        kb_scores.append((flops, KB))
    kb_scores.sort(reverse=True)
    chosen_kb = [KB for _, KB in kb_scores[:top_kb]]

    # Stage 2: coarse MB/NB for each chosen KB
    mbnb_candidates = set()
    for KB in chosen_kb:
        scored = []
        for MB, NB in itertools.product(coarse, coarse):
            avg_ms, sd_ms, flops = eval_config(A, B, MB=MB, NB=NB, KB=KB, repeats=repeats, min_wall=min_wall)
            rows.append(dict(stage=2, MB=MB, NB=NB, KB=KB, avg_ms=avg_ms, sd_ms=sd_ms, gflops=flops))
            scored.append((flops, MB, NB))
        scored.sort(reverse=True)
        for _, MB, NB in scored[:top_mb_nb]:
            mbnb_candidates.add((MB, NB, KB))

    # Stage 3: local refinement around each (MB,NB,KB)
    def clamp(v, lo, hi): return max(lo, min(hi, v))
    refined = set()
    for MB, NB, KB in mbnb_candidates:
        for dmb in (-step_refine, 0, step_refine):
            for dnb in (-step_refine, 0, step_refine):
                MB2 = clamp(MB + dmb, 4, m)   # keep valid
                NB2 = clamp(NB + dnb, 4, n)
                # snap to multiples of 4 to keep search small & aligned
                MB2 = int(math.floor(MB2/4)*4)
                NB2 = int(math.floor(NB2/4)*4)
                if MB2 <= 0 or NB2 <= 0: continue
                refined.add((MB2, NB2, KB))

    for MB, NB, KB in sorted(refined):
        avg_ms, sd_ms, flops = eval_config(A, B, MB=MB, NB=NB, KB=KB, repeats=repeats, min_wall=min_wall)
        rows.append(dict(stage=3, MB=MB, NB=NB, KB=KB, avg_ms=avg_ms, sd_ms=sd_ms, gflops=flops))

    # Save CSV
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["stage","MB","NB","KB","avg_ms","sd_ms","gflops"])
        w.writeheader()
        w.writerows(rows)

    # Print top 10 overall
    top10 = sorted(rows, key=lambda r: r["gflops"], reverse=True)[:10]
    print("Top 10 configs:")
    for r in top10:
        print(f"stage{r['stage']} MB/NB/KB={r['MB']}/{r['NB']}/{r['KB']}  "
              f"{r['avg_ms']:.2f} ms  ~{r['gflops']:.2f} GFLOPs  (±{r['sd_ms']:.2f} ms)")
    return rows

if __name__ == "__main__":
    # Example: smaller sizes for quick dry-run; bump to 512/1024 for your real tests
    staged_sweep(m=256, n=256, k=256,
                 kb_list=(16,32,48,64,96,128),
                 coarse=(8,16,32,48,64),
                 step_refine=8,
                 repeats=3, min_wall=5,
                 csv_path="gemm_sweep_staged_256_2.csv")
