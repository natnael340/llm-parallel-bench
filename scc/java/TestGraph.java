import java.util.*;

public class TestGraph {

    private static boolean equalNested(List<List<Integer>> a, List<List<Integer>> b) {
        if (a.size() != b.size()) return false;
        for (int i = 0; i < a.size(); i++) {
            if (!a.get(i).equals(b.get(i))) return false;
        }
        return true;
    }

    private static void sortEdges(List<int[]> edges) {
        edges.sort((l, r) -> {
            if (l[0] != r[0]) return Integer.compare(l[0], r[0]);
            return Integer.compare(l[1], r[1]);
        });
    }

    private static void expectSameMultiset(List<int[]> a, List<int[]> b, String testName) {
        sortEdges(a);
        sortEdges(b);

        boolean equal = a.size() == b.size();
        if (equal) {
            for (int i = 0; i < a.size(); i++) {
                if (a.get(i)[0] != b.get(i)[0] || a.get(i)[1] != b.get(i)[1]) {
                    equal = false;
                    break;
                }
            }
        }

        if (!equal) {
            System.err.println("\n--- Multiset mismatch in " + testName + " ---");
            System.err.println("left (got)  size=" + a.size());
            for (int i = 0; i < Math.min(a.size(), 20); i++) {
                System.err.println("  " + a.get(i)[0] + "," + a.get(i)[1]);
            }
            if (a.size() > 20) System.err.println("  ...(" + (a.size() - 20) + " more)");

            System.err.println("right (exp) size=" + b.size());
            for (int i = 0; i < Math.min(b.size(), 20); i++) {
                System.err.println("  " + b.get(i)[0] + "," + b.get(i)[1]);
            }
            if (b.size() > 20) System.err.println("  ...(" + (b.size() - 20) + " more)");

            if (a.size() == b.size()) {
                for (int i = 0; i < a.size(); i++) {
                    if (a.get(i)[0] != b.get(i)[0] || a.get(i)[1] != b.get(i)[1]) {
                        System.err.println("first diff at idx " + i +
                                " got=(" + a.get(i)[0] + "," + a.get(i)[1] + ")" +
                                " exp=(" + b.get(i)[0] + "," + b.get(i)[1] + ")");
                        break;
                    }
                }
            }
            System.err.println("-------------------------");
            throw new AssertionError("multiset equality failed in " + testName);
        }
    }

    private static List<int[]> toEdgeList(int[][] edges) {
        List<int[]> list = new ArrayList<>();
        for (int[] e : edges) {
            list.add(e);
        }
        return list;
    }

    private static void testEmptyGraph() {
        Graph g = new Graph(0);
        assert g.findSCCs().isEmpty() : "testEmptyGraph: SCCs should be empty";
        assert g.reduceEdges().isEmpty() : "testEmptyGraph: reduced should be empty";
    }

    private static void testSingletonNoEdges() {
        Graph g = new Graph(1);
        List<List<Integer>> expected = new ArrayList<>();
        expected.add(Arrays.asList(0));
        assert equalNested(g.findSCCs(), expected) : "testSingletonNoEdges: SCC mismatch";
        assert g.reduceEdges().isEmpty() : "testSingletonNoEdges: reduced should be empty";
    }

    private static void testSingletonSelfLoop() {
        Graph g = new Graph(1);
        g.addEdge(0, 0);
        List<List<Integer>> expected = new ArrayList<>();
        expected.add(Arrays.asList(0));
        assert equalNested(g.findSCCs(), expected) : "testSingletonSelfLoop: SCC mismatch";
        assert g.reduceEdges().isEmpty() : "testSingletonSelfLoop: reduced should be empty";
    }

    private static void testSimpleCycle3() {
        Graph g = new Graph(3);
        g.addEdge(0, 1);
        g.addEdge(1, 2);
        g.addEdge(2, 0);
        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(Arrays.asList(2, 1, 0));
        assert equalNested(g.findSCCs(), expectedSccs) : "testSimpleCycle3: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{{2, 0}, {0, 1}, {2, 1}, {1, 0}});
        expectSameMultiset(g.reduceEdges(), expected, "testSimpleCycle3");
    }

    private static void testTwoNodeMutualScc() {
        Graph g = new Graph(2);
        g.addEdge(0, 1);
        g.addEdge(1, 0);
        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(Arrays.asList(1, 0));
        assert equalNested(g.findSCCs(), expectedSccs) : "testTwoNodeMutualScc: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{{1, 0}, {1, 0}});
        expectSameMultiset(g.reduceEdges(), expected, "testTwoNodeMutualScc");
    }

    private static void testDenseThreeNodeScc() {
        Graph g = new Graph(3);
        int[][] edges = {{0, 1}, {1, 2}, {2, 0}, {0, 2}, {2, 1}, {1, 0}};
        for (int[] e : edges) {
            g.addEdge(e[0], e[1]);
        }
        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(Arrays.asList(2, 1, 0));
        assert equalNested(g.findSCCs(), expectedSccs) : "testDenseThreeNodeScc: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{{2, 0}, {2, 1}, {2, 0}, {2, 1}});
        expectSameMultiset(g.reduceEdges(), expected, "testDenseThreeNodeScc");
    }

    private static void testMultipleSccsWithCross() {
        // SCC1: 0->1->2->0; SCC2: 3<->4; cross 2->3
        Graph g = new Graph(5);
        g.addEdge(0, 1);
        g.addEdge(1, 2);
        g.addEdge(2, 0);
        g.addEdge(3, 4);
        g.addEdge(4, 3);
        g.addEdge(2, 3);

        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(Arrays.asList(4, 3));
        expectedSccs.add(Arrays.asList(2, 1, 0));
        assert equalNested(g.findSCCs(), expectedSccs) : "testMultipleSccsWithCross: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{{4, 3}, {4, 3}, {2, 0}, {0, 1}, {2, 1}, {1, 0}});
        List<int[]> reduced = g.reduceEdges();
        assert reduced.size() == expected.size() : "testMultipleSccsWithCross: size mismatch";
        expectSameMultiset(reduced, expected, "testMultipleSccsWithCross");
    }

    private static void testDisconnectedWithDagComponent() {
        // SCC: 0,1,2 ; DAG piece: 3->4->5
        Graph g = new Graph(6);
        g.addEdge(0, 1);
        g.addEdge(1, 2);
        g.addEdge(2, 0);
        g.addEdge(3, 4);
        g.addEdge(4, 5);

        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(Arrays.asList(2, 1, 0));
        expectedSccs.add(Arrays.asList(5));
        expectedSccs.add(Arrays.asList(4));
        expectedSccs.add(Arrays.asList(3));
        assert equalNested(g.findSCCs(), expectedSccs) : "testDisconnectedWithDagComponent: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{{2, 0}, {0, 1}, {2, 1}, {1, 0}});
        List<int[]> reduced = g.reduceEdges();
        assert reduced.size() == expected.size() : "testDisconnectedWithDagComponent: size mismatch";
        expectSameMultiset(reduced, expected, "testDisconnectedWithDagComponent");
    }

    private static void testStarLikeScc() {
        // 0 connected both ways with leaves => single SCC
        int n = 7;
        Graph g = new Graph(n);
        for (int i = 1; i < n; i++) {
            g.addEdge(0, i);
            g.addEdge(i, 0);
        }

        List<Integer> scc = new ArrayList<>();
        for (int i = 0; i < n; i++) scc.add(n - 1 - i);
        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(scc);
        assert equalNested(g.findSCCs(), expectedSccs) : "testStarLikeScc: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{
                {6, 0}, {6, 0}, {0, 1}, {0, 2}, {0, 3}, {0, 4}, {0, 5},
                {0, 1}, {0, 2}, {0, 3}, {0, 4}, {0, 5}
        });
        List<int[]> reduced = g.reduceEdges();
        assert reduced.size() == expected.size() : "testStarLikeScc: size mismatch";
        expectSameMultiset(reduced, expected, "testStarLikeScc");
    }

    private static void testLargeRingScc() {
        int n = 300;
        Graph g = new Graph(n);
        List<int[]> expected = new ArrayList<>();

        for (int i = 0; i < n; i++) {
            g.addEdge(i, (i + 1) % n);
            if ((i + 1) != n - 1) expected.add(new int[]{i, (i + 1) % n});
            if (i != 0) expected.add(new int[]{i, (i - 1 + n) % n});
        }

        List<Integer> scc = new ArrayList<>();
        for (int i = 0; i < n; i++) scc.add(n - 1 - i);
        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(scc);
        assert equalNested(g.findSCCs(), expectedSccs) : "testLargeRingScc: SCC mismatch";

        List<int[]> reduced = g.reduceEdges();
        assert reduced.size() == expected.size() : "testLargeRingScc: size mismatch";
        expectSameMultiset(reduced, expected, "testLargeRingScc");
    }

    private static void testRandomSccs() {
        for (int trial = 0; trial < 5; trial++) {
            int n = 80;
            Graph g = new Graph(n);
            List<int[]> expected = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                g.addEdge(i, (i + 1) % n);
                if ((i + 1) != n - 1) expected.add(new int[]{i, (i + 1) % n});
                if (i != 0) expected.add(new int[]{i, (i - 1 + n) % n});
            }

            Random rng = new Random(2025 + trial);
            for (int k = 0; k < n * 2; k++) {
                int u = rng.nextInt(n);
                int v = rng.nextInt(n);
                if (u != v) g.addEdge(u, v);
            }

            List<Integer> scc = new ArrayList<>();
            for (int i = 0; i < n; i++) scc.add(n - 1 - i);
            List<List<Integer>> expectedSccs = new ArrayList<>();
            expectedSccs.add(scc);
            assert equalNested(g.findSCCs(), expectedSccs) : "testRandomSccs trial " + trial + ": SCC mismatch";

            List<int[]> reduced = g.reduceEdges();
            assert reduced.size() == expected.size() : "testRandomSccs trial " + trial + ": size mismatch";
        }
    }

    public static void main(String[] args) {
        testEmptyGraph();
        testSingletonNoEdges();
        testSingletonSelfLoop();
        testSimpleCycle3();
        testTwoNodeMutualScc();
        testDenseThreeNodeScc();
        testMultipleSccsWithCross();
        testDisconnectedWithDagComponent();
        testStarLikeScc();
        testLargeRingScc();
        testRandomSccs();
        System.out.println("All tests passed.");
    }
}
