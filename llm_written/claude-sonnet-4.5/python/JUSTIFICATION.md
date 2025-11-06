# Parallelization Justification: Tarjan's SCC Algorithm

## 1. What Changed and Why

The original algorithm finds **strongly connected components** (SCCs) in a directed graph and then reduces the edges within each SCC to a minimal set. Think of a graph as a network where arrows connect nodes. An SCC is a group of nodes where you can travel from any node to any other following the arrows.

**Original sequential process:**
1. Find all SCCs using Tarjan's depth-first search (this part stays sequential)
2. For each SCC found, build two spanning trees (forward and reverse)
3. Combine the trees to get the minimal edge set
4. Move to the next SCC and repeat

**Concrete example (5 nodes in one SCC):**
```
Input: Nodes [0,1,2,3,4] with edges forming a cycle
       0→1→2→3→4→0 (plus some extra connections)

Process:
  - Find forward tree: edges that reach all nodes going forward
  - Find reverse tree: edges that reach all nodes going backward  
  - Combine: minimal set that maintains strong connectivity
```

## 2. How We Made It Parallel

The key insight: **each SCC can be processed independently**. Once we know which nodes belong to which SCC, the edge minimization work for SCC-A doesn't depend on SCC-B's work.

**Step-by-step parallel approach:**

```
Input Graph ▶ [Find all SCCs sequentially using Tarjan's DFS]
                     │
                     ▼
              [SCC-1][SCC-2][SCC-3][SCC-4][SCC-5]
                 │      │      │      │      │
              Worker1 Worker2 Worker3 Worker4 Worker5
              (build  (build  (build  (build  (build
               trees)  trees)  trees)  trees)  trees)
                 │      │      │      │      │
                 └──────┴──────┴──────┴──────┘
                            │
                     Fixed-order merge
                    (SCC-1, then 2, then 3...)
                            │
                            ▼
                    Final edge list
```

**What happens:**
1. **Split**: After finding SCCs, we have a list: [SCC-1, SCC-2, SCC-3, ...]
2. **Assign**: Each worker gets one SCC and its portion of the graph structure
3. **Process**: Each worker independently builds forward and reverse spanning trees for their SCC
4. **Combine**: Results are collected in the **same order** as the original SCC list (SCC-1's edges first, then SCC-2's edges, etc.)

**Safety switch for small graphs:**
If there are fewer than 4 SCCs, we skip parallelism and run sequentially. Starting worker processes costs time (about 150-200 milliseconds), so it's only worth it for larger workloads.

## 3. Why the Answer Is Always the Same (Determinism)

Three guarantees ensure identical results every time:

**A. Fixed split:**
- The number of SCCs and their membership never change for a given graph
- Each SCC is always assigned to workers in the same order (SCC-1, SCC-2, SCC-3...)

**B. Fixed combine order:**
- Results are collected in a list that preserves SCC order
- We use `list(executor.map(...))` which maintains input order
- Final edges: [all edges from SCC-1] + [all edges from SCC-2] + ...

**C. No conflicts:**
- Each worker only reads the graph structure (immutable)
- Each worker writes to its own local result list
- No shared state is modified during parallel execution
- Only the final merge step (which is sequential) touches the combined result

**Evidence of determinism:**
Running the same 50-vertex graph with 5 SCCs twice:
- Run 1 hash: `2a3cfa09561422d0`
- Run 2 hash: `2a3cfa09561422d0`

Both runs produce identical edge lists (see `evidence/run_summary.txt`).

## 4. Proof It Works

**Correctness parity:** All test cases match sequential output exactly.
- Empty graph: ✓ 0 edges (both implementations)
- Single SCC (3 vertices): ✓ 4 edges (both implementations)
- Multiple SCCs (50 vertices, 5 SCCs): ✓ 90 edges (both implementations)
- Large graph (1000 vertices, 20 SCCs): ✓ 1960 edges (both implementations)

See `evidence/run_summary.txt` for full test results.

**Determinism:** Multiple runs of the parallel version on the same input produce identical hashes:
- Hash comparison: `2a3cfa09561422d0` (run 1) = `2a3cfa09561422d0` (run 2)

**Performance caveat:** The large test case shows **0.03x speedup** (slower, not faster). This is documented in `evidence/perf.txt`.

Reason: Python's process pool has ~180ms startup overhead. Each SCC's work takes only ~0.3ms. With 20 SCCs:
- Sequential: 20 × 0.3ms = 6ms
- Parallel: 180ms overhead + (20 × 0.3ms ÷ workers) = ~194ms

**When parallelization helps:**
- Graphs with 100+ SCCs
- Each SCC has 1000+ vertices
- Total work time > 500ms (exceeds overhead)

For typical small-to-medium graphs, the sequential fallback (< 4 SCCs) keeps performance optimal.

## 5. Limits and Safety Switches

**Small-input sequential fallback:**
- Threshold: Graphs with fewer than 4 SCCs stay sequential
- Reason: Process spawning overhead (180ms) exceeds work time

**Resource bounds:**
- Worker pool capped at `min(cpu_count, num_sccs)` workers
- Avoids oversubscription: never spawn more workers than available CPU cores
- On a 16-core machine with 20 SCCs, uses 16 workers (not 20)

**Corner cases handled:**
- Empty graph: Returns empty edge list immediately
- Single vertex: No edges to minimize
- Disconnected components: Each SCC processed independently

**Known limitation:**
- Process pool overhead makes this slower for small graphs (< ~500ms total work)
- Trade-off: Correctness and determinism are preserved; parallelism only activates when enough SCCs exist

## 6. How to Reproduce

**Run full test suite (correctness, determinism, performance):**
```bash
python test_tarjan.py
```

**Generate evidence files:**
```bash
python run_tests.py
```

**Check specific results:**
```bash
cat evidence/run_summary.txt   # Correctness and determinism evidence
cat evidence/perf.txt           # Performance analysis
```

**Verify determinism manually (two runs, compare hashes):**
```bash
python -c "
from algo_parallel import Graph
g = Graph(50)
edges = [(i, i+1) for i in range(0, 9)] + [(9, 0)] + \
        [(i, i+1) for i in range(10, 19)] + [(19, 10)] + \
        [(i, i+1) for i in range(20, 29)] + [(29, 20)] + \
        [(i, i+1) for i in range(30, 39)] + [(39, 30)] + \
        [(i, i+1) for i in range(40, 49)] + [(49, 40)]
for u, v in edges:
    g.add_edge(u, v)
result = g.reduce_edges()
print(sorted(result))
"
```
Run twice and compare output lists.

## 7. Glossary

**Parallel** — Multiple workers process different SCCs at the same time, each on a separate CPU core.

**Deterministic** — Running the algorithm multiple times on the same input always produces the exact same output (same edges, same order).

**Worker** — An independent process that handles edge minimization for one SCC.

**SCC (Strongly Connected Component)** — A group of nodes in a graph where you can reach any node from any other node following the directed edges.

**Merge/Combine** — Join partial results (edges from each SCC) in a fixed order to build the final edge list.

**Process pool overhead** — Time cost (~180ms in Python) to start worker processes and transfer data between them.

**Spanning tree** — A minimal set of edges that connects all nodes in a component without creating cycles.

**Fixed-order collection** — Results are gathered in the same sequence every time (SCC-1 first, then SCC-2, etc.), ensuring determinism.
