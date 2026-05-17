// GemmSweepBenchmark.java - Staged GEMM configuration sweep
// Equivalent to tests/go/test_go_pack.go

import java.io.*;
import java.util.*;

public class GemmSweepBenchmark {

    public static void main(String[] args) {
        // Quick dry-run; raise to 512/1024 for real tests.
        int m = 256, n = 256, k = 256;

        int[] kbList = {16, 32, 48, 64, 96, 128};
        int[] coarse = {8, 16, 32, 48, 64};
        int stepRefine = 8;

        int topKB = 2;
        int topMBNB = 5;
        int repeats = 3;
        double minWall = 5.0; // seconds
        String csvPath = "gemm_sweep_staged_256_java.csv";

        int seedA = 1;
        int seedB = 2;

        stagedSweep(m, n, k, kbList, coarse, stepRefine, topKB, topMBNB, repeats, minWall, csvPath, seedA, seedB);
    }

    private static double[][] makeRandomMatrix(int rows, int cols, int seed) {
        Random rng = new Random(seed);
        double[][] matrix = new double[rows][cols];
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                matrix[i][j] = rng.nextDouble() * 2.0 - 1.0; // [-1, 1]
            }
        }
        return matrix;
    }

    private static double[][] zeros(int rows, int cols) {
        return new double[rows][cols];
    }

    private static double timeAvgPerRun(Runnable fn, double minWallSeconds, int warmup) {
        for (int i = 0; i < warmup; i++) {
            fn.run();
        }

        long startNs = System.nanoTime();
        double total = 0.0;
        int runs = 0;

        while (total < minWallSeconds) {
            fn.run();
            runs++;
            total = (System.nanoTime() - startNs) / 1e9;
        }

        if (runs == 0) return 0.0;
        return total / runs;
    }

    private static double gflops(int m, int n, int k, double seconds) {
        if (seconds <= 0) return 0;
        return (2.0 * m * n * k) / (seconds * 1e9);
    }

    private static double mean(List<Double> xs) {
        if (xs.isEmpty()) return 0;
        double sum = 0;
        for (double x : xs) sum += x;
        return sum / xs.size();
    }

    private static double pstdev(List<Double> xs) {
        if (xs.isEmpty()) return 0;
        double m = mean(xs);
        double sum = 0;
        for (double x : xs) {
            double d = x - m;
            sum += d * d;
        }
        return Math.sqrt(sum / xs.size());
    }

    record Row(int stage, int MB, int NB, int KB, double avgMs, double sdMs, double gflops) {}

    private static Row evalConfig(double[][] A, double[][] B, int MB, int NB, int KB, int repeats, double minWall, int m, int n, int k, int stage) {
        List<Double> samples = new ArrayList<>(repeats);
        for (int i = 0; i < repeats; i++) {
            double avgSec = timeAvgPerRun(() -> {
                double[][] C = zeros(m, n);
                Gemm.run(A, B, 1.0, C, 0.0, MB, NB, KB);
            }, minWall, 1);
            samples.add(avgSec);
        }

        double avgSec = mean(samples);
        double sdSec = pstdev(samples);
        return new Row(stage, MB, NB, KB, avgSec * 1000.0, sdSec * 1000.0, gflops(m, n, k, avgSec));
    }

    private static int clamp(int v, int lo, int hi) {
        if (v < lo) return lo;
        if (v > hi) return hi;
        return v;
    }

    private static int floorToMultipleOf(int v, int step) {
        if (step <= 0) return v;
        return (v / step) * step;
    }

    private static List<Row> stagedSweep(
            int m, int n, int k,
            int[] kbList,
            int[] coarse,
            int stepRefine,
            int topKB,
            int topMBNB,
            int repeats,
            double minWall,
            String csvPath,
            int seedA, int seedB) {

        double[][] A = makeRandomMatrix(m, k, seedA);
        double[][] B = makeRandomMatrix(k, n, seedB);

        List<Row> rows = new ArrayList<>(1024);

        // ----- Stage 1: scan KB with MB=NB=32 -----
        System.out.println("Stage 1: Scanning KB values with MB=NB=32...");
        List<int[]> kbScores = new ArrayList<>(kbList.length); // [gflops*1000, KB]

        for (int KB : kbList) {
            Row r = evalConfig(A, B, 32, 32, KB, repeats, minWall, m, n, k, 1);
            rows.add(r);
            kbScores.add(new int[]{(int)(r.gflops * 1000), KB});
            System.out.printf("  KB=%d: %.2f ms, %.3f GFLOP/s%n", KB, r.avgMs, r.gflops);
        }

        kbScores.sort((a, b) -> Integer.compare(b[0], a[0]));
        if (topKB > kbScores.size()) topKB = kbScores.size();
        List<Integer> chosenKB = new ArrayList<>(topKB);
        for (int i = 0; i < topKB; i++) {
            chosenKB.add(kbScores.get(i)[1]);
        }
        System.out.println("Top KB values: " + chosenKB);

        // ----- Stage 2: coarse MB/NB for each chosen KB -----
        System.out.println("\nStage 2: Coarse MB/NB grid for top KB values...");
        Set<String> mbnbCandidates = new HashSet<>();

        for (int KB : chosenKB) {
            List<int[]> cands = new ArrayList<>(); // [gflops*1000, MB, NB]
            for (int MB : coarse) {
                for (int NB : coarse) {
                    Row r = evalConfig(A, B, MB, NB, KB, repeats, minWall, m, n, k, 2);
                    rows.add(r);
                    cands.add(new int[]{(int)(r.gflops * 1000), MB, NB});
                    System.out.printf("  MB=%d, NB=%d, KB=%d: %.2f ms, %.3f GFLOP/s%n", MB, NB, KB, r.avgMs, r.gflops);
                }
            }

            cands.sort((a, b) -> Integer.compare(b[0], a[0]));
            int limit = Math.min(topMBNB, cands.size());
            for (int i = 0; i < limit; i++) {
                mbnbCandidates.add(cands.get(i)[1] + "," + cands.get(i)[2] + "," + KB);
            }
        }

        // ----- Stage 3: local refinement around each (MB,NB,KB) -----
        System.out.println("\nStage 3: Local refinement...");
        Set<String> refined = new HashSet<>();

        for (String key : mbnbCandidates) {
            String[] parts = key.split(",");
            int MB = Integer.parseInt(parts[0]);
            int NB = Integer.parseInt(parts[1]);
            int KB = Integer.parseInt(parts[2]);

            for (int dmb : new int[]{-stepRefine, 0, stepRefine}) {
                for (int dnb : new int[]{-stepRefine, 0, stepRefine}) {
                    int mb2 = clamp(MB + dmb, 4, m);
                    int nb2 = clamp(NB + dnb, 4, n);
                    mb2 = floorToMultipleOf(mb2, 4);
                    nb2 = floorToMultipleOf(nb2, 4);
                    if (mb2 <= 0 || nb2 <= 0) continue;
                    refined.add(mb2 + "," + nb2 + "," + KB);
                }
            }
        }

        List<int[]> keys = new ArrayList<>();
        for (String key : refined) {
            String[] parts = key.split(",");
            keys.add(new int[]{Integer.parseInt(parts[0]), Integer.parseInt(parts[1]), Integer.parseInt(parts[2])});
        }
        keys.sort((a, b) -> {
            if (a[2] != b[2]) return Integer.compare(a[2], b[2]);
            if (a[0] != b[0]) return Integer.compare(a[0], b[0]);
            return Integer.compare(a[1], b[1]);
        });

        for (int[] key : keys) {
            int MB = key[0], NB = key[1], KB = key[2];
            Row r = evalConfig(A, B, MB, NB, KB, repeats, minWall, m, n, k, 3);
            rows.add(r);
            System.out.printf("  MB=%d, NB=%d, KB=%d: %.2f ms, %.3f GFLOP/s%n", MB, NB, KB, r.avgMs, r.gflops);
        }

        // ----- Save CSV -----
        if (csvPath != null && !csvPath.isEmpty()) {
            try (PrintWriter writer = new PrintWriter(new FileWriter(csvPath))) {
                writer.println("stage,MB,NB,KB,avg_ms,sd_ms,gflops");
                for (Row r : rows) {
                    writer.printf("%d,%d,%d,%d,%.6f,%.6f,%.6f%n",
                        r.stage, r.MB, r.NB, r.KB, r.avgMs, r.sdMs, r.gflops);
                }
                System.out.println("\nResults saved to " + csvPath);
            } catch (IOException e) {
                System.out.println("Failed to create CSV: " + e.getMessage());
            }
        }

        // ----- Top 10 overall -----
        List<Row> sorted = new ArrayList<>(rows);
        sorted.sort((a, b) -> Double.compare(b.gflops, a.gflops));

        int top = Math.min(10, sorted.size());
        System.out.println("\nTop 10 configs:");
        for (int i = 0; i < top; i++) {
            Row r = sorted.get(i);
            System.out.printf("stage%d MB/NB/KB=%d/%d/%d  %.2f ms  ~%.2f GFLOP/s  (±%.2f ms)%n",
                r.stage, r.MB, r.NB, r.KB, r.avgMs, r.gflops, r.sdMs);
        }

        return rows;
    }
}
