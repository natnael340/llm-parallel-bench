using System;
using System.IO;
using System.Diagnostics;

namespace SmithWatermanAlignment
{
    public class SmithWatermanTests
    {
        private SmithWaterman swStandard = null!;
        private SmithWaterman swHighGap = null!;
        private const double Epsilon = 1e-6;
        
        private int testsPassed = 0;
        private int testsFailed = 0;

        public int GetPassedCount() => testsPassed;
        public int GetFailedCount() => testsFailed;

        public void SetUp()
        {
            swStandard = new SmithWaterman(match: 2, mismatch: -1, gap: -1);
            swHighGap = new SmithWaterman(match: 3, mismatch: -3, gap: -2);
        }

        private void RunTest(string testName, Action testMethod)
        {
            Console.Write($"Running: {testName}... ");
            try
            {
                testMethod();
                Console.WriteLine("✓ PASSED");
                testsPassed++;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"✗ FAILED: {ex.Message}");
                testsFailed++;
            }
        }

        private void AssertEqual<T>(T expected, T actual, string message = "")
        {
            if (expected == null && actual == null) return;
            if (expected == null || actual == null || !expected.Equals(actual))
            {
                throw new Exception($"Expected: {expected}, Actual: {actual}. {message}");
            }
        }

        private void AssertEqual(double expected, double actual, double delta, string message = "")
        {
            if (Math.Abs(expected - actual) > delta)
            {
                throw new Exception($"Expected: {expected}, Actual: {actual} (within {delta}). {message}");
            }
        }

        private void AssertGreater<T>(T actual, T threshold, string message = "") where T : IComparable<T>
        {
            if (actual.CompareTo(threshold) <= 0)
            {
                throw new Exception($"Expected {actual} > {threshold}. {message}");
            }
        }

        private void AssertGreaterOrEqual<T>(T actual, T threshold, string message = "") where T : IComparable<T>
        {
            if (actual.CompareTo(threshold) < 0)
            {
                throw new Exception($"Expected {actual} >= {threshold}. {message}");
            }
        }

        private void AssertLess<T>(T actual, T threshold, string message = "") where T : IComparable<T>
        {
            if (actual.CompareTo(threshold) >= 0)
            {
                throw new Exception($"Expected {actual} < {threshold}. {message}");
            }
        }

        private void AssertNotNull(object obj, string message = "")
        {
            if (obj == null)
            {
                throw new Exception($"Expected non-null object. {message}");
            }
        }

        // ==================== Basic Functionality Tests ====================

        public void TestPerfectMatch()
        {
            string query = "ACGT";
            string reference = "ACGT";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual(alignedA, alignedB);
            AssertEqual(8, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        public void TestNoMatch()
        {
            string query = "AAAA";
            string reference = "TTTT";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual("", alignedA);
            AssertEqual("", alignedB);
            AssertEqual(0, score);
            AssertEqual(0.0, identity, Epsilon);
        }

        public void TestPartialMatch()
        {
            string query = "ACGTACGT";
            string reference = "TACGTGCA";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual(alignedA.Length, alignedB.Length);
            AssertEqual("TACGT", alignedA);
            AssertEqual("TACGT", alignedB);
            AssertEqual(10, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        public void TestGapInQuery()
        {
            string query = "ACGT";
            string reference = "ACAGT";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual("AC-GT", alignedA);
            AssertEqual("ACAGT", alignedB);
            AssertEqual(7, score);
            AssertEqual(80.0, identity, Epsilon);
        }

        public void TestGapInReference()
        {
            string query = "ACAGT";
            string reference = "ACGT";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual("AC-GT", alignedB);
            AssertEqual("ACAGT", alignedA);
            AssertEqual(7, score);
            AssertEqual(80.0, identity, Epsilon);
        }

        // ==================== Edge Cases ====================

        public void TestEmptyQuery()
        {
            string query = "";
            string reference = "ACGT";

            var H = swStandard.ConstructMatrix(query, reference);
            AssertEqual(1, H.Length);

            var (alignedA, alignedB, score, identity) = swStandard.Traceback(H, query, reference);
            AssertEqual("", alignedA);
            AssertEqual("", alignedB);
            AssertEqual(0, score);
            AssertEqual(0.0, identity, Epsilon);
        }

        public void TestEmptyReference()
        {
            string query = "ACGT";
            string reference = "";

            var H = swStandard.ConstructMatrix(query, reference);
            AssertEqual(1, H[0].Length);

            var (alignedA, alignedB, score, identity) = swStandard.Traceback(H, query, reference);
            AssertEqual("", alignedA);
            AssertEqual("", alignedB);
            AssertEqual(0, score);
            AssertEqual(0.0, identity, Epsilon);
        }

        public void TestBothEmpty()
        {
            string query = "";
            string reference = "";

            var H = swStandard.ConstructMatrix(query, reference);
            AssertEqual(1, H.Length);
            AssertEqual(1, H[0].Length);

            var (alignedA, alignedB, score, identity) = swStandard.Traceback(H, query, reference);
            AssertEqual("", alignedA);
            AssertEqual("", alignedB);
            AssertEqual(0, score);
            AssertEqual(0.0, identity, Epsilon);
        }

        public void TestSingleCharacterMatch()
        {
            string query = "A";
            string reference = "A";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual("A", alignedA);
            AssertEqual("A", alignedB);
            AssertEqual(2, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        public void TestSingleCharacterMismatch()
        {
            string query = "A";
            string reference = "T";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual("", alignedA);
            AssertEqual("", alignedB);
            AssertEqual(0, score);
            AssertEqual(0.0, identity, Epsilon);
        }

        public void TestQueryMuchLonger()
        {
            string query = "ACGTACGTACGTACGT";
            string reference = "ACG";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual(alignedA.Length, alignedB.Length);
            AssertEqual("ACG", alignedB);
            AssertEqual("ACG", alignedA);
            AssertEqual(6, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        public void TestReferenceMuchLonger()
        {
            string query = "ACG";
            string reference = "ACGTACGTACGTACGT";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual(alignedA.Length, alignedB.Length);
            AssertEqual("ACG", alignedB);
            AssertEqual("ACG", alignedA);
            AssertEqual(6, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        // ==================== Matrix Construction Tests ====================

        public void TestMatrixDimensions()
        {
            string query = "ACGT";
            string reference = "TAGC";

            var H = swStandard.ConstructMatrix(query, reference);

            AssertEqual(query.Length + 1, H.Length);
            AssertEqual(reference.Length + 1, H[0].Length);
        }

        public void TestMatrixFirstRowColumnZeros()
        {
            string query = "ACGT";
            string reference = "TAGC";

            var H = swStandard.ConstructMatrix(query, reference);

            foreach (int val in H[0])
            {
                AssertEqual(0, val);
            }

            foreach (var row in H)
            {
                AssertEqual(0, row[0]);
            }
        }

        public void TestMatrixNonNegativeValues()
        {
            string query = "ACGTTAGC";
            string reference = "GCATACGT";

            var H = swStandard.ConstructMatrix(query, reference);

            foreach (var row in H)
            {
                foreach (int val in row)
                {
                    AssertGreaterOrEqual(val, 0);
                }
            }
        }

        public void TestFindHighestScoreSimple()
        {
            string query = "AC";
            string reference = "AC";

            var H = swStandard.ConstructMatrix(query, reference);
            var (i, j) = swStandard.FindHighestScore(H);

            AssertEqual(2, i);
            AssertEqual(2, j);
        }

        public void TestFindHighestScoreZeroMatrix()
        {
            int[][] H = new int[][]
            {
                new int[] {0, 0, 0},
                new int[] {0, 0, 0},
                new int[] {0, 0, 0}
            };

            var (i, j) = swStandard.FindHighestScore(H);

            AssertEqual(0, i);
            AssertEqual(0, j);
        }

        // ==================== Different Scoring Schemes ====================

        public void TestHighGapPenalty()
        {
            string query = "ACGT";
            string reference = "ACAGT";

            var (alignedA, alignedB, score, identity) = swHighGap.FindAlignment(query, reference);

            AssertEqual(alignedA.Length, alignedB.Length);
            AssertEqual("AC-GT", alignedA);
            AssertEqual("ACAGT", alignedB);
            AssertEqual(10, score);
            AssertEqual(80.0, identity, Epsilon);
        }

        public void TestNegativeMatchScore()
        {
            var swNegative = new SmithWaterman(match: -1, mismatch: -2, gap: -1);
            string query = "ACGT";
            string reference = "ACGT";

            var H = swNegative.ConstructMatrix(query, reference);

            foreach (var row in H)
            {
                foreach (int val in row)
                {
                    AssertEqual(0, val);
                }
            }
        }

        // ==================== Special Character Tests ====================

        public void TestLowercaseSequences()
        {
            string query = "acgt";
            string reference = "acgt";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual("acgt", alignedA);
            AssertEqual("acgt", alignedB);
            AssertEqual(8, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        public void TestMixedCaseSequences()
        {
            string query = "AcGt";
            string reference = "aCgT";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual(alignedA.Length, alignedB.Length);
            AssertEqual("", alignedA);
            AssertEqual("", alignedB);
            AssertEqual(0, score);
            AssertEqual(0.0, identity, Epsilon);
        }

        public void TestNumericCharacters()
        {
            string query = "123";
            string reference = "123";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual("123", alignedA);
            AssertEqual("123", alignedB);
            AssertEqual(6, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        public void TestSpecialCharacters()
        {
            string query = "A-C*G";
            string reference = "A-C*G";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual("A-C*G", alignedA);
            AssertEqual("A-C*G", alignedB);
            AssertEqual(10, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        // ==================== Repetitive Patterns ====================

        public void TestRepeatedCharacters()
        {
            string query = "AAAA";
            string reference = "AAAA";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual("AAAA", alignedA);
            AssertEqual("AAAA", alignedB);
            AssertEqual(8, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        public void TestTandemRepeats()
        {
            string query = "ACGTACGTACGT";
            string reference = "ACGTACGTACGT";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual(query, alignedA);
            AssertEqual(reference, alignedB);
            AssertEqual(24, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        // ==================== Alignment Properties Tests ====================

        public void TestAlignmentLengthsEqual()
        {
            var testCases = new[]
            {
                (query: "ACGT", reference: "TAGC", expectedA: "A-C", expectedB: "AGC"),
                (query: "AAAA", reference: "TTTT", expectedA: "", expectedB: ""),
                (query: "ACGTACGT", reference: "ACGT", expectedA: "ACGT", expectedB: "ACGT"),
                (query: "A", reference: "ACGTACGT", expectedA: "A", expectedB: "A"),
                (query: "ACGTNNACGT", reference: "ACGTACGT", expectedA: "ACGTNNACGT", expectedB: "ACGT--ACGT")
            };

            foreach (var testCase in testCases)
            {
                var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(testCase.query, testCase.reference);
                AssertEqual(alignedA.Length, alignedB.Length,
                    $"Failed for query={testCase.query}, reference={testCase.reference}");
                AssertEqual(testCase.expectedA, alignedA);
                AssertEqual(testCase.expectedB, alignedB);
            }
        }

        public void TestNoDoubleGaps()
        {
            string query = "ACGTACGT";
            string reference = "TAGCTAGC";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual(alignedA.Length, alignedB.Length);
            AssertEqual("A-CGTA-C", alignedA);
            AssertEqual("AGC-TAGC", alignedB);
            AssertEqual(7, score);
            AssertEqual(62.5, identity, Epsilon);
        }

        // ==================== Real Biological Sequences ====================

        public void TestRealisticDnaSequences()
        {
            string query = "ATCGATCGATCG";
            string reference = "ATCGATCGATCG";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertEqual(query, alignedA);
            AssertEqual(reference, alignedB);
            AssertEqual(24, score);
            AssertEqual(100.0, identity, Epsilon);
        }

        public void TestDnaWithSingleMutation()
        {
            string query = "ATCGATCGATCG";
            string reference = "ATCGTTCGATCG";

            var (alignedA, alignedB, score, identity) = swStandard.FindAlignment(query, reference);

            AssertGreater(alignedA.Length, 8);
            AssertEqual(alignedA.Length, alignedB.Length);
            AssertEqual(21, score);
            AssertEqual(91.66666666666666, identity, Epsilon);
        }

        // ==================== Performance Tests ====================

        public void TestPerformanceMediumSequences()
        {
            string query = string.Concat(System.Linq.Enumerable.Repeat("ACGT", 50));
            string reference = string.Concat(System.Linq.Enumerable.Repeat("TAGC", 50));

            Stopwatch sw = Stopwatch.StartNew();
            var H = swStandard.ConstructMatrix(query, reference);
            sw.Stop();
            double matrixTime = sw.Elapsed.TotalSeconds;

            sw.Restart();
            var result = swStandard.Traceback(H, query, reference);
            sw.Stop();
            double tracebackTime = sw.Elapsed.TotalSeconds;

            Console.Write($"(Matrix: {matrixTime:F4}s, Traceback: {tracebackTime:F4}s) ");

            AssertLess(matrixTime, 5.0, "Matrix construction took too long");
            AssertLess(tracebackTime, 2.0, "Traceback took too long");
        }

        public void TestLargeSequencesFromFile()
        {
            string filePath = "large_test_input.txt";

            if (!File.Exists(filePath))
            {
                Console.Write("SKIPPED (file not found) ");
                return;
            }

            string[] lines = File.ReadAllLines(filePath);
            string query = lines[0].Trim();
            string reference = lines[1].Trim();
            int expectedScore = int.Parse(lines[2].Trim());
            double expectedIdentity = double.Parse(lines[3].Trim());

            var H = swStandard.ConstructMatrix(query, reference);
            AssertNotNull(H);
            AssertEqual(query.Length + 1, H.Length);
            AssertEqual(reference.Length + 1, H[0].Length);

            var (alignedA, alignedB, score, identity) = swStandard.Traceback(H, query, reference);
            AssertEqual(alignedA.Length, alignedB.Length);
            AssertEqual(expectedScore, score);
            AssertEqual(expectedIdentity, identity, Epsilon);
        }

        // ==================== Run All Tests ====================

        public void RunAllTests()
        {
            SetUp();

            Console.WriteLine("============================================");
            Console.WriteLine("Running Smith-Waterman Tests");
            Console.WriteLine("============================================\n");

            Console.WriteLine("=== Basic Functionality Tests ===");
            RunTest("TestPerfectMatch", TestPerfectMatch);
            RunTest("TestNoMatch", TestNoMatch);
            RunTest("TestPartialMatch", TestPartialMatch);
            RunTest("TestGapInQuery", TestGapInQuery);
            RunTest("TestGapInReference", TestGapInReference);

            Console.WriteLine("\n=== Edge Cases ===");
            RunTest("TestEmptyQuery", TestEmptyQuery);
            RunTest("TestEmptyReference", TestEmptyReference);
            RunTest("TestBothEmpty", TestBothEmpty);
            RunTest("TestSingleCharacterMatch", TestSingleCharacterMatch);
            RunTest("TestSingleCharacterMismatch", TestSingleCharacterMismatch);
            RunTest("TestQueryMuchLonger", TestQueryMuchLonger);
            RunTest("TestReferenceMuchLonger", TestReferenceMuchLonger);

            Console.WriteLine("\n=== Matrix Construction Tests ===");
            RunTest("TestMatrixDimensions", TestMatrixDimensions);
            RunTest("TestMatrixFirstRowColumnZeros", TestMatrixFirstRowColumnZeros);
            RunTest("TestMatrixNonNegativeValues", TestMatrixNonNegativeValues);
            RunTest("TestFindHighestScoreSimple", TestFindHighestScoreSimple);
            RunTest("TestFindHighestScoreZeroMatrix", TestFindHighestScoreZeroMatrix);

            Console.WriteLine("\n=== Different Scoring Schemes ===");
            RunTest("TestHighGapPenalty", TestHighGapPenalty);
            RunTest("TestNegativeMatchScore", TestNegativeMatchScore);

            Console.WriteLine("\n=== Special Character Tests ===");
            RunTest("TestLowercaseSequences", TestLowercaseSequences);
            RunTest("TestMixedCaseSequences", TestMixedCaseSequences);
            RunTest("TestNumericCharacters", TestNumericCharacters);
            RunTest("TestSpecialCharacters", TestSpecialCharacters);

            Console.WriteLine("\n=== Repetitive Patterns ===");
            RunTest("TestRepeatedCharacters", TestRepeatedCharacters);
            RunTest("TestTandemRepeats", TestTandemRepeats);

            Console.WriteLine("\n=== Alignment Properties ===");
            RunTest("TestAlignmentLengthsEqual", TestAlignmentLengthsEqual);
            RunTest("TestNoDoubleGaps", TestNoDoubleGaps);

            Console.WriteLine("\n=== Biological Sequences ===");
            RunTest("TestRealisticDnaSequences", TestRealisticDnaSequences);
            RunTest("TestDnaWithSingleMutation", TestDnaWithSingleMutation);

            Console.WriteLine("\n=== Performance Tests ===");
            RunTest("TestPerformanceMediumSequences", TestPerformanceMediumSequences);
            RunTest("TestLargeSequencesFromFile", TestLargeSequencesFromFile);

            Console.WriteLine("\n============================================");
            Console.WriteLine("Test Summary:");
            Console.WriteLine($"  Passed: {testsPassed}");
            Console.WriteLine($"  Failed: {testsFailed}");
            Console.WriteLine($"  Total:  {testsPassed + testsFailed}");
            Console.WriteLine("============================================");
        }
    }
}