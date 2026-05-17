import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Random;

public class run_smithwaterman {
    static String hex(byte[] b){
        StringBuilder sb = new StringBuilder();
        for(byte x: b) sb.append(String.format("%02x", x));
        return sb.toString();
    }

    static byte[] sha256(String s){
        try{
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            return md.digest(s.getBytes("UTF-8"));
        }catch(Exception e){ throw new RuntimeException(e); }
    }

    static String matrixToString(int[][] H){
        StringBuilder sb = new StringBuilder();
        for(int i=0;i<H.length;i++){
            sb.append(Arrays.toString(H[i])).append('\n');
        }
        return sb.toString();
    }

    static void assertEqualMatrices(int[][] A, int[][] B, String label){
        if(A.length != B.length) throw new AssertionError(label+": row mismatch");
        for(int i=0;i<A.length;i++){
            if(A[i].length != B[i].length) throw new AssertionError(label+": col mismatch at "+i);
            for(int j=0;j<A[i].length;j++){
                if(A[i][j] != B[i][j]){
                    throw new AssertionError(label+": value mismatch at ("+i+","+j+") " + A[i][j] + " != " + B[i][j]);
                }
            }
        }
    }

    static class ResultSummary{
        boolean ok=true;
        StringBuilder log = new StringBuilder();
        void add(String s){ log.append(s).append('\n'); }
    }

    public static void main(String[] args) throws Exception {
        ResultSummary summary = new ResultSummary();

        SmithWatermanSeq seq = new SmithWatermanSeq(2, -1, -1);
        AlgoParallel par = new AlgoParallel(2, -1, -1);

        String[][] cases = new String[][]{
            {"", ""}, // empty
            {"A", ""},
            {"", "G"},
            {"GATTACA", "GCATGCU"}, // standard example
            {"AAAAAA", "AAA"},
            {"ACGTACGTACGT", "ACGTACGT"}
        };

        int pass=0, fail=0;

        for(int idx=0; idx<cases.length; idx++){
            String q = cases[idx][0];
            String r = cases[idx][1];

            int[][] Hs = seq.constructMatrix(q,r);
            int[][] Hp = par.constructMatrix(q,r);

            try{ assertEqualMatrices(Hs, Hp, "case"+idx); summary.add("case"+idx+" matrix parity: OK"); pass++; }
            catch(Throwable t){ summary.add("case"+idx+" matrix parity: FAIL -> "+t.getMessage()); fail++; }

            SmithWatermanSeq.AlignmentResult rs = seq.traceback(Hs,q,r);
            AlgoParallel.AlignmentResult rp1 = par.traceback(Hp,q,r);
            AlgoParallel.AlignmentResult rp2 = par.traceback(Hp,q,r);

            String seqStr = rs.alignedA+"|"+rs.alignedB+"|"+rs.score+"|"+rs.identity;
            String parStr1 = rp1.alignedA+"|"+rp1.alignedB+"|"+rp1.score+"|"+rp1.identity;
            String parStr2 = rp2.alignedA+"|"+rp2.alignedB+"|"+rp2.score+"|"+rp2.identity;

            if(!seqStr.equals(parStr1)) { summary.add("case"+idx+" traceback parity: FAIL"); fail++; }
            else { summary.add("case"+idx+" traceback parity: OK"); pass++; }

            String h1 = hex(sha256(parStr1));
            String h2 = hex(sha256(parStr2));
            if(!h1.equals(h2)) { summary.add("case"+idx+" determinism: FAIL "+h1+" vs "+h2); fail++; }
            else { summary.add("case"+idx+" determinism: OK hash="+h1); pass++; }
        }

        boolean doPerf = args.length >= 3 && args[0].equals("--perf");
        String perfReport = "SKIPPED: set --perf N M for performance check";
        if(doPerf){
            int N = Integer.parseInt(args[1]);
            int M = Integer.parseInt(args[2]);
            Random rnd = new Random(42);
            String alphabet = "ACGT";
            StringBuilder qb = new StringBuilder();
            StringBuilder rb = new StringBuilder();
            for(int i=0;i<N;i++) qb.append(alphabet.charAt(rnd.nextInt(alphabet.length())));
            for(int j=0;j<M;j++) rb.append(alphabet.charAt(rnd.nextInt(alphabet.length())));
            String q = qb.toString(), r = rb.toString();

            long t0 = System.nanoTime();
            int[][] Hs = seq.constructMatrix(q,r);
            long t1 = System.nanoTime();
            int[][] Hp = par.constructMatrix(q,r);
            long t2 = System.nanoTime();

            assertEqualMatrices(Hs, Hp, "large-matrix");
            SmithWatermanSeq.AlignmentResult rs = seq.traceback(Hs,q,r);
            AlgoParallel.AlignmentResult rp1 = par.traceback(Hp,q,r);
            if(!(rs.alignedA.equals(rp1.alignedA) && rs.alignedB.equals(rp1.alignedB) && rs.score==rp1.score)){
                throw new AssertionError("large traceback mismatch");
            }

            double tSeq = (t1 - t0)/1e9;
            double tPar = (t2 - t1)/1e9;
            double speedup = tSeq / tPar;
            int cores = Math.max(1, Runtime.getRuntime().availableProcessors());
            perfReport = String.format("N=%d M=%d cores=%d t_seq=%.3fs t_par=%.3fs speedup=%.2fx", N, M, cores, tSeq, tPar, speedup);
            System.out.println(perfReport);
        }

        java.nio.file.Files.createDirectories(java.nio.file.Paths.get("evidence"));
        java.nio.file.Files.write(java.nio.file.Paths.get("evidence/run_summary.txt"), summary.log.toString().getBytes("UTF-8"));
        java.nio.file.Files.write(java.nio.file.Paths.get("evidence/perf.txt"), perfReport.getBytes("UTF-8"));

        if(fail>0) {
            System.err.println("FAILURES: "+fail+" (passes: "+pass+")");
            System.exit(1);
        } else {
            System.out.println("All tests passed. ("+pass+" checks)");
        }
    }
}
