mod smith_waterman;
mod tests;

use smith_waterman::SmithWaterman;

fn main() {
    let args: Vec<String> = std::env::args().collect();

    // If "test" argument is passed, run tests
    if args.len() > 1 && args[1] == "test" {
        println!("Running tests...\n");
        tests::run_all_tests();
        std::process::exit(if tests::get_failed_count() > 0 { 1 } else { 0 });
    }

    // Otherwise, run the main application
    println!("Running Smith-Waterman Alignment\n");

    let seq_a = "AGCTGTA";
    let seq_b = "GCTAGTA";

    let sw = SmithWaterman::new(2, -1, -2);
    let result = sw.find_alignment(seq_a, seq_b);

    println!("Sequence A: {}", result.aligned_a);
    println!("Sequence B: {}", result.aligned_b);
    println!("Alignment score: {}", result.score);
    println!("Identity: {}%", result.identity);
}