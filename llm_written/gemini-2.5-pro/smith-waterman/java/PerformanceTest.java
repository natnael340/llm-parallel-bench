import java.util.concurrent.TimeUnit;

public class PerformanceTest {

    private static final int MATCH_SCORE = 2;
    private static final int MISMATCH_SCORE = -1;
    private static final int GAP_SCORE = -1;
    private static final int STRING_LENGTH = 1500; // Increased size for more meaningful perf test

    public static void main(String[] args) {
        System.out.println("Running Performance Test...");

        String query = generateRandomString(STRING_LENGTH);
        String reference = generateRandomString(STRING_LENGTH);

        // Sequential Run
        SmithWaterman sw = new SmithWaterman(MATCH_SCORE, MISMATCH_SCORE, GAP_SCORE);
        long startTimeSeq = System.nanoTime();
        sw.findAlignment(query, reference);
        long endTimeSeq = System.nanoTime();
        long durationSeq = TimeUnit.NANOSECONDS.toMillis(endTimeSeq - startTimeSeq);
        System.out.println("Sequential Time: " + durationSeq + " ms");

        // Parallel Run
        SmithWatermanParallel swParallel = new SmithWatermanParallel(MATCH_SCORE, MISMATCH_SCORE, GAP_SCORE);
        long startTimePar = System.nanoTime();
        swParallel.findAlignment(query, reference);
        long endTimePar = System.nanoTime();
        long durationPar = TimeUnit.NANOSECONDS.toMillis(endTimePar - startTimePar);
        swParallel.shutdown();
        System.out.println("Parallel Time: " + durationPar + " ms");

        // Performance Comparison
        if (durationPar > 0) {
            double speedup = (double) durationSeq / durationPar;
            System.out.printf("Speedup: %.2fx%n", speedup);
        } else {
            System.out.println("Parallel execution was too fast to measure speedup.");
        }
        
        // Write evidence to file
        String evidence = String.format("N=%d, t_seq=%dms, t_par=%dms, speedup=%.2fx, cores=%d",
            STRING_LENGTH,
            durationSeq,
            durationPar,
            (durationPar > 0) ? (double) durationSeq / durationPar : 0.0,
            Runtime.getRuntime().availableProcessors()
        );

        try {
            java.nio.file.Files.createDirectories(java.nio.file.Paths.get("evidence"));
            java.nio.file.Files.write(java.nio.file.Paths.get("evidence/perf.txt"), evidence.getBytes());
        } catch (java.io.IOException e) {
            System.err.println("Failed to write performance evidence file.");
            e.printStackTrace();
        }
    }

    private static String generateRandomString(int length) {
        String chars = "ACGT";
        StringBuilder sb = new StringBuilder(length);
        java.util.Random random = new java.util.Random();
        for (int i = 0; i < length; i++) {
            sb.append(chars.charAt(random.nextInt(chars.length())));
        }
        return sb.toString();
    }
}
