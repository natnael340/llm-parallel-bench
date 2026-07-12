import json, statistics, glob, os

RES = os.path.dirname(os.path.abspath(__file__))

def load(name):
    with open(os.path.join(RES, name)) as f:
        d = json.load(f)
    e = d["elapsed_ms"]
    return {
        "mean": statistics.mean(e),
        "stdev": statistics.stdev(e) if len(e) > 1 else 0.0,
        "median": statistics.median(e),
        "n": len(e),
    }

seq = load("temp.json")
threads = [1, 2, 4, 8, 16]
par = {t: load(f"temp_par_{t}.json") for t in threads}

p1 = par[1]["mean"]

print(f"{'Threads':>7} {'Mean(ms)':>10} {'SD':>7} {'vs par@1':>9}")
print("-" * 38)
for t in threads:
    m = par[t]["mean"]
    print(f"{t:>7} {m:>10.2f} {par[t]['stdev']:>7.2f} {p1/m:>8.2f}x")
print("-" * 38)
print(f"Sequential baseline mean : {seq['mean']:.2f} ms  (SD {seq['stdev']:.2f})")
print(f"seq / par@1              : {seq['mean']/p1:.2f}x   <- single-thread gap (data structure)")
print(f"par@1 / par@16           : {p1/par[16]['mean']:.2f}x   <- parallelism")
print(f"seq / par@16             : {seq['mean']/par[16]['mean']:.2f}x   <- combined")
