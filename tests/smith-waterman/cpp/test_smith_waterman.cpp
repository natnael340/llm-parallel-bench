#include <iostream>
#include <fstream>
#include <cassert>
#include <cmath>
#include <string>
#include <chrono>
#include "../../llm_written/gemini-2.5-pro/smith-waterman/c++/algo_parallel.h"

// Helper function for floating point comparison
bool almostEqual(double a, double b, double epsilon = 1e-6) {
    return std::fabs(a - b) < epsilon;
}

// Test counter
int tests_passed = 0;
int tests_failed = 0;

#define TEST(name) \
    std::cout << "Running: " << name << "... "; \
    try {

#define END_TEST \
        std::cout << "✓ PASSED" << std::endl; \
        tests_passed++; \
    } catch (const std::exception& e) { \
        std::cout << "✗ FAILED: " << e.what() << std::endl; \
        tests_failed++; \
    }

// ==================== Basic Functionality Tests ====================

void test_perfect_match() {
    TEST("test_perfect_match")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACGT";
    std::string reference = "ACGT";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == aligned_b);
    assert(score == 8);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

void test_no_match() {
    TEST("test_no_match")
    SmithWaterman sw(2, -1, -1);
    std::string query = "AAAA";
    std::string reference = "TTTT";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == "");
    assert(aligned_b == "");
    assert(score == 0);
    assert(almostEqual(identity, 0.0));
    END_TEST
}

void test_partial_match() {
    TEST("test_partial_match")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACGTACGT";
    std::string reference = "TACGTGCA";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a.length() == aligned_b.length());
    assert(aligned_a == "TACGT");
    assert(aligned_b == "TACGT");
    assert(score == 10);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

void test_gap_in_query() {
    TEST("test_gap_in_query")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACGT";
    std::string reference = "ACAGT";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == "AC-GT");
    assert(aligned_b == "ACAGT");
    assert(score == 7);
    assert(almostEqual(identity, 80.0));
    END_TEST
}

void test_gap_in_reference() {
    TEST("test_gap_in_reference")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACAGT";
    std::string reference = "ACGT";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_b == "AC-GT");
    assert(aligned_a == "ACAGT");
    assert(score == 7);
    assert(almostEqual(identity, 80.0));
    END_TEST
}

// ==================== Edge Cases ====================

void test_empty_query() {
    TEST("test_empty_query")
    SmithWaterman sw(2, -1, -1);
    std::string query = "";
    std::string reference = "ACGT";
    
    auto H = sw.constructMatrix(query, reference);
    assert(H.size() == 1); // Only header row
    
    auto [aligned_a, aligned_b, score, identity] = sw.traceback(H, query, reference);
    assert(aligned_a == "");
    assert(aligned_b == "");
    assert(score == 0);
    assert(almostEqual(identity, 0.0));
    END_TEST
}

void test_empty_reference() {
    TEST("test_empty_reference")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACGT";
    std::string reference = "";
    
    auto H = sw.constructMatrix(query, reference);
    assert(H[0].size() == 1); // Only header column
    
    auto [aligned_a, aligned_b, score, identity] = sw.traceback(H, query, reference);
    assert(aligned_a == "");
    assert(aligned_b == "");
    assert(score == 0);
    assert(almostEqual(identity, 0.0));
    END_TEST
}

void test_both_empty() {
    TEST("test_both_empty")
    SmithWaterman sw(2, -1, -1);
    std::string query = "";
    std::string reference = "";
    
    auto H = sw.constructMatrix(query, reference);
    assert(H.size() == 1);
    assert(H[0].size() == 1);
    
    auto [aligned_a, aligned_b, score, identity] = sw.traceback(H, query, reference);
    assert(aligned_a == "");
    assert(aligned_b == "");
    assert(score == 0);
    assert(almostEqual(identity, 0.0));
    END_TEST
}

void test_single_character_match() {
    TEST("test_single_character_match")
    SmithWaterman sw(2, -1, -1);
    std::string query = "A";
    std::string reference = "A";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == "A");
    assert(aligned_b == "A");
    assert(score == 2);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

void test_single_character_mismatch() {
    TEST("test_single_character_mismatch")
    SmithWaterman sw(2, -1, -1);
    std::string query = "A";
    std::string reference = "T";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == "");
    assert(aligned_b == "");
    assert(score == 0);
    assert(almostEqual(identity, 0.0));
    END_TEST
}

void test_query_much_longer() {
    TEST("test_query_much_longer")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACGTACGTACGTACGT";
    std::string reference = "ACG";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a.length() == aligned_b.length());
    assert(aligned_b == "ACG");
    assert(aligned_a == "ACG");
    assert(score == 6);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

void test_reference_much_longer() {
    TEST("test_reference_much_longer")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACG";
    std::string reference = "ACGTACGTACGTACGT";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a.length() == aligned_b.length());
    assert(aligned_b == "ACG");
    assert(aligned_a == "ACG");
    assert(score == 6);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

// ==================== Matrix Construction Tests ====================

void test_matrix_dimensions() {
    TEST("test_matrix_dimensions")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACGT";
    std::string reference = "TAGC";
    
    auto H = sw.constructMatrix(query, reference);
    assert(H.size() == query.length() + 1);
    assert(H[0].size() == reference.length() + 1);
    END_TEST
}

void test_matrix_first_row_column_zeros() {
    TEST("test_matrix_first_row_column_zeros")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACGT";
    std::string reference = "TAGC";
    
    auto H = sw.constructMatrix(query, reference);
    
    // Check first row
    for (int val : H[0]) {
        assert(val == 0);
    }
    
    // Check first column
    for (const auto& row : H) {
        assert(row[0] == 0);
    }
    END_TEST
}

void test_matrix_non_negative_values() {
    TEST("test_matrix_non_negative_values")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACGTTAGC";
    std::string reference = "GCATACGT";
    
    auto H = sw.constructMatrix(query, reference);
    
    for (const auto& row : H) {
        for (int val : row) {
            assert(val >= 0);
        }
    }
    END_TEST
}

void test_find_highest_score_simple() {
    TEST("test_find_highest_score_simple")
    SmithWaterman sw(2, -1, -1);
    std::string query = "AC";
    std::string reference = "AC";
    
    auto H = sw.constructMatrix(query, reference);
    auto pos = sw.findHighestScore(H);
    
    // Highest score should be at bottom-right for perfect match
    assert(pos.first == 2);
    assert(pos.second == 2);
    END_TEST
}

void test_find_highest_score_zero_matrix() {
    TEST("test_find_highest_score_zero_matrix")
    SmithWaterman sw(2, -1, -1);
    std::vector<std::vector<int>> H = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}};
    
    auto pos = sw.findHighestScore(H);
    assert(pos.first == 0);
    assert(pos.second == 0);
    END_TEST
}

// ==================== Different Scoring Schemes ====================

void test_high_gap_penalty() {
    TEST("test_high_gap_penalty")
    SmithWaterman sw(3, -3, -2);
    std::string query = "ACGT";
    std::string reference = "ACAGT";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a.length() == aligned_b.length());
    assert(aligned_a == "AC-GT");
    assert(aligned_b == "ACAGT");
    assert(score == 10);
    assert(almostEqual(identity, 80.0));
    END_TEST
}

void test_negative_match_score() {
    TEST("test_negative_match_score")
    SmithWaterman sw(-1, -2, -1);
    std::string query = "ACGT";
    std::string reference = "ACGT";
    
    auto H = sw.constructMatrix(query, reference);
    
    // All values should remain zero due to Smith-Waterman's max(0, ...) constraint
    for (const auto& row : H) {
        for (int val : row) {
            assert(val == 0);
        }
    }
    END_TEST
}

// ==================== Special Character Tests ====================

void test_lowercase_sequences() {
    TEST("test_lowercase_sequences")
    SmithWaterman sw(2, -1, -1);
    std::string query = "acgt";
    std::string reference = "acgt";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == "acgt");
    assert(aligned_b == "acgt");
    assert(score == 8);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

void test_mixed_case_sequences() {
    TEST("test_mixed_case_sequences")
    SmithWaterman sw(2, -1, -1);
    std::string query = "AcGt";
    std::string reference = "aCgT";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a.length() == aligned_b.length());
    assert(aligned_a == "");
    assert(aligned_b == "");
    assert(score == 0);
    assert(almostEqual(identity, 0.0));
    END_TEST
}

void test_numeric_characters() {
    TEST("test_numeric_characters")
    SmithWaterman sw(2, -1, -1);
    std::string query = "123";
    std::string reference = "123";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == "123");
    assert(aligned_b == "123");
    assert(score == 6);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

void test_special_characters() {
    TEST("test_special_characters")
    SmithWaterman sw(2, -1, -1);
    std::string query = "A-C*G";
    std::string reference = "A-C*G";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == "A-C*G");
    assert(aligned_b == "A-C*G");
    assert(score == 10);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

// ==================== Repetitive Patterns ====================

void test_repeated_characters() {
    TEST("test_repeated_characters")
    SmithWaterman sw(2, -1, -1);
    std::string query = "AAAA";
    std::string reference = "AAAA";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == "AAAA");
    assert(aligned_b == "AAAA");
    assert(score == 8);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

void test_tandem_repeats() {
    TEST("test_tandem_repeats")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACGTACGTACGT";
    std::string reference = "ACGTACGTACGT";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == query);
    assert(aligned_b == reference);
    assert(score == 24);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

// ==================== Alignment Properties Tests ====================

void test_alignment_lengths_equal() {
    TEST("test_alignment_lengths_equal")
    SmithWaterman sw(2, -1, -1);
    
    struct TestCase {
        std::string query;
        std::string reference;
        std::string expected_a;
        std::string expected_b;
    };
    
    TestCase cases[] = {
        {"ACGT", "TAGC", "A-C", "AGC"},
        {"AAAA", "TTTT", "", ""},
        {"ACGTACGT", "ACGT", "ACGT", "ACGT"},
        {"A", "ACGTACGT", "A", "A"},
        {"ACGTNNACGT", "ACGTACGT", "ACGTNNACGT", "ACGT--ACGT"}
    };
    
    for (const auto& tc : cases) {
        auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(tc.query, tc.reference);
        assert(aligned_a.length() == aligned_b.length());
        assert(aligned_a == tc.expected_a);
        assert(aligned_b == tc.expected_b);
    }
    END_TEST
}

void test_no_double_gaps() {
    TEST("test_no_double_gaps")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ACGTACGT";
    std::string reference = "TAGCTAGC";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a.length() == aligned_b.length());
    assert(aligned_a == "A-CGTA-C");
    assert(aligned_b == "AGC-TAGC");
    assert(score == 7);
    assert(almostEqual(identity, 62.5));
    END_TEST
}

// ==================== Real Biological Sequences ====================

void test_realistic_dna_sequences() {
    TEST("test_realistic_dna_sequences")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ATCGATCGATCG";
    std::string reference = "ATCGATCGATCG";
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    assert(aligned_a == query);
    assert(aligned_b == reference);
    assert(score == 24);
    assert(almostEqual(identity, 100.0));
    END_TEST
}

void test_dna_with_single_mutation() {
    TEST("test_dna_with_single_mutation")
    SmithWaterman sw(2, -1, -1);
    std::string query = "ATCGATCGATCG";
    std::string reference = "ATCGTTCGATCG"; // T instead of A at position 5
    
    auto [aligned_a, aligned_b, score, identity] = sw.findAlignment(query, reference);
    
    // Should still align most of the sequence
    assert(aligned_a.length() > 8);
    assert(aligned_a.length() == aligned_b.length());
    assert(score == 21);
    assert(almostEqual(identity, 91.66666666666666));
    END_TEST
}

// ==================== Performance Tests ====================

void test_performance_medium_sequences() {
    TEST("test_performance_medium_sequences")
    SmithWaterman sw(2, -1, -1);
    
    // Create medium-sized sequences (200 characters each)
    std::string query = "";
    std::string reference = "";
    for (int i = 0; i < 50; i++) {
        query += "ACGT";
        reference += "TAGC";
    }
    
    // Test matrix construction time
    auto start = std::chrono::high_resolution_clock::now();
    auto H = sw.constructMatrix(query, reference);
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> matrix_time = end - start;
    
    // Test traceback time
    start = std::chrono::high_resolution_clock::now();
    auto result = sw.traceback(H, query, reference);
    end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> traceback_time = end - start;
    
    std::cout << "(Matrix: " << matrix_time.count() << "s, Traceback: " << traceback_time.count() << "s) ";
    
    assert(matrix_time.count() < 5.0);
    assert(traceback_time.count() < 2.0);
    END_TEST
}

void test_large_sequences_from_file() {
    TEST("test_large_sequences_from_file")
    SmithWaterman sw(2, -1, -1);
    
    std::ifstream file("large_test_input.txt");
    if (!file.is_open()) {
        std::cout << "SKIPPED (file not found)" << std::endl;
        return;
    }
    
    std::string query, reference;
    int expected_score;
    double expected_identity;
    
    std::getline(file, query);
    std::getline(file, reference);
    file >> expected_score >> expected_identity;
    file.close();
    
    // Test matrix construction
    auto H = sw.constructMatrix(query, reference);
    assert(H.size() > 0);
    assert(H.size() == query.length() + 1);
    assert(H[0].size() == reference.length() + 1);
    
    // Test traceback
    auto [aligned_a, aligned_b, score, identity] = sw.traceback(H, query, reference);
    assert(aligned_a.length() == aligned_b.length());
    assert(score == expected_score);
    assert(almostEqual(identity, expected_identity));
    END_TEST
}

void test_performance() {
    TEST("test_performance")
    SmithWaterman sw(2, -1, -1);
    
    std::ifstream file("large_test_input.txt");
    if (!file.is_open()) {
        std::cout << "SKIPPED (file not found)" << std::endl;
        return;
    }
    
    std::string query, reference;
    
    std::getline(file, query);
    std::getline(file, reference);
    file.close();

    // warmup
    auto _ = sw.findAlignment(query, reference);

    int iters = 20;
    int runs = 5;

    double nums [runs];
    for (int run = 0; run < runs; run++) {
        auto start = std::chrono::high_resolution_clock::now();
        for (int iter = 0; iter < iters; iter++) {
            auto _ = sw.findAlignment(query, reference);
        }
        auto end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = end - start;
        nums[run] = elapsed.count() * 1000 / iters; // ms per iteration
    }

    double mean = 0.0;
    for (double num : nums) {
        mean += num;
    }
    mean /= runs;

    double variance = 0.0;
    for (double num : nums) {
        variance += (num - mean) * (num - mean);
    }
    variance /= runs;
    double sd = std::sqrt(variance);

    std::cout << "Mean: " << mean << " ms, SD: " << sd << " ms" << std::endl;
    END_TEST
}

// ==================== Main Test Runner ====================

int main() {
    std::cout << "============================================" << std::endl;
    std::cout << "Running Smith-Waterman Tests" << std::endl;
    std::cout << "============================================" << std::endl << std::endl;
    
    std::cout << "=== Basic Functionality Tests ===" << std::endl;
    test_perfect_match();
    test_no_match();
    test_partial_match();
    test_gap_in_query();
    test_gap_in_reference();
    
    std::cout << "\n=== Edge Cases ===" << std::endl;
    test_empty_query();
    test_empty_reference();
    test_both_empty();
    test_single_character_match();
    test_single_character_mismatch();
    test_query_much_longer();
    test_reference_much_longer();
    
    std::cout << "\n=== Matrix Construction Tests ===" << std::endl;
    test_matrix_dimensions();
    test_matrix_first_row_column_zeros();
    test_matrix_non_negative_values();
    test_find_highest_score_simple();
    test_find_highest_score_zero_matrix();
    
    std::cout << "\n=== Different Scoring Schemes ===" << std::endl;
    test_high_gap_penalty();
    test_negative_match_score();
    
    std::cout << "\n=== Special Character Tests ===" << std::endl;
    test_lowercase_sequences();
    test_mixed_case_sequences();
    test_numeric_characters();
    test_special_characters();
    
    std::cout << "\n=== Repetitive Patterns ===" << std::endl;
    test_repeated_characters();
    test_tandem_repeats();
    
    std::cout << "\n=== Alignment Properties ===" << std::endl;
    test_alignment_lengths_equal();
    test_no_double_gaps();
    
    std::cout << "\n=== Biological Sequences ===" << std::endl;
    test_realistic_dna_sequences();
    test_dna_with_single_mutation();
    
    std::cout << "\n=== Performance Tests ===" << std::endl;
    test_performance_medium_sequences();
    test_large_sequences_from_file();
    test_performance();
    
    std::cout << "\n============================================" << std::endl;
    std::cout << "Test Summary:" << std::endl;
    std::cout << "  Passed: " << tests_passed << std::endl;
    std::cout << "  Failed: " << tests_failed << std::endl;
    std::cout << "  Total:  " << (tests_passed + tests_failed) << std::endl;
    std::cout << "============================================" << std::endl;
    
    return tests_failed > 0 ? 1 : 0;
}