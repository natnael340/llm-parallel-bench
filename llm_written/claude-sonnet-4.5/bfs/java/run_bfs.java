import java.util.*;

/**
 * Unified runner for BFS testing and performance evaluation.
 * 
 * Usage:
 *   java TestBfs    - Run correctness and determinism tests
 *   java PerfBfs    - Run performance benchmarks
 */
public class RunBfs {
    public static void main(String[] args) {
        if (args.length == 0) {
            System.out.println("BFS Parallel Implementation Runner");
            System.out.println("===================================");
            System.out.println();
            System.out.println("To run tests:");
            System.out.println("  java TestBfs");
            System.out.println();
            System.out.println("To run performance benchmarks:");
            System.out.println("  java PerfBfs");
            System.out.println();
            System.out.println("To compile all files:");
            System.out.println("  javac Graph.java BfsSequential.java BfsParallel.java TestBfs.java PerfBfs.java");
            return;
        }
    }
}
