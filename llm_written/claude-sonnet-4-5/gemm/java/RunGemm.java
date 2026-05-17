import java.io.*;

public class RunGemm {
    public static void main(String[] args) throws IOException {
        System.out.println("=== GEMM Parallel Test Suite ===\n");
        
        // Run all tests
        TestGemm.main(new String[]{"all"});
    }
}
