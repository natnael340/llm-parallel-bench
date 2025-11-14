#include <iostream>
#include <vector>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include "nlohmann/json.hpp"

// #include "graph.cpp"
#include "../../llm_written/gpt-5/cpp/algo_parallel.cpp"

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
void benchmarkReduceEdges(int iterations, int warmups, const string& filename) {
    int graphSize = 100000;
    int clusterSize = 300;
    int noClusterInGroup = 3;
    Graph g = buildGraph(graphSize, clusterSize, noClusterInGroup);

    vector<double> batchTimes;
    batchTimes.reserve(iterations);

    // warmups
    for (int w = 0; w < warmups; ++w) {
        g.ReduceEdgesParallel();
    }

    double total_elapsed_ms = 0.0;
    // timed runs
    for (int i = 0; i < iterations; ++i) {
        auto start = chrono::high_resolution_clock::now();
        
        g.ReduceEdgesParallel();

        auto end = chrono::high_resolution_clock::now();
        chrono::duration<double, milli> diff = end - start;
        batchTimes.push_back(diff.count());
        total_elapsed_ms += diff.count();
    }

    double mean = total_elapsed_ms / iterations;

    double sq_sum = 0;

    for (double t : batchTimes) sq_sum += (t - mean) * (t - mean);
    double stddev = sqrt(sq_sum / iterations);


    json result = {
        {"elapsed_ms", batchTimes},
        {"mean", mean},
        {"sd", stddev},
        {"iterations", iterations}
    };


    // Write results to file
    ofstream out(filename);
    if (!out) {
        cerr << "Error opening file: " << filename << "\n";
        return;
    }

    out << result.dump(2);
    out.close();

    // fmt.Printf("Mean: %.2f ms ± %.2f ms\n", mean, stddev)
    cout << "Mean: " << mean << " ms ± " << stddev << " ms\n";
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

    int iterations = flags.count("iterations") ? stoi(flags["iterations"]) : 100;
    int warmup = flags.count("warmup") ? stoi(flags["warmup"]) : 5;

    if (flags.count("out") == 0){
        cerr << "Error: Output file not specified. Use --out <filename>\n";
        return 1;
    }

    string filename = flags["out"];

    benchmarkReduceEdges(iterations, warmup, filename);
    return 0;
}