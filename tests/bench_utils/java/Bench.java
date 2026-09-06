import java.io.FileWriter;
import java.io.IOException;
import java.time.Instant;
import java.util.Arrays;

/**
 * Shared benchmark harness for all Java benchmarks. Mirrors tests/bench_utils.py:
 * reps x iters timing with warmup, median/IQR and mean/SD statistics, and the
 * schema-v2 JSON result format.
 */
public class Bench {

    public static class Result {
        public double[] elapsedMs;
        public double median, iqr, mean, sd;
        public int reps, iters;
    }

    // --- env helpers: the standard benchmark env contract ---

    private static int envInt(String name, int def) {
        String v = System.getenv(name);
        if (v == null || v.isEmpty()) return def;
        try {
            return Integer.parseInt(v);
        } catch (NumberFormatException e) {
            return def;
        }
    }

    public static int reps(int def) { return envInt("BENCH_REPS", def); }
    public static int iters(int def) { return envInt("BENCH_ITERS", def); }

    public static String impl() {
        String v = System.getenv("IMPL");
        return (v == null || v.isEmpty()) ? "seq" : v;
    }

    public static String model() {
        String v = System.getenv("MODEL");
        return (v == null || v.isEmpty()) ? "baseline" : v;
    }

    public static String out() {
        String v = System.getenv("BENCH_OUT");
        return v == null ? "" : v;
    }

    // --- statistics ---

    public static double median(double[] values) {
        double[] s = values.clone();
        Arrays.sort(s);
        int n = s.length;
        return (n % 2 == 0) ? (s[n / 2 - 1] + s[n / 2]) / 2.0 : s[n / 2];
    }

    /**
     * Interquartile range using the same definition as Python's
     * statistics.quantiles(data, n=4) (exclusive, interpolated), so the
     * dispersion figure is comparable across all six languages and matches
     * what bench/aggregate.py recomputes. The previous truncated nearest-rank
     * indexing disagreed with the Python harness on identical samples.
     */
    public static double iqr(double[] values) {
        double[] s = values.clone();
        Arrays.sort(s);
        int n = s.length;
        if (n < 2) return 0.0;
        final int nq = 4;
        int m = n + 1;
        double[] q = new double[3];
        for (int i = 1; i <= 3; i++) {
            int j = i * m / nq;
            if (j < 1) j = 1;
            if (j > n - 1) j = n - 1;
            double delta = (double) (i * m - j * nq);
            q[i - 1] = (s[j - 1] * (nq - delta) + s[j] * delta) / nq;
        }
        return q[2] - q[0];
    }

    public static double mean(double[] values) {
        double sum = 0;
        for (double v : values) sum += v;
        return sum / values.length;
    }

    public static double sd(double[] values) {
        if (values.length < 2) return 0;
        double m = mean(values);
        double sq = 0;
        for (double v : values) sq += (v - m) * (v - m);
        return Math.sqrt(sq / (values.length - 1));
    }

    /**
     * Runs warmup untimed calls, then reps timed blocks of iters calls each,
     * recording per-block mean time per call in milliseconds.
     */
    public static Result run(Runnable fn, int reps, int iters, int warmup) {
        for (int i = 0; i < warmup; i++) fn.run();

        double[] perRunMs = new double[reps];
        for (int r = 0; r < reps; r++) {
            long start = System.nanoTime();
            for (int k = 0; k < iters; k++) fn.run();
            long end = System.nanoTime();
            perRunMs[r] = (end - start) / 1_000_000.0 / iters;
        }

        Result res = new Result();
        res.elapsedMs = perRunMs;
        res.median = median(perRunMs);
        res.iqr = iqr(perRunMs);
        res.mean = mean(perRunMs);
        res.sd = sd(perRunMs);
        res.reps = reps;
        res.iters = iters;
        return res;
    }

    public static String format(String label, Result r) {
        return String.format("%s | mean %.2f ms/run ± %.2f SD | median %.2f ms/run ± %.2f IQR (n=%d)",
                label, r.mean, r.sd, r.median, r.iqr, r.reps);
    }

    /**
     * Writes the schema-v2 JSON result to path (no-op if null/empty).
     * paramsJson is a pre-rendered JSON object, e.g. "{\"graph_size\": 2000}".
     */
    public static void writeResult(String path, Result r, String algo, String impl, String paramsJson) {
        if (path == null || path.isEmpty()) return;
        if (paramsJson == null || paramsJson.isEmpty()) paramsJson = "{}";
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"schema_version\": 2,\n");
        sb.append("  \"algo\": \"").append(algo).append("\",\n");
        sb.append("  \"lang\": \"java\",\n");
        sb.append("  \"impl\": \"").append(impl).append("\",\n");
        sb.append("  \"model\": \"").append(model()).append("\",\n");
        sb.append("  \"elapsed_ms\": [");
        for (int i = 0; i < r.elapsedMs.length; i++) {
            if (i > 0) sb.append(", ");
            sb.append(r.elapsedMs[i]);
        }
        sb.append("],\n");
        sb.append("  \"mean\": ").append(r.mean).append(",\n");
        sb.append("  \"sd\": ").append(r.sd).append(",\n");
        sb.append("  \"median\": ").append(r.median).append(",\n");
        sb.append("  \"iqr\": ").append(r.iqr).append(",\n");
        sb.append("  \"reps\": ").append(r.reps).append(",\n");
        sb.append("  \"iters_per_rep\": ").append(r.iters).append(",\n");
        sb.append("  \"params\": ").append(paramsJson).append(",\n");
        sb.append("  \"timestamp\": \"").append(Instant.now().toString()).append("\"\n");
        sb.append("}\n");
        try (FileWriter fw = new FileWriter(path)) {
            fw.write(sb.toString());
        } catch (IOException ex) {
            System.err.println("Error writing result JSON: " + ex.getMessage());
        }
    }
}
