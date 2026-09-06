import os
import unittest

import pytest

from tests import bench_utils
# The implementation under test is staged by bench/run.py (see
# bench/manifests/smith-waterman/python.json); the adapter exposes the
# canonical entry (a SmithWaterman class with .findAlignment).
from .staging.impl_adapter import BenchSmithWaterman as SmithWaterman

CONFIG = bench_utils.get_bench_config(default_reps=5, default_iters=1)

# Shared large-sequence input, path provided by the runner (SW_INPUT env).
SW_INPUT = os.environ.get(
    "SW_INPUT",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "large_test_input.txt"),
)


class TestSmithWaterman(unittest.TestCase):
    """Correctness via the shared findAlignment entry (uniform across all impls)."""

    def setUp(self):
        self.sw = SmithWaterman(matchScore=2, mismatchScore=-1, gapScore=-1)
        self.e = 1e-6

    def test_perfect_match(self):
        a, b, score, identity = self.sw.findAlignment("ACGT", "ACGT")
        self.assertEqual(a, b)
        self.assertEqual(score, 8)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)

    def test_no_match(self):
        a, b, score, identity = self.sw.findAlignment("AAAA", "TTTT")
        self.assertEqual(a, "")
        self.assertEqual(b, "")
        self.assertEqual(score, 0)
        self.assertAlmostEqual(identity, 0.0, delta=self.e)

    def test_partial_match(self):
        a, b, score, identity = self.sw.findAlignment("ACGTACGT", "TACGTGCA")
        self.assertEqual(a, "TACGT")
        self.assertEqual(b, "TACGT")
        self.assertEqual(score, 10)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)

    def test_gap_in_query(self):
        a, b, score, identity = self.sw.findAlignment("ACGT", "ACAGT")
        self.assertEqual(a, "AC-GT")
        self.assertEqual(b, "ACAGT")
        self.assertEqual(score, 7)
        self.assertAlmostEqual(identity, 80.0, delta=self.e)

    def test_gap_in_reference(self):
        a, b, score, identity = self.sw.findAlignment("ACAGT", "ACGT")
        self.assertEqual(a, "ACAGT")
        self.assertEqual(b, "AC-GT")
        self.assertEqual(score, 7)
        self.assertAlmostEqual(identity, 80.0, delta=self.e)

    def test_single_character_match(self):
        a, b, score, identity = self.sw.findAlignment("A", "A")
        self.assertEqual(a, "A")
        self.assertEqual(b, "A")
        self.assertEqual(score, 2)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)

    def test_single_character_mismatch(self):
        a, b, score, identity = self.sw.findAlignment("A", "T")
        self.assertEqual(score, 0)
        self.assertAlmostEqual(identity, 0.0, delta=self.e)

    def test_large_sequences_from_file(self):
        with open(SW_INPUT) as f:
            lines = f.readlines()
        query, reference = lines[0].strip(), lines[1].strip()
        expected_score = int(lines[2].strip())
        expected_identity = float(lines[3].strip())

        a, b, score, identity = self.sw.findAlignment(query, reference)
        self.assertEqual(len(a), len(b))
        self.assertEqual(score, expected_score)
        self.assertAlmostEqual(identity, expected_identity, delta=self.e)


class TestSmithWatermanPerformance(unittest.TestCase):

    @pytest.mark.perf
    def test_performance_large_sequences(self):
        with open(SW_INPUT) as f:
            lines = f.readlines()
        query, reference = lines[0].strip(), lines[1].strip()

        sw = SmithWaterman(matchScore=2, mismatchScore=-1, gapScore=-1)
        reps, iters = CONFIG["reps"], CONFIG["iters"]
        result = bench_utils.run_benchmark(
            lambda: sw.findAlignment(query, reference), reps=reps, iters=iters, warmup=1
        )
        print(bench_utils.format_result("SW large sequences", result))
        bench_utils.write_result(
            result, algo="smith-waterman", lang="python", impl=CONFIG["impl"],
            iters_per_rep=iters,
            params={"query_len": len(query), "reference_len": len(reference)},
        )
