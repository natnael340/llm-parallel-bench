use sha2::{Sha256, Digest};
use std::time::Instant;
use std::fmt::Write as FmtWrite;

mod algo_sequential;
mod algo_parallel;

use algo_sequential::SmithWaterman as SeqSW;
use algo_parallel::SmithWaterman as ParSW;

fn hash_result(result: &algo_parallel::AlignmentResult) -> String {
    let mut hasher = Sha256::new();
    hasher.update(result.aligned_a.as_bytes());
    hasher.update(result.aligned_b.as_bytes());
    hasher.update(&result.score.to_le_bytes());
    hasher.update(&result.identity.to_le_bytes());
    format!("{:x}", hasher.finalize())
}

fn hash_result_seq(result: &algo_sequential::AlignmentResult) -> String {
    let mut hasher = Sha256::new();
    hasher.update(result.aligned_a.as_bytes());
    hasher.update(result.aligned_b.as_bytes());
    hasher.update(&result.score.to_le_bytes());
    hasher.update(&result.identity.to_le_bytes());
    format!("{:x}", hasher.finalize())
}

fn generate_sequence(len: usize, seed: u64) -> String {
    let bases = ['A', 'C', 'G', 'T'];
    let mut rng = seed;
    (0..len)
        .map(|_| {
            rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
            bases[(rng % 4) as usize]
        })
        .collect()
}

struct TestCase {
    name: &'static str,
    query: String,
    reference: String,
}

fn run_test(test: &TestCase, match_score: i32, mismatch_score: i32, gap_score: i32) -> Result<(), String> {
    println!("\n=== Test: {} ===", test.name);
    println!("Query length: {}, Reference length: {}", test.query.len(), test.reference.len());
    
    // Sequential
    let seq_sw = SeqSW::new(match_score, mismatch_score, gap_score);
    let seq_start = Instant::now();
    let seq_result = seq_sw.find_alignment(&test.query, &test.reference);
    let seq_duration = seq_start.elapsed();
    let seq_hash = hash_result_seq(&seq_result);
    
    println!("Sequential:");
    println!("  Time: {:.6}s", seq_duration.as_secs_f64());
    println!("  Score: {}, Identity: {:.2}%", seq_result.score, seq_result.identity);
    println!("  Hash: {}", seq_hash);
    
    // Parallel Run 1
    let par_sw = ParSW::new(match_score, mismatch_score, gap_score);
    let par_start = Instant::now();
    let par_result1 = par_sw.find_alignment(&test.query, &test.reference);
    let par_duration1 = par_start.elapsed();
    let par_hash1 = hash_result(&par_result1);
    
    println!("Parallel Run 1:");
    println!("  Time: {:.6}s", par_duration1.as_secs_f64());
    println!("  Score: {}, Identity: {:.2}%", par_result1.score, par_result1.identity);
    println!("  Hash: {}", par_hash1);
    
    // Parallel Run 2 (determinism check)
    let par_start2 = Instant::now();
    let par_result2 = par_sw.find_alignment(&test.query, &test.reference);
    let par_duration2 = par_start2.elapsed();
    let par_hash2 = hash_result(&par_result2);
    
    println!("Parallel Run 2:");
    println!("  Time: {:.6}s", par_duration2.as_secs_f64());
    println!("  Score: {}, Identity: {:.2}%", par_result2.score, par_result2.identity);
    println!("  Hash: {}", par_hash2);
    
    // Correctness check
    if seq_result.aligned_a != par_result1.aligned_a 
        || seq_result.aligned_b != par_result1.aligned_b
        || seq_result.score != par_result1.score {
        return Err(format!("FAIL: Output mismatch between sequential and parallel"));
    }
    
    // Determinism check
    if par_hash1 != par_hash2 {
        return Err(format!("FAIL: Parallel runs produced different results (hash mismatch)"));
    }
    
    // Speedup
    let speedup = seq_duration.as_secs_f64() / par_duration1.as_secs_f64();
    println!("  Speedup: {:.2}x", speedup);
    
    println!("PASS ✓");
    Ok(())
}

fn main() {
    println!("Smith-Waterman Parallel Differential Test Suite");
    println!("================================================\n");
    
    let match_score = 2;
    let mismatch_score = -1;
    let gap_score = -1;
    
    let mut tests = Vec::new();
    
    // Edge case: empty
    tests.push(TestCase {
        name: "Edge: Empty sequences",
        query: String::new(),
        reference: String::new(),
    });
    
    // Edge case: single char
    tests.push(TestCase {
        name: "Edge: Single character",
        query: "A".to_string(),
        reference: "A".to_string(),
    });
    
    // Edge case: no match
    tests.push(TestCase {
        name: "Edge: No match",
        query: "AAAA".to_string(),
        reference: "TTTT".to_string(),
    });
    
    // Small
    tests.push(TestCase {
        name: "Small: 20x20",
        query: "ACGTACGTACGTACGTACGT".to_string(),
        reference: "ACGTACGTACGTACGTACGT".to_string(),
    });
    
    // Medium
    tests.push(TestCase {
        name: "Medium: 100x100",
        query: generate_sequence(100, 12345),
        reference: generate_sequence(100, 54321),
    });
    
    // Medium-Large
    tests.push(TestCase {
        name: "Medium-Large: 500x500",
        query: generate_sequence(500, 99999),
        reference: generate_sequence(500, 11111),
    });
    
    // Large
    tests.push(TestCase {
        name: "Large: 1000x1000",
        query: generate_sequence(1000, 777777),
        reference: generate_sequence(1000, 888888),
    });
    
    let mut passed = 0;
    let mut failed = 0;
    let mut failure_messages = Vec::new();
    
    for test in &tests {
        match run_test(test, match_score, mismatch_score, gap_score) {
            Ok(_) => passed += 1,
            Err(e) => {
                failed += 1;
                failure_messages.push(format!("{}: {}", test.name, e));
            }
        }
    }
    
    println!("\n================================================");
    println!("Test Summary: {} passed, {} failed", passed, failed);
    
    if !failure_messages.is_empty() {
        println!("\nFailures:");
        for msg in &failure_messages {
            println!("  - {}", msg);
        }
        std::process::exit(1);
    } else {
        println!("All tests passed! ✓");
        std::process::exit(0);
    }
}
