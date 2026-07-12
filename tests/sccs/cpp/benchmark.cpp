#include <iostream>
#include <cstdlib>

//#include "./seq/graph.cpp"
#include "./par/graph.cpp"

#include "../../bench_utils/cpp/bench_utils.hpp"

using namespace std;


void ringSCC(int start, int end, Graph& g) {
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


Graph buildGraph(int graphSize, int clusterSize, int noClusterInGroup) {
    Graph g(graphSize);

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

// Benchmark runner
void benchmarkReduceEdges(const string& filename) {
    int graphSize = 100000;
    int clusterSize = 300;
    int noClusterInGroup = 3;
    Graph g = buildGraph(graphSize, clusterSize, noClusterInGroup);

    const int reps = 5, iters = 20;
    auto bm = run_benchmark([&]() { g.ReduceEdges(); }, reps, iters, 1);

    const char* impl_env = std::getenv("IMPL");
    string impl = impl_env ? impl_env : "par";

    string label = "SCC ReduceEdges | graph_size=" + to_string(graphSize);
    cout << format_result(label, bm) << "\n";
    write_result(bm, filename, "sccs", "cpp", impl, iters);
}


unordered_map<string, string> parseFlags(int argc, char* argv[]) {
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

    if (flags.count("out") == 0) {
        cerr << "Error: Output file not specified. Use --out <filename>\n";
        return 1;
    }

    string filename = flags["out"];

    benchmarkReduceEdges(filename);
    return 0;
}