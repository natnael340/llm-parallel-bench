import unittest
import pytest
import os
from tests import bench_utils
from .main import SmithWaterman as SmithWatermanSequential
from .algo_parallel import SmithWaterman as SmithWatermanParallel

IMPL = os.environ.get("IMPL", "par")
_BaseImpl = SmithWatermanParallel if IMPL == "par" else SmithWatermanSequential


class SmithWaterman(_BaseImpl):
    pass


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class TestSmithWaterman(unittest.TestCase):
    
    def setUp(self):
        self.sw_standard = SmithWaterman(matchScore=2, mismatchScore=-1, gapScore=-1)
        self.sw_high_gap = SmithWaterman(matchScore=3, mismatchScore=-3, gapScore=-2)
        self.e = 1e-6  # Small epsilon for floating point comparisons
    
    # ==================== Basic Functionality Tests ====================
    
    def test_perfect_match(self):
        """Test with identical sequences"""
        query = "ACGT"
        reference = "ACGT"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        self.assertEqual(aligned_a, aligned_b)
        self.assertEqual(score, 8)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)

    
    def test_no_match(self):
        """Test with completely different sequences"""
        query = "AAAA"
        reference = "TTTT"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        
        self.assertEqual(aligned_a, "")
        self.assertEqual(aligned_b, "")
        self.assertEqual(score, 0)
        self.assertAlmostEqual(identity, 0.0, delta=self.e)
    
    def test_partial_match(self):
        """Test with partial sequence overlap"""
        query = "ACGTACGT"
        reference = "TACGTGCA"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(query, reference)
       
        self.assertEqual(len(aligned_a), len(aligned_b))
        self.assertEqual(aligned_a, "TACGT")
        self.assertEqual(aligned_b, "TACGT")
        self.assertEqual(score, 10)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)
    
    def test_gap_in_query(self):
        """Test alignment with gap in query sequence"""
        query = "ACGT"
        reference = "ACAGT"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        
        self.assertEqual(aligned_a, "AC-GT")
        self.assertEqual(aligned_b, "ACAGT")
        self.assertEqual(score, 7)
        self.assertAlmostEqual(identity, 80.0, delta=self.e)
    
    def test_gap_in_reference(self):
        """Test alignment with gap in reference sequence"""
        query = "ACAGT"
        reference = "ACGT"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        self.assertEqual(aligned_b, "AC-GT")
        self.assertEqual(aligned_a, "ACAGT")
        self.assertEqual(score, 7)
        self.assertAlmostEqual(identity, 80.0, delta=self.e)
    
    # ==================== Edge Cases ====================
    
    def test_empty_query(self):
        """Test with empty query string"""
        query = ""
        reference = "ACGT"
        H = self.sw_standard.constructMatrix(query, reference)
        self.assertEqual(len(H), 1)  # Only header row
        start_pos = self.sw_standard.findHighestScore(H)
        aligned_a, aligned_b, score, identity = self.sw_standard.traceback(H, query, reference, start_pos)
        self.assertEqual(aligned_a, "")
        self.assertEqual(aligned_b, "")
        self.assertEqual(score, 0)
        self.assertAlmostEqual(identity, 0.0, delta=self.e)
    
    def test_empty_reference(self):
        """Test with empty reference string"""
        query = "ACGT"
        reference = ""
        H = self.sw_standard.constructMatrix(query, reference)
        self.assertEqual(len(H[0]), 1)  # Only header column
        start_pos = self.sw_standard.findHighestScore(H)
        aligned_a, aligned_b, score, identity = self.sw_standard.traceback(H, query, reference, start_pos)
        self.assertEqual(aligned_a, "")
        self.assertEqual(aligned_b, "")
        self.assertEqual(score, 0)
        self.assertAlmostEqual(identity, 0.0, delta=self.e)
    
    def test_both_empty(self):
        """Test with both sequences empty"""
        query = ""
        reference = ""
        H = self.sw_standard.constructMatrix(query, reference)
        self.assertEqual(len(H), 1)
        self.assertEqual(len(H[0]), 1)
        start_pos = self.sw_standard.findHighestScore(H)
        aligned_a, aligned_b, score, identity = self.sw_standard.traceback(H, query, reference, start_pos)
        self.assertEqual(aligned_a, "")
        self.assertEqual(aligned_b, "")
        self.assertEqual(score, 0)
        self.assertAlmostEqual(identity, 0.0, delta=self.e)
    
    def test_single_character_match(self):
        """Test with single character sequences that match"""
        query = "A"
        reference = "A"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        self.assertEqual(aligned_a, "A")
        self.assertEqual(aligned_b, "A")
        self.assertEqual(score, 2)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)
    
    def test_single_character_mismatch(self):
        """Test with single character sequences that don't match"""
        query = "A"
        reference = "T"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        
        self.assertEqual(aligned_a, "")
        self.assertEqual(aligned_b, "")
        self.assertEqual(score, 0)
        self.assertAlmostEqual(identity, 0.0, delta=self.e)
    
    def test_query_much_longer(self):
        """Test when query is much longer than reference"""
        query = "ACGTACGTACGTACGT"
        reference = "ACG"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(query, reference)

        self.assertEqual(len(aligned_a), len(aligned_b))
        self.assertEqual(aligned_b, "ACG")
        self.assertEqual(aligned_a, "ACG")
        self.assertEqual(score, 6)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)
    
    def test_reference_much_longer(self):
        """Test when reference is much longer than query"""
        query = "ACG"
        reference = "ACGTACGTACGTACGT"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(query, reference)
        self.assertEqual(len(aligned_a), len(aligned_b))
        self.assertEqual(aligned_b, "ACG")
        self.assertEqual(aligned_a, "ACG")
        self.assertEqual(score, 6)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)
    
    # ==================== Matrix Construction Tests ====================
    
    def test_matrix_dimensions(self):
        """Test that matrix has correct dimensions"""
        query = "ACGT"
        reference = "TAGC"
        H = self.sw_standard.constructMatrix(query, reference)
        self.assertEqual(len(H), len(query) + 1)
        self.assertEqual(len(H[0]), len(reference) + 1)
    
    def test_matrix_first_row_column_zeros(self):
        """Test that first row and column are all zeros"""
        query = "ACGT"
        reference = "TAGC"
        H = self.sw_standard.constructMatrix(query, reference)
        
        # Check first row
        for val in H[0]:
            self.assertEqual(val, 0)
        
        # Check first column
        for row in H:
            self.assertEqual(row[0], 0)
    
    def test_matrix_non_negative_values(self):
        """Test that all matrix values are non-negative (Smith-Waterman property)"""
        query = "ACGTTAGC"
        reference = "GCATACGT"
        H = self.sw_standard.constructMatrix(query, reference)
        
        for row in H:
            for val in row:
                self.assertGreaterEqual(val, 0)
    
    def test_find_highest_score_simple(self):
        """Test finding highest score in matrix"""
        query = "AC"
        reference = "AC"
        H = self.sw_standard.constructMatrix(query, reference)
        pos = self.sw_standard.findHighestScore(H)
        self.assertIsInstance(pos, tuple)
        self.assertEqual(len(pos), 2)
        # Highest score should be at bottom-right for perfect match
        self.assertEqual(pos, (2, 2))
    
    def test_find_highest_score_zero_matrix(self):
        """Test finding highest score when all scores are zero"""
        H = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        pos = self.sw_standard.findHighestScore(H)
        self.assertEqual(pos, (0, 0))
    
    # ==================== Different Scoring Schemes ====================
    
    def test_high_gap_penalty(self):
        """Test with high gap penalty"""
        query = "ACGT"
        reference = "ACAGT"
        aligned_a, aligned_b, score, identity = self.sw_high_gap.findAlignment(
            query,
            reference
        )
        self.assertEqual(len(aligned_a), len(aligned_b))
        self.assertEqual(aligned_a, "AC-GT")
        self.assertEqual(aligned_b, "ACAGT")
        self.assertEqual(score, 10)
        self.assertAlmostEqual(identity, 80.0, delta=self.e)
    
    def test_negative_match_score(self):
        """Test with negative match score (unusual but valid)"""
        sw_negative = SmithWaterman(matchScore=-1, mismatchScore=-2, gapScore=-1)
        query = "ACGT"
        reference = "ACGT"
        H = sw_negative.constructMatrix(query, reference)
        
        # All values should remain zero due to Smith-Waterman's max(0, ...) constraint
        for row in H:
            for val in row:
                self.assertEqual(val, 0)
    
    # ==================== Special Character Tests ====================
    
    def test_lowercase_sequences(self):
        """Test with lowercase sequences"""
        query = "acgt"
        reference = "acgt"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        self.assertEqual(aligned_a, "acgt")
        self.assertEqual(aligned_b, "acgt")
        self.assertEqual(score, 8)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)
    
    def test_mixed_case_sequences(self):
        """Test with mixed case sequences"""
        query = "AcGt"
        reference = "aCgT"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment( query, reference)
        # Should not find partial matches where case matches
        # Expecting no alignment due to case sensitivity
        self.assertEqual(len(aligned_a), len(aligned_b))
        self.assertEqual(aligned_a, "")
        self.assertEqual(aligned_b, "")
        self.assertEqual(score, 0)
        self.assertAlmostEqual(identity, 0.0, delta=self.e)
    
    def test_numeric_characters(self):
        """Test with numeric characters in sequences"""
        query = "123"
        reference = "123"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        self.assertEqual(aligned_a, "123")
        self.assertEqual(aligned_b, "123")
        self.assertEqual(score, 6)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)
    
    def test_special_characters(self):
        """Test with special characters"""
        query = "A-C*G"
        reference = "A-C*G"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        self.assertEqual(aligned_a, "A-C*G")
        self.assertEqual(aligned_b, "A-C*G")
        self.assertEqual(score, 10)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)
    
    # ==================== Repetitive Patterns ====================
    
    def test_repeated_characters(self):
        """Test with sequences of repeated characters"""
        query = "AAAA"
        reference = "AAAA"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        self.assertEqual(aligned_a, "AAAA")
        self.assertEqual(aligned_b, "AAAA")
        self.assertEqual(score, 8)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)
    
    def test_tandem_repeats(self):
        """Test with tandem repeat sequences"""
        query = "ACGTACGTACGT"
        reference = "ACGTACGTACGT"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        self.assertEqual(aligned_a, query)
        self.assertEqual(aligned_b, reference)
        self.assertEqual(score, 24)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)
    
    # ==================== Alignment Properties Tests ====================
    
    def test_alignment_lengths_equal(self):
        """Test that aligned sequences always have equal length"""
        test_cases = [
            ("ACGT", "TAGC", "A-C", "AGC"),
            ("AAAA", "TTTT", "", ""),
            ("ACGTACGT", "ACGT", "ACGT", "ACGT"),
            ("A", "ACGTACGT", "A", "A"),
            ("ACGTNNACGT", "ACGTACGT", "ACGTNNACGT", "ACGT--ACGT"),
        ]
        
        for query, reference, expected_a, expected_b in test_cases:
            with self.subTest(query=query, reference=reference):
                aligned_a, aligned_b, _, _ = self.sw_standard.findAlignment(query, reference)
                self.assertEqual(len(aligned_a), len(aligned_b))
                self.assertEqual(aligned_a, expected_a)
                self.assertEqual(aligned_b, expected_b)
    
    def test_no_double_gaps(self):
        """Test that there are no positions with gaps in both sequences"""
        query = "ACGTACGT"
        reference = "TAGCTAGC"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(query, reference)
        
        self.assertEqual(len(aligned_a), len(aligned_b))
        self.assertEqual(aligned_a, "A-CGTA-C")
        self.assertEqual(aligned_b, "AGC-TAGC")
        self.assertEqual(score, 7)
        self.assertAlmostEqual(identity, 62.5, delta=self.e)
        # ==================== Real Biological Sequences ====================
    
    def test_realistic_dna_sequences(self):
        """Test with realistic DNA sequences"""
        query = "ATCGATCGATCG"
        reference = "ATCGATCGATCG"
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(
            query,
            reference
        )
        self.assertEqual(aligned_a, query)
        self.assertEqual(aligned_b, reference)
        self.assertEqual(score, 24)
        self.assertAlmostEqual(identity, 100.0, delta=self.e)
    
    def test_dna_with_single_mutation(self):
        """Test DNA sequences with single point mutation"""
        query = "ATCGATCGATCG"
        reference = "ATCGTTCGATCG"  # T instead of A at position 5
        aligned_a, aligned_b, score, identity = self.sw_standard.findAlignment(query, reference)
        
        # Should still align most of the sequence
        self.assertGreater(len(aligned_a), 8)
        self.assertEqual(len(aligned_a), len(aligned_b))
        self.assertEqual(score, 21)
        self.assertAlmostEqual(identity, 91.66666666666666, delta=self.e)


# Test for large input files
class TestSmithWatermanLargeInput(unittest.TestCase):
    
    def setUp(self):
        self.sw = SmithWaterman(matchScore=2, mismatchScore=-1, gapScore=-1)
        self.e = 1e-6  # Small epsilon for floating point comparisons
    
    def test_large_sequences_from_file(self):
        """Test with large sequences loaded from file"""
        try:
            with open(os.path.join(BASE_DIR, 'large_test_input.txt'), 'r') as f:
                lines = f.readlines()
                query = lines[0].strip()
                reference = lines[1].strip()
                expected_score = int(lines[2].strip())
                expected_identity = float(lines[3].strip())
            
            # Test matrix construction completes
            H = self.sw.constructMatrix(query, reference)
            self.assertIsNotNone(H)
            
            # Test dimensions
            self.assertEqual(len(H), len(query) + 1)
            self.assertEqual(len(H[0]), len(reference) + 1)
            
            # Test traceback completes
            start_pos = self.sw.findHighestScore(H)
            aligned_a, aligned_b, score, identity = self.sw.traceback(H, query, reference, start_pos)
            self.assertEqual(len(aligned_a), len(aligned_b))
            self.assertEqual(score, expected_score)
            self.assertAlmostEqual(identity, expected_identity, delta=self.e)
            
        except FileNotFoundError:
            self.skipTest("large_test_input.txt not found")
    
    def test_performance_medium_sequences(self):
        """Test performance with medium-sized sequences (100-500 chars)"""
        import time
        
        query = "ACGT" * 50  # 200 characters
        reference = "TAGC" * 50  # 200 characters
        
        start_time = time.time()
        H = self.sw.constructMatrix(query, reference)
        matrix_time = time.time() - start_time
        
        start_time = time.time()
        start_pos = self.sw.findHighestScore(H)
        _ = self.sw.traceback(H, query, reference, start_pos)
        traceback_time = time.time() - start_time
        
        # These are reasonable time limits; adjust as needed
        self.assertLess(matrix_time, 5.0, "Matrix construction took too long")
        self.assertLess(traceback_time, 2.0, "Traceback took too long")

class TestSmithWatermanPerformance(unittest.TestCase):
    
    def setUp(self):
        self.sw = SmithWaterman(matchScore=2, mismatchScore=-1, gapScore=-1)
        self.e = 1e-6  # Small epsilon for floating point comparisons
    
    def test_performance_large_sequences(self):
        try:
            with open(os.path.join(BASE_DIR, 'large_test_input.txt'), 'r') as f:
                lines = f.readlines()
                query = lines[0].strip()
                reference = lines[1].strip()

            def run_alignment():
                _ = self.sw.findAlignment(query, reference)

            reps, iters = 5, 1
            result = bench_utils.run_benchmark(run_alignment, reps=reps, iters=iters, warmup=1)
            print(bench_utils.format_result("SW large sequences", result))
            bench_utils.write_result(
                result, algo="smith-waterman", lang="python", impl=IMPL, iters_per_rep=iters
            )

        except FileNotFoundError:
            self.skipTest("large_test_input.txt not found")