use crate::smith_waterman::SmithWaterman;
use std::cell::Cell;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::time::Instant;

thread_local! {
    static TESTS_PASSED: Cell<i32> = Cell::new(0);
    static TESTS_FAILED: Cell<i32> = Cell::new(0);
}

pub fn get_failed_count() -> i32 {
    TESTS_FAILED.with(|f| f.get())
}

fn run_test(name: &str, test_fn: fn()) {
    print!("Running: {}... ", name);
    match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| test_fn())) {
        Ok(_) => {
            println!("✓ PASSED");
            TESTS_PASSED.with(|p| p.set(p.get() + 1));
        }
        Err(_) => {
            println!("✗ FAILED");
            TESTS_FAILED.with(|f| f.set(f.get() + 1));
        }
    }
}

fn assert_eq_f64(a: f64, b: f64, epsilon: f64) {
    assert!((a - b).abs() < epsilon, "Expected: {}, Actual: {}", b, a);
}

// ==================== Basic Functionality Tests ====================

fn test_perfect_match() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("ACGT", "ACGT");
    
    assert_eq!(result.aligned_a, result.aligned_b);
    assert_eq!(result.score, 8);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

fn test_no_match() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("AAAA", "TTTT");
    
    assert_eq!(result.aligned_a, "");
    assert_eq!(result.aligned_b, "");
    assert_eq!(result.score, 0);
    assert_eq_f64(result.identity, 0.0, 1e-6);
}

fn test_partial_match() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("ACGTACGT", "TACGTGCA");
    
    assert_eq!(result.aligned_a.len(), result.aligned_b.len());
    assert_eq!(result.aligned_a, "TACGT");
    assert_eq!(result.aligned_b, "TACGT");
    assert_eq!(result.score, 10);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

fn test_gap_in_query() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("ACGT", "ACAGT");
    
    assert_eq!(result.aligned_a, "AC-GT");
    assert_eq!(result.aligned_b, "ACAGT");
    assert_eq!(result.score, 7);
    assert_eq_f64(result.identity, 80.0, 1e-6);
}

fn test_gap_in_reference() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("ACAGT", "ACGT");
    
    assert_eq!(result.aligned_b, "AC-GT");
    assert_eq!(result.aligned_a, "ACAGT");
    assert_eq!(result.score, 7);
    assert_eq_f64(result.identity, 80.0, 1e-6);
}

// ==================== Edge Cases ====================

fn test_empty_query() {
    let sw = SmithWaterman::new(2, -1, -1);
    let h = sw.construct_matrix("", "ACGT");
    assert_eq!(h.len(), 1);
    
    let result = sw.traceback(&h, "", "ACGT");
    assert_eq!(result.aligned_a, "");
    assert_eq!(result.aligned_b, "");
    assert_eq!(result.score, 0);
    assert_eq_f64(result.identity, 0.0, 1e-6);
}

fn test_empty_reference() {
    let sw = SmithWaterman::new(2, -1, -1);
    let h = sw.construct_matrix("ACGT", "");
    assert_eq!(h[0].len(), 1);
    
    let result = sw.traceback(&h, "ACGT", "");
    assert_eq!(result.aligned_a, "");
    assert_eq!(result.aligned_b, "");
    assert_eq!(result.score, 0);
    assert_eq_f64(result.identity, 0.0, 1e-6);
}

fn test_both_empty() {
    let sw = SmithWaterman::new(2, -1, -1);
    let h = sw.construct_matrix("", "");
    assert_eq!(h.len(), 1);
    assert_eq!(h[0].len(), 1);
    
    let result = sw.traceback(&h, "", "");
    assert_eq!(result.aligned_a, "");
    assert_eq!(result.aligned_b, "");
    assert_eq!(result.score, 0);
    assert_eq_f64(result.identity, 0.0, 1e-6);
}

fn test_single_character_match() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("A", "A");
    
    assert_eq!(result.aligned_a, "A");
    assert_eq!(result.aligned_b, "A");
    assert_eq!(result.score, 2);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

fn test_single_character_mismatch() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("A", "T");
    
    assert_eq!(result.aligned_a, "");
    assert_eq!(result.aligned_b, "");
    assert_eq!(result.score, 0);
    assert_eq_f64(result.identity, 0.0, 1e-6);
}

fn test_query_much_longer() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("ACGTACGTACGTACGT", "ACG");
    
    assert_eq!(result.aligned_a.len(), result.aligned_b.len());
    assert_eq!(result.aligned_b, "ACG");
    assert_eq!(result.aligned_a, "ACG");
    assert_eq!(result.score, 6);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

fn test_reference_much_longer() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("ACG", "ACGTACGTACGTACGT");
    
    assert_eq!(result.aligned_a.len(), result.aligned_b.len());
    assert_eq!(result.aligned_b, "ACG");
    assert_eq!(result.aligned_a, "ACG");
    assert_eq!(result.score, 6);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

// ==================== Matrix Construction Tests ====================

fn test_matrix_dimensions() {
    let sw = SmithWaterman::new(2, -1, -1);
    let h = sw.construct_matrix("ACGT", "TAGC");
    
    assert_eq!(h.len(), 5); // query.len() + 1
    assert_eq!(h[0].len(), 5); // reference.len() + 1
}

fn test_matrix_first_row_column_zeros() {
    let sw = SmithWaterman::new(2, -1, -1);
    let h = sw.construct_matrix("ACGT", "TAGC");
    
    // Check first row
    for &val in &h[0] {
        assert_eq!(val, 0);
    }
    
    // Check first column
    for row in &h {
        assert_eq!(row[0], 0);
    }
}

fn test_matrix_non_negative_values() {
    let sw = SmithWaterman::new(2, -1, -1);
    let h = sw.construct_matrix("ACGTTAGC", "GCATACGT");
    
    for row in &h {
        for &val in row {
            assert!(val >= 0);
        }
    }
}

fn test_find_highest_score_simple() {
    let sw = SmithWaterman::new(2, -1, -1);
    let h = sw.construct_matrix("AC", "AC");
    let (i, j) = sw.find_highest_score(&h);
    
    assert_eq!(i, 2);
    assert_eq!(j, 2);
}

fn test_find_highest_score_zero_matrix() {
    let sw = SmithWaterman::new(2, -1, -1);
    let h = vec![vec![0, 0, 0], vec![0, 0, 0], vec![0, 0, 0]];
    let (i, j) = sw.find_highest_score(&h);
    
    assert_eq!(i, 0);
    assert_eq!(j, 0);
}

// ==================== Different Scoring Schemes ====================

fn test_high_gap_penalty() {
    let sw = SmithWaterman::new(3, -3, -2);
    let result = sw.find_alignment("ACGT", "ACAGT");
    
    assert_eq!(result.aligned_a.len(), result.aligned_b.len());
    assert_eq!(result.aligned_a, "AC-GT");
    assert_eq!(result.aligned_b, "ACAGT");
    assert_eq!(result.score, 10);
    assert_eq_f64(result.identity, 80.0, 1e-6);
}

fn test_negative_match_score() {
    let sw = SmithWaterman::new(-1, -2, -1);
    let h = sw.construct_matrix("ACGT", "ACGT");
    
    for row in &h {
        for &val in row {
            assert_eq!(val, 0);
        }
    }
}

// ==================== Special Character Tests ====================

fn test_lowercase_sequences() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("acgt", "acgt");
    
    assert_eq!(result.aligned_a, "acgt");
    assert_eq!(result.aligned_b, "acgt");
    assert_eq!(result.score, 8);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

fn test_mixed_case_sequences() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("AcGt", "aCgT");
    
    assert_eq!(result.aligned_a.len(), result.aligned_b.len());
    assert_eq!(result.aligned_a, "");
    assert_eq!(result.aligned_b, "");
    assert_eq!(result.score, 0);
    assert_eq_f64(result.identity, 0.0, 1e-6);
}

fn test_numeric_characters() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("123", "123");
    
    assert_eq!(result.aligned_a, "123");
    assert_eq!(result.aligned_b, "123");
    assert_eq!(result.score, 6);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

fn test_special_characters() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("A-C*G", "A-C*G");
    
    assert_eq!(result.aligned_a, "A-C*G");
    assert_eq!(result.aligned_b, "A-C*G");
    assert_eq!(result.score, 10);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

// ==================== Repetitive Patterns ====================

fn test_repeated_characters() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("AAAA", "AAAA");
    
    assert_eq!(result.aligned_a, "AAAA");
    assert_eq!(result.aligned_b, "AAAA");
    assert_eq!(result.score, 8);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

fn test_tandem_repeats() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("ACGTACGTACGT", "ACGTACGTACGT");
    
    assert_eq!(result.aligned_a, "ACGTACGTACGT");
    assert_eq!(result.aligned_b, "ACGTACGTACGT");
    assert_eq!(result.score, 24);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

// ==================== Alignment Properties Tests ====================

fn test_alignment_lengths_equal() {
    let sw = SmithWaterman::new(2, -1, -1);
    
    let test_cases = vec![
        ("ACGT", "TAGC", "A-C", "AGC"),
        ("AAAA", "TTTT", "", ""),
        ("ACGTACGT", "ACGT", "ACGT", "ACGT"),
        ("A", "ACGTACGT", "A", "A"),
        ("ACGTNNACGT", "ACGTACGT", "ACGTNNACGT", "ACGT--ACGT"),
    ];
    
    for (query, reference, expected_a, expected_b) in test_cases {
        let result = sw.find_alignment(query, reference);
        assert_eq!(result.aligned_a.len(), result.aligned_b.len(),
                   "Failed for query={}, reference={}", query, reference);
        assert_eq!(result.aligned_a, expected_a);
        assert_eq!(result.aligned_b, expected_b);
    }
}

fn test_no_double_gaps() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("ACGTACGT", "TAGCTAGC");
    
    assert_eq!(result.aligned_a.len(), result.aligned_b.len());
    assert_eq!(result.aligned_a, "A-CGTA-C");
    assert_eq!(result.aligned_b, "AGC-TAGC");
    assert_eq!(result.score, 7);
    assert_eq_f64(result.identity, 62.5, 1e-6);
}

// ==================== Real Biological Sequences ====================

fn test_realistic_dna_sequences() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("ATCGATCGATCG", "ATCGATCGATCG");
    
    assert_eq!(result.aligned_a, "ATCGATCGATCG");
    assert_eq!(result.aligned_b, "ATCGATCGATCG");
    assert_eq!(result.score, 24);
    assert_eq_f64(result.identity, 100.0, 1e-6);
}

fn test_dna_with_single_mutation() {
    let sw = SmithWaterman::new(2, -1, -1);
    let result = sw.find_alignment("ATCGATCGATCG", "ATCGTTCGATCG");
    
    assert!(result.aligned_a.len() > 8);
    assert_eq!(result.aligned_a.len(), result.aligned_b.len());
    assert_eq!(result.score, 21);
    assert_eq_f64(result.identity, 91.66666666666666, 1e-6);
}

// ==================== Performance Tests ====================

fn test_performance_medium_sequences() {
    let sw = SmithWaterman::new(2, -1, -1);
    
    let query = "ACGT".repeat(50);
    let reference = "TAGC".repeat(50);
    
    let start = Instant::now();
    let h = sw.construct_matrix(&query, &reference);
    let matrix_time = start.elapsed().as_secs_f64();
    
    let start = Instant::now();
    let _result = sw.traceback(&h, &query, &reference);
    let traceback_time = start.elapsed().as_secs_f64();
    
    print!("(Matrix: {:.4}s, Traceback: {:.4}s) ", matrix_time, traceback_time);
    
    assert!(matrix_time < 5.0, "Matrix construction took too long");
    assert!(traceback_time < 2.0, "Traceback took too long");
}

fn test_large_sequences_from_file() {
    let file_path = "large_test_input.txt";
    
    match File::open(file_path) {
        Ok(file) => {
            let reader = BufReader::new(file);
            let lines: Vec<String> = reader.lines().filter_map(Result::ok).collect();
            
            if lines.len() >= 4 {
                let query = lines[0].trim();
                let reference = lines[1].trim();
                let expected_score: i32 = lines[2].trim().parse().unwrap();
                let expected_identity: f64 = lines[3].trim().parse().unwrap();
                
                let sw = SmithWaterman::new(2, -1, -1);
                let h = sw.construct_matrix(query, reference);
                assert_eq!(h.len(), query.len() + 1);
                assert_eq!(h[0].len(), reference.len() + 1);
                
                let result = sw.traceback(&h, query, reference);
                assert_eq!(result.aligned_a.len(), result.aligned_b.len());
                assert_eq!(result.score, expected_score);
                assert_eq_f64(result.identity, expected_identity, 1e-6);
            }
        }
        Err(_) => {
            print!("SKIPPED (file not found) ");
        }
    }
}

// ==================== Run All Tests ====================

pub fn run_all_tests() {
    // Reset counters
    TESTS_PASSED.with(|p| p.set(0));
    TESTS_FAILED.with(|f| f.set(0));

    println!("============================================");
    println!("Running Smith-Waterman Tests");
    println!("============================================\n");

    println!("=== Basic Functionality Tests ===");
    run_test("test_perfect_match", test_perfect_match);
    run_test("test_no_match", test_no_match);
    run_test("test_partial_match", test_partial_match);
    run_test("test_gap_in_query", test_gap_in_query);
    run_test("test_gap_in_reference", test_gap_in_reference);

    println!("\n=== Edge Cases ===");
    run_test("test_empty_query", test_empty_query);
    run_test("test_empty_reference", test_empty_reference);
    run_test("test_both_empty", test_both_empty);
    run_test("test_single_character_match", test_single_character_match);
    run_test("test_single_character_mismatch", test_single_character_mismatch);
    run_test("test_query_much_longer", test_query_much_longer);
    run_test("test_reference_much_longer", test_reference_much_longer);

    println!("\n=== Matrix Construction Tests ===");
    run_test("test_matrix_dimensions", test_matrix_dimensions);
    run_test("test_matrix_first_row_column_zeros", test_matrix_first_row_column_zeros);
    run_test("test_matrix_non_negative_values", test_matrix_non_negative_values);
    run_test("test_find_highest_score_simple", test_find_highest_score_simple);
    run_test("test_find_highest_score_zero_matrix", test_find_highest_score_zero_matrix);

    println!("\n=== Different Scoring Schemes ===");
    run_test("test_high_gap_penalty", test_high_gap_penalty);
    run_test("test_negative_match_score", test_negative_match_score);

    println!("\n=== Special Character Tests ===");
    run_test("test_lowercase_sequences", test_lowercase_sequences);
    run_test("test_mixed_case_sequences", test_mixed_case_sequences);
    run_test("test_numeric_characters", test_numeric_characters);
    run_test("test_special_characters", test_special_characters);

    println!("\n=== Repetitive Patterns ===");
    run_test("test_repeated_characters", test_repeated_characters);
    run_test("test_tandem_repeats", test_tandem_repeats);

    println!("\n=== Alignment Properties ===");
    run_test("test_alignment_lengths_equal", test_alignment_lengths_equal);
    run_test("test_no_double_gaps", test_no_double_gaps);

    println!("\n=== Biological Sequences ===");
    run_test("test_realistic_dna_sequences", test_realistic_dna_sequences);
    run_test("test_dna_with_single_mutation", test_dna_with_single_mutation);

    println!("\n=== Performance Tests ===");
    run_test("test_performance_medium_sequences", test_performance_medium_sequences);
    run_test("test_large_sequences_from_file", test_large_sequences_from_file);

    let passed = TESTS_PASSED.with(|p| p.get());
    let failed = TESTS_FAILED.with(|f| f.get());

    println!("\n============================================");
    println!("Test Summary:");
    println!("  Passed: {}", passed);
    println!("  Failed: {}", failed);
    println!("  Total:  {}", passed + failed);
    println!("============================================");
}