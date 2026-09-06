import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.List;

// Plain benchmark runner: correctness via the shared findAlignment entry
// (uniform across all impls) + large-file check + perf. The implementation
// under test is provided by the staged adapter class Impl
// (see bench/manifests/smith-waterman/java.json).
public class TestSmithWaterman {
    private static int passed = 0;
    private static int failed = 0;
    private static final double EPS = 1e-6;

    public static void main(String[] args) throws IOException {
        testCase("test_perfect_match", "ACGT", "ACGT", "ACGT", "ACGT", 8, 100.0);
        testCase("test_no_match", "AAAA", "TTTT", "", "", 0, 0.0);
        testCase("test_partial_match", "ACGTACGT", "TACGTGCA", "TACGT", "TACGT", 10, 100.0);
        testCase("test_gap_in_query", "ACGT", "ACAGT", "AC-GT", "ACAGT", 7, 80.0);
        testCase("test_gap_in_reference", "ACAGT", "ACGT", "ACAGT", "AC-GT", 7, 80.0);
        testCase("test_single_char_match", "A", "A", "A", "A", 2, 100.0);

        String[] input = readSWInput();
        if (input != null) {
            Impl impl = new Impl(2, -1, -1);
            Impl.Result r = impl.findAlignment(input[0], input[1]);
            int expScore = Integer.parseInt(input[2].trim());
            double expIdentity = Double.parseDouble(input[3].trim());
            boolean ok = r.a.length() == r.b.length() && r.score == expScore
                         && Math.abs(r.identity - expIdentity) <= EPS;
            report("test_large_sequences_from_file", ok);
        }

        System.out.printf("%d passed, %d failed%n", passed, failed);
        if (failed > 0) {
            System.out.println(failed + " test(s) failed — skipping benchmark");
            System.exit(1);
        }

        if (input == null) {
            System.out.println("SW_INPUT not set — skipping benchmark");
            return;
        }

        performanceSpeed(input[0], input[1]);
    }

    private static void testCase(String name, String query, String reference,
                                 String expA, String expB, int expScore, double expIdentity) {
        Impl impl = new Impl(2, -1, -1);
        Impl.Result r = impl.findAlignment(query, reference);
        boolean ok = r.a.equals(expA) && r.b.equals(expB) && r.score == expScore
                     && Math.abs(r.identity - expIdentity) <= EPS;
        if (!ok) {
            System.out.printf("  got: a=%s b=%s score=%d identity=%f%n", r.a, r.b, r.score, r.identity);
        }
        report(name, ok);
    }

    private static void report(String name, boolean ok) {
        System.out.println(name + (ok ? " passed" : " failed"));
        if (ok) passed++;
        else failed++;
    }

    private static String[] readSWInput() throws IOException {
        String path = System.getenv("SW_INPUT");
        if (path == null || path.isEmpty()) return null;
        if (!Files.exists(Paths.get(path))) return null;
        List<String> lines = Files.readAllLines(Paths.get(path));
        if (lines.size() < 4) return null;
        return new String[]{lines.get(0).trim(), lines.get(1).trim(), lines.get(2), lines.get(3)};
    }

    private static void performanceSpeed(String query, String reference) {
        Impl impl = new Impl(2, -1, -1);
        int reps = Bench.reps(5);
        int iters = Bench.iters(1);

        Bench.Result r = Bench.run(() -> impl.findAlignment(query, reference), reps, iters, 1);
        System.out.println(Bench.format("SW large sequences", r));

        String params = String.format("{\"query_len\": %d, \"reference_len\": %d}",
                                      query.length(), reference.length());
        Bench.writeResult(Bench.out(), r, "smith-waterman", Bench.impl(), params);
    }
}
