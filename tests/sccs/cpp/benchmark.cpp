#include <cstdlib>
#include <iostream>
#include <random>
#include <set>
#include <string>
#include <utility>
#include <vector>

#include "impl.hpp"          // staged adapter: BenchGraph + bench_reduce_edges(BenchGraph&)
#include "bench_utils.hpp"

using namespace std;

// --- correctness: SCC strong-check heuristic (mirrors the Go harness) ---
// For SCC of size k>1: (k-1) <= internal edges <= 2*(k-1), and every SCC
// node appears in at least one kept internal edge.
static bool isSccStrong(const vector<int>& sccNodes, const vector<pair<int,int>>& edges) {
    set<int> nodeSet(sccNodes.begin(), sccNodes.end());
    int k = (int)sccNodes.size();
    if (k <= 1) return true;

    int internalEdges = 0;
    set<int> touched;
    for (auto& e : edges) {
        if (nodeSet.count(e.first) && nodeSet.count(e.second)) {
            internalEdges++;
            touched.insert(e.first);
            touched.insert(e.second);
        }
    }
    if (internalEdges < k - 1) return false;
    if (internalEdges > 2 * (k - 1)) return false;
    if ((int)touched.size() < k) return false;
    return true;
}

static bool checkAllSCCs(BenchGraph& g) {
    auto edges = bench_reduce_edges(g);
    for (auto& scc : g.FindSCCs()) {
        if (!isSccStrong(scc, edges)) return false;
    }
    return true;
}

// Random multi-SCC graph; ReduceEdges must return byte-identical output across runs.
static bool checkDeterminism() {
    const int numScc = 24, sccSize = 40, runs = 5;
    unsigned seed = random_device{}();
    mt19937 rng(seed);
    uniform_int_distribution<int> pick(0, sccSize - 1);

    BenchGraph g(numScc * sccSize);
    for (int s = 0; s < numScc; s++) {
        int start = s * sccSize;
        for (int u = start; u < start + sccSize; u++) g.AddEdge(u, start + (u - start + 1) % sccSize);
        for (int i = 0; i < sccSize * 3; i++) {
            int u = start + pick(rng), v = start + pick(rng);
            if (u != v) g.AddEdge(u, v);
        }
    }
    for (int s = 0; s < numScc - 1; s++) {
        for (int i = 0; i < 6; i++) g.AddEdge(s * sccSize + pick(rng), (s + 1) * sccSize + pick(rng));
    }

    auto sccs = g.FindSCCs();
    vector<pair<int,int>> first;
    for (int r = 0; r < runs; r++) {
        auto edges = bench_reduce_edges(g);
        for (auto& scc : sccs) {
            if (!isSccStrong(scc, edges)) {
                cout << "determinism run " << r << ": reduced edges broke SCC (seed=" << seed << ")" << endl;
                return false;
            }
        }
        if (r == 0) {
            first = edges;
        } else if (edges != first) {
            cout << "determinism run " << r << ": output differs from run 0 (seed=" << seed << ")" << endl;
            return false;
        }
    }
    return true;
}

static int runCorrectnessChecks() {
    int failures = 0;
    auto expect = [&](bool ok, const string& name) {
        cout << name << (ok ? " passed" : " failed") << endl;
        if (!ok) failures++;
    };

    {   // simple 3-cycle
        BenchGraph g(3);
        g.AddEdge(0, 1); g.AddEdge(1, 2); g.AddEdge(2, 0);
        expect(checkAllSCCs(g), "test_scc_3cycle");
    }
    {   // two-node mutual SCC
        BenchGraph g(2);
        g.AddEdge(0, 1); g.AddEdge(1, 0);
        expect(checkAllSCCs(g), "test_scc_2node_mutual");
    }
    {   // multiple SCCs with a cross edge
        BenchGraph g(5);
        g.AddEdge(0, 1); g.AddEdge(1, 2); g.AddEdge(2, 0);
        g.AddEdge(3, 4); g.AddEdge(4, 3);
        g.AddEdge(2, 3);
        expect(checkAllSCCs(g), "test_scc_multiple");
    }
    {   // 7-node example graph
        BenchGraph g(7);
        g.AddEdge(0, 1); g.AddEdge(1, 2); g.AddEdge(1, 3); g.AddEdge(1, 4);
        g.AddEdge(2, 0); g.AddEdge(2, 3); g.AddEdge(3, 5); g.AddEdge(5, 3);
        g.AddEdge(5, 4); g.AddEdge(5, 6); g.AddEdge(6, 4); g.AddEdge(4, 6);
        expect(checkAllSCCs(g), "test_scc_7node");
    }
    expect(checkDeterminism(), "test_scc_determinism");
    return failures;
}

// --- benchmark graph construction (shared with all languages) ---

static void ringSCC(int start, int end, BenchGraph& g) {
    for (int i = start; i < end; i++) {
        int v = (i + 1) % end;
        if (v == 0) {
            v = start;
        }
        if (i == v) {
            continue;
        }
        g.AddEdge(i, v);
    }
}

static BenchGraph buildGraph(int graphSize, int clusterSize, int noClusterInGroup) {
    BenchGraph g(graphSize);

    srand(43);

    for (int i = 0; i < graphSize; i += clusterSize) {
        // Create a ring SCC
        ringSCC(i, min(i + clusterSize, graphSize), g);

        int currentCluster = (i / clusterSize);
        if (currentCluster / noClusterInGroup == (currentCluster + 1) / noClusterInGroup) {
            if ((i + clusterSize) < graphSize) {
                int endA = min(i + clusterSize, graphSize);
                int endB = min(i + 2 * clusterSize, graphSize);

                int u = i + (rand() % (endA - i));
                int v = endA + (rand() % (endB - endA));
                g.AddEdge(u, v);
            }
        }
    }

    return g;
}

static void benchmarkReduceEdges(const string& filename) {
    int graphSize = 100000;
    int clusterSize = 300;
    int noClusterInGroup = 3;
    BenchGraph g = buildGraph(graphSize, clusterSize, noClusterInGroup);

    if (!bench_digest_out().empty()) {
        auto edges = bench_reduce_edges(g);
        ostringstream out;
        for (const auto& scc : g.FindSCCs()) {
            out << "S";
            for (int v : scc) out << " " << v;
            out << "\n";
        }
        for (const auto& e : edges) out << "E " << e.first << " " << e.second << "\n";
        write_digest(out.str());
        return;
    }

    int reps = bench_reps(5), iters = bench_iters(20);
    auto bm = run_benchmark([&]() { bench_reduce_edges(g); }, reps, iters, 1);

    string label = "SCC ReduceEdges | graph_size=" + to_string(graphSize);
    cout << format_result(label, bm) << "\n";

    string params = "{\"graph_size\": " + to_string(graphSize)
        + ", \"cluster_size\": " + to_string(clusterSize)
        + ", \"no_cluster_in_group\": " + to_string(noClusterInGroup) + "}";
    write_result(bm, filename, "sccs", "cpp", bench_impl(), iters, params);
}

static unordered_map<string, string> parseFlags(int argc, char* argv[]) {
    unordered_map<string, string> flags;
    for (int i = 1; i < argc - 1; ++i) {
        string key = argv[i];
        if (key.rfind("--", 0) == 0) { // starts with --
            flags[key.substr(2)] = argv[i + 1];
            ++i;
        }
    }
    return flags;
}

int main(int argc, char* argv[]) {
    auto flags = parseFlags(argc, argv);

    // Output path: --out flag, else BENCH_OUT env (may be empty: print only).
    string filename = flags.count("out") ? flags["out"] : bench_out();

    int failures = runCorrectnessChecks();
    if (failures > 0) {
        cout << failures << " correctness check(s) failed — skipping benchmark" << endl;
        return 1;
    }

    benchmarkReduceEdges(filename);
    return 0;
}
