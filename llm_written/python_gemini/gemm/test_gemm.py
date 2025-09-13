
import unittest
import random
import copy
import time
from gemm_parallel import gemm, gemm_sequential, validate_matrix

def create_random_matrix(rows: int, cols: int, seed: int = 0) -> list[list[float]]:
    """Creates a matrix with deterministic random values."""
    rand = random.Random(seed)
    return [[rand.uniform(-10.0, 10.0) for _ in range(cols)] for _ in range(rows)]

class TestGEMM(unittest.TestCase):

    def assertMatricesAlmostEqual(self, A, B, places=5, msg=None):
        """Asserts that two matrices are almost equal, element by element."""
        self.assertEqual(len(A), len(B), msg=f"Matrix row count differs: {len(A)} vs {len(B)}. {msg or ''}")
        self.assertEqual(len(A[0]), len(B[0]), msg=f"Matrix col count differs: {len(A[0])} vs {len(B[0])}. {msg or ''}")
        for r in range(len(A)):
            for c in range(len(A[0])):
                self.assertAlmostEqual(A[r][c], B[r][c], places=places, msg=f"Mismatch at ({r},{c}). {msg or ''}")

    def test_small_matrix(self):
        """Test with a small, well-known matrix multiplication."""
        A = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
        B = [[1.0, 4.0], [2.0, 5.0], [3.0, 6.0]]
        expected_C = [[14.0, 32.0], [32.0, 77.0], [50.0, 122.0]]
        
        C_seq = gemm_sequential(A, B)
        C_par = gemm(A, B)
        
        self.assertMatricesAlmostEqual(C_seq, expected_C, msg="Sequential result mismatch")
        self.assertMatricesAlmostEqual(C_par, expected_C, msg="Parallel result mismatch")
        self.assertMatricesAlmostEqual(C_seq, C_par, msg="Sequential vs Parallel mismatch")

    def test_alpha_beta_params(self):
        """Test the alpha and beta scaling factors."""
        A = create_random_matrix(20, 30, seed=1)
        B = create_random_matrix(30, 25, seed=2)
        C_init = create_random_matrix(20, 25, seed=3)
        alpha = 2.5
        beta = -1.5

        C_init_seq = copy.deepcopy(C_init)
        C_init_par = copy.deepcopy(C_init)

        # Expected result: C = alpha * A * B + beta * C_init
        C_base = gemm_sequential(A, B)
        expected_C = [[alpha * C_base[r][c] + beta * C_init[r][c] for c in range(25)] for r in range(20)]

        C_seq = gemm_sequential(A, B, alpha=alpha, C=C_init_seq, beta=beta)
        C_par = gemm(A, B, alpha=alpha, C=C_init_par, beta=beta)

        self.assertMatricesAlmostEqual(C_seq, expected_C, msg="Sequential alpha/beta result mismatch")
        self.assertMatricesAlmostEqual(C_par, expected_C, msg="Parallel alpha/beta result mismatch")
        self.assertMatricesAlmostEqual(C_seq, C_par, msg="Sequential vs Parallel mismatch for alpha/beta")

    def test_various_shapes_and_sizes(self):
        """Test with various matrix shapes and block sizes."""
        # Note: Using small dimensions to force many blocks and test edge cases
        # in blocking logic. For parallel execution, larger matrices are needed.
        test_configs = [
            # m, k, n, MB, NB, KB
            (100, 50, 80, 32, 32, 16),
            (128, 128, 128, 64, 64, 64), # Powers of 2
            (99, 47, 83, 33, 29, 17),    # Prime dimensions
            (200, 10, 150, 64, 64, 8),   # Tall A, small k
            (10, 200, 15, 8, 8, 64),     # Wide A
        ]

        for i, (m, k, n, mb, nb, kb) in enumerate(test_configs):
            with self.subTest(f"config_{i}", m=m, k=k, n=n, MB=mb, NB=nb, KB=kb):
                A = create_random_matrix(m, k, seed=10 + i)
                B = create_random_matrix(k, n, seed=20 + i)

                C_seq = gemm_sequential(A, B, MB=mb, NB=nb, KB=kb)
                C_par = gemm(A, B, MB=mb, NB=nb, KB=kb)
                
                self.assertMatricesAlmostEqual(C_seq, C_par, msg=f"Mismatch for config {i}")

    def test_large_matrix_correctness(self):
        """Differential test with a large matrix to trigger parallel path."""
        m, k, n = 256, 128, 200
        A = create_random_matrix(m, k, seed=42)
        B = create_random_matrix(k, n, seed=43)

        print(f"\nTesting correctness for large matrix ({m}x{k}) * ({k}x{n})...")
        start_seq = time.time()
        C_seq = gemm_sequential(A, B)
        duration_seq = time.time() - start_seq
        print(f"Sequential finished in {duration_seq:.4f}s")
        
        start_par = time.time()
        C_par = gemm(A, B)
        duration_par = time.time() - start_par
        print(f"Parallel finished in {duration_par:.4f}s")
        
        self.assertMatricesAlmostEqual(C_seq, C_par)

    def test_determinism(self):
        """Ensure the parallel implementation is deterministic."""
        m, k, n = 200, 150, 180
        A = create_random_matrix(m, k, seed=101)
        B = create_random_matrix(k, n, seed=102)

        print("\nTesting determinism...")
        
        C1 = gemm(A, B)
        C2 = gemm(A, B)

        # For determinism, results must be exactly equal, not just close.
        self.assertEqual(C1, C2, "Parallel implementation is not deterministic.")

    def test_input_validation(self):
        """Test that input validation raises appropriate errors."""
        with self.assertRaises(ValueError, msg="Should fail for ragged matrix"):
            validate_matrix([[1], [2, 3]], "ragged")
        with self.assertRaises(ValueError, msg="Should fail for non-numeric"):
            validate_matrix([[1, "a"]], "non-numeric")
        with self.assertRaises(ValueError, msg="Should fail for shape mismatch"):
            gemm([[1, 2]], [[1], [2], [3]])


if __name__ == '__main__':
    unittest.main()
