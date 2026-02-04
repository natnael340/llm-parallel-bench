import java.util.*;

/**
 * Unified runner for BFS testing and performance evaluation.
 * 
 * Usage:
 *   java RunBfs test    - Run correctness and determinism tests
 *   java RunBfs perf    - Run performance benchmarks
 *   java RunBfs all     - Run both tests and benchmarks
 */
public class RunBfs {
    public static void main(String[] args) {
        if (args.length == 0) {
            System.out.println("Usage: java RunBfs [test|perf|all]");
            System.out.println("  test - Run correctness and determinism tests");
            System.out.println("  perf - Run performance benchmarks");
            System.out.println("  all  - Run both tests and benchmarks");
            System.exit(1);
        }
        
        String mode = args[0].toLowerCase();
        
        switch (mode) {
            case "test":
                runTests();
                break;
            case "perf":
                runPerformance();
                break;
            case "all":
                runTests();
                System.out.println("\n" + "=".repeat(50) + "\n");
                runPerformance();
                break;
            default:
                System.out.println("Unknown mode: " + mode);
                System.out.println("Use 'test', 'perf', or 'all'");
                System.exit(1);
        }
    }
    
    private static void runTests() {
        TestBfs.main(new String[0]);
    }
    
    private static void runPerformance() {
        PerfBfs.main(new String[0]);
    }
}
