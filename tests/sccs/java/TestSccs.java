// Swap the line below to switch between sequential and parallel implementations.
//import seq.Graph;
import par.Graph;

import java.util.*;

public class TestGraph {

    private static boolean equalNested(List<List<Integer>> a, List<List<Integer>> b) {
        if (a.size() != b.size()) return false;
        Set<Set<Integer>> setA = new HashSet<>();
        for (List<Integer> scc : a) setA.add(new HashSet<>(scc));
        Set<Set<Integer>> setB = new HashSet<>();
        for (List<Integer> scc : b) setB.add(new HashSet<>(scc));
        return setA.equals(setB);
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
        for (int[] e : edges) list.add(e);
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
        // 0->1->2->0
        // Tarjan gives SCC=[2,1,0], scc.get(0)=2
        //   forward from 2: (2,0),(0,1)
        //   reverse from 2: (2,1),(1,0)
        Graph g = new Graph(3);
        g.addEdge(0, 1);
        g.addEdge(1, 2);
        g.addEdge(2, 0);
        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(Arrays.asList(0, 1, 2));
        assert equalNested(g.findSCCs(), expectedSccs) : "testSimpleCycle3: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{{2, 0}, {0, 1}, {2, 1}, {1, 0}});
        expectSameMultiset(g.reduceEdges(), expected, "testSimpleCycle3");
    }

    private static void testTwoNodeMutualScc() {
        // 0<->1
        // Tarjan gives SCC=[1,0], scc.get(0)=1
        //   forward from 1: (1,0)
        //   reverse from 1: (1,0)
        Graph g = new Graph(2);
        g.addEdge(0, 1);
        g.addEdge(1, 0);
        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(Arrays.asList(0, 1));
        assert equalNested(g.findSCCs(), expectedSccs) : "testTwoNodeMutualScc: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{{1, 0}, {1, 0}});
        expectSameMultiset(g.reduceEdges(), expected, "testTwoNodeMutualScc");
    }

    private static void testDenseThreeNodeScc() {
        // All 6 edges among {0,1,2} (added: 0->1,1->2,2->0,0->2,2->1,1->0)
        // adj[2]=[0,1], Tarjan gives SCC=[2,1,0], scc.get(0)=2
        //   forward from 2: (2,0),(2,1)  [adj[2]=[0,1], both pushed at once from node 2]
        //   reverse from 2: (2,1),(2,0)  [revAdj[2]=[1,0], same pattern]
        Graph g = new Graph(3);
        int[][] edges = {{0, 1}, {1, 2}, {2, 0}, {0, 2}, {2, 1}, {1, 0}};
        for (int[] e : edges) g.addEdge(e[0], e[1]);
        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(Arrays.asList(0, 1, 2));
        assert equalNested(g.findSCCs(), expectedSccs) : "testDenseThreeNodeScc: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{{2, 0}, {2, 1}, {2, 1}, {2, 0}});
        expectSameMultiset(g.reduceEdges(), expected, "testDenseThreeNodeScc");
    }

    private static void testMultipleSccsWithCross() {
        // SCC1: 0->1->2->0  Tarjan root=2: forward (2,0),(0,1); reverse (2,1),(1,0)
        // SCC2: 3<->4        Tarjan root=4: forward (4,3);       reverse (4,3)
        // cross: 2->3
        Graph g = new Graph(5);
        g.addEdge(0, 1); g.addEdge(1, 2); g.addEdge(2, 0);
        g.addEdge(3, 4); g.addEdge(4, 3);
        g.addEdge(2, 3);

        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(Arrays.asList(0, 1, 2));
        expectedSccs.add(Arrays.asList(3, 4));
        assert equalNested(g.findSCCs(), expectedSccs) : "testMultipleSccsWithCross: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{{4, 3}, {4, 3}, {2, 0}, {0, 1}, {2, 1}, {1, 0}});
        List<int[]> reduced = g.reduceEdges();
        assert reduced.size() == expected.size() : "testMultipleSccsWithCross: size mismatch";
        expectSameMultiset(reduced, expected, "testMultipleSccsWithCross");
    }

    private static void testDisconnectedWithDagComponent() {
        // SCC {0,1,2}: 0->1->2->0  Tarjan root=2: forward (2,0),(0,1); reverse (2,1),(1,0)
        // Singletons {3},{4},{5}: 3->4->5 (DAG, no SCC edges)
        Graph g = new Graph(6);
        g.addEdge(0, 1); g.addEdge(1, 2); g.addEdge(2, 0);
        g.addEdge(3, 4); g.addEdge(4, 5);

        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(Arrays.asList(0, 1, 2));
        expectedSccs.add(Arrays.asList(3));
        expectedSccs.add(Arrays.asList(4));
        expectedSccs.add(Arrays.asList(5));
        assert equalNested(g.findSCCs(), expectedSccs) : "testDisconnectedWithDagComponent: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{{2, 0}, {0, 1}, {2, 1}, {1, 0}});
        List<int[]> reduced = g.reduceEdges();
        assert reduced.size() == expected.size() : "testDisconnectedWithDagComponent: size mismatch";
        expectSameMultiset(reduced, expected, "testDisconnectedWithDagComponent");
    }

    private static void testStarLikeScc() {
        // 0 connected both ways with 1..6 => single SCC
        // Tarjan gives SCC=[6,5,4,3,2,1,0], scc.get(0)=6
        //   forward from 6: (6,0),(0,1),(0,2),(0,3),(0,4),(0,5)
        //   reverse from 6: (6,0),(0,1),(0,2),(0,3),(0,4),(0,5)  [same structure]
        int n = 7;
        Graph g = new Graph(n);
        for (int i = 1; i < n; i++) {
            g.addEdge(0, i);
            g.addEdge(i, 0);
        }

        List<Integer> scc = new ArrayList<>();
        for (int i = 0; i < n; i++) scc.add(i);
        List<List<Integer>> expectedSccs = new ArrayList<>();
        expectedSccs.add(scc);
        assert equalNested(g.findSCCs(), expectedSccs) : "testStarLikeScc: SCC mismatch";

        List<int[]> expected = toEdgeList(new int[][]{
                {6, 0}, {0, 1}, {0, 2}, {0, 3}, {0, 4}, {0, 5},
                {6, 0}, {0, 1}, {0, 2}, {0, 3}, {0, 4}, {0, 5}
        });
        List<int[]> reduced = g.reduceEdges();
        assert reduced.size() == expected.size() : "testStarLikeScc: size mismatch";
        expectSameMultiset(reduced, expected, "testStarLikeScc");
    }

    private static void testLargeRingScc() {
        // Ring 0->1->...->299->0
        // Tarjan gives SCC=[299,298,...,0], scc.get(0)=299
        //   forward from 299: (299,0),(0,1),(1,2),...,(297,298)   = n-1 edges
        //   reverse from 299: (299,298),(298,297),...,(1,0)         = n-1 edges
        int n = 300;
        Graph g = new Graph(n);
        for (int i = 0; i < n; i++) g.addEdge(i, (i + 1) % n);

        List<int[]> expected = new ArrayList<>();
        expected.add(new int[]{n - 1, 0});                                      // forward start: 299->0
        for (int i = 0; i < n - 2; i++) expected.add(new int[]{i, i + 1});    // forward rest: 0->1,...,297->298
        for (int i = n - 1; i > 0; i--) expected.add(new int[]{i, i - 1});    // reverse: 299->298,...,1->0

        List<Integer> scc = new ArrayList<>();
        for (int i = 0; i < n; i++) scc.add(i);
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
            for (int i = 0; i < n; i++) g.addEdge(i, (i + 1) % n);

            Random rng = new Random(2025 + trial);
            for (int k = 0; k < n * 2; k++) {
                int u = rng.nextInt(n);
                int v = rng.nextInt(n);
                if (u != v) g.addEdge(u, v);
            }

            List<Integer> scc = new ArrayList<>();
            for (int i = 0; i < n; i++) scc.add(i);
            List<List<Integer>> expectedSccs = new ArrayList<>();
            expectedSccs.add(scc);
            assert equalNested(g.findSCCs(), expectedSccs) : "testRandomSccs trial " + trial + ": SCC mismatch";

            List<int[]> reduced = g.reduceEdges();
            assert reduced.size() == 2 * (n - 1) : "testRandomSccs trial " + trial + ": size mismatch, got " + reduced.size();
        }
    }

    private static boolean edgeListsEqual(List<int[]> a, List<int[]> b) {
        if (a.size() != b.size()) return false;
        for (int i = 0; i < a.size(); i++) {
            if (a.get(i)[0] != b.get(i)[0] || a.get(i)[1] != b.get(i)[1]) return false;
        }
        return true;
    }

    // Sort edge list for stable comparison across runs (used in testDeterminism)
    private static List<int[]> sortedEdges(List<int[]> edges) {
        List<int[]> sorted = new ArrayList<>(edges);
        sortEdges(sorted);
        return sorted;
    }

    private static void testDeterminism() {
        int numScc = 24;
        int sccSize = 40;
        int n = numScc * sccSize;
        int runs = 5;

        long seed = new Random().nextLong();
        Random rng = new Random(seed);

        Graph g = new Graph(n);
        for (int s = 0; s < numScc; s++) {
            int start = s * sccSize;
            for (int u = start; u < start + sccSize; u++) {
                int nxt = start + (u - start + 1) % sccSize;
                g.addEdge(u, nxt);
            }
            for (int i = 0; i < sccSize * 3; i++) {
                int u = start + rng.nextInt(sccSize);
                int v = start + rng.nextInt(sccSize);
                if (u != v) g.addEdge(u, v);
            }
        }
        for (int s = 0; s < numScc - 1; s++) {
            int a0 = s * sccSize;
            int b0 = (s + 1) * sccSize;
            for (int i = 0; i < 6; i++) {
                int u = a0 + rng.nextInt(sccSize);
                int v = b0 + rng.nextInt(sccSize);
                g.addEdge(u, v);
            }
        }

        List<int[]> baseline = sortedEdges(g.reduceEdges());
        for (int r = 1; r < runs; r++) {
            List<int[]> edges = sortedEdges(g.reduceEdges());
            assert edgeListsEqual(edges, baseline) :
                "testDeterminism run " + r + ": output differs from run 0" +
                " (seed=" + seed + ", baseline_len=" + baseline.size() + ", this_len=" + edges.size() + ")";
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
        testDeterminism();
        System.out.println("All tests passed.");
    }
}
