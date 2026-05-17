#include <iostream>
#include <vector>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include "nlohmann/json.hpp"

//#include "./seq/graph.cpp"
#include "./par/graph.cpp"

using namespace std;
using json = nlohmann::json;


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

    const int reps = 5;
    const int iters = 20;

    // warmup
    g.ReduceEdges();

    vector<double> perRepeatMs;
    perRepeatMs.reserve(reps);

    for (int r = 0; r < reps; ++r) {
        auto start = chrono::high_resolution_clock::now();
        for (int i = 0; i < iters; ++i) {
            g.ReduceEdges();
        }
        auto end = chrono::high_resolution_clock::now();
        chrono::duration<double, milli> diff = end - start;
        perRepeatMs.push_back(diff.count() / iters);
    }

    double sum = 0.0;
    for (double t : perRepeatMs) sum += t;
    double mean = sum / reps;

    double sq_sum = 0.0;
    for (double t : perRepeatMs) sq_sum += (t - mean) * (t - mean);
    double stddev = sqrt(sq_sum / reps);

    json result = {
        {"elapsed_ms", perRepeatMs},
        {"mean", mean},
        {"sd", stddev},
        {"iterations", reps}
    };

    ofstream out(filename);
    if (!out) {
        cerr << "Error opening file: " << filename << "\n";
        return;
    }

    out << result.dump(2);
    out.close();

    cout << "SCC ReduceEdges | graph_size=" << graphSize
         << " | " << mean << " ms/run ± " << stddev << " (n=" << reps << ")\n";
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