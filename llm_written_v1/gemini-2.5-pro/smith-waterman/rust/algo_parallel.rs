use rayon::prelude::*;
use std::sync::Arc;

pub struct SmithWaterman {
    match_score: i32,
    mismatch_score: i32,
    gap_score: i32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct AlignmentResult {
    pub aligned_a: String,
    pub aligned_b: String,
    pub score: i32,
    pub identity: f64,
}

impl SmithWaterman {
    pub fn new(match_score: i32, mismatch_score: i32, gap_score: i32) -> Self {
        SmithWaterman {
            match_score,
            mismatch_score,
            gap_score,
        }
    }

    pub fn construct_matrix_parallel(&self, query: &str, reference: &str) -> (Vec<i32>, usize, usize) {
        let n = query.len() + 1;
        let m = reference.len() + 1;

        if n < 20 || m < 20 { // Fallback for small inputs where parallelism has too much overhead
            return self.construct_matrix_sequential(query, reference);
        }

        let mut h = vec![0; n * m];
        let h_ptr_addr = h.as_mut_ptr() as usize;

        let query_chars = Arc::new(query.chars().collect::<Vec<char>>());
        let reference_chars = Arc::new(reference.chars().collect::<Vec<char>>());

        for k in 2..(n + m - 1) {
            // Clone the Arcs for each iteration of the outer loop.
            // This is cheap (just bumps a reference count) and gives ownership
            // to the `move` closure for the parallel operations.
            let qc = Arc::clone(&query_chars);
            let rc = Arc::clone(&reference_chars);

            (1..k).into_par_iter().for_each(move |i| {
                let j = k - i;
                if i < n && j < m {
                    let h = h_ptr_addr as *mut i32;
                    unsafe {
                        let score_diagonal = *h.add((i - 1) * m + (j - 1))
                            + if qc[i - 1] == rc[j - 1] {
                                self.match_score
                            } else {
                                self.mismatch_score
                            };

                        let score_up = *h.add((i - 1) * m + j) + self.gap_score;
                        let score_left = *h.add(i * m + (j - 1)) + self.gap_score;
                        
                        *h.add(i * m + j) = 0.max(score_diagonal.max(score_up.max(score_left)));
                    }
                }
            });
        }
        
        (h, n, m)
    }
    
    pub fn find_highest_score_parallel(&self, h: &[i32], m: usize) -> (usize, usize) {
        if h.is_empty() {
            return (0, 0);
        }

        let result = h.par_chunks(m)
            .enumerate()
            .map(|(i, row)| {
                let (j, &max_val) = row
                    .iter()
                    .enumerate()
                    .max_by_key(|&(_, &val)| val)
                    .unwrap_or((0, &0));
                (max_val, i, j)
            })
            .reduce(
                || (i32::MIN, 0, 0),
                |a, b| if a.0 >= b.0 { a } else { b },
            );
        
        (result.1, result.2)
    }

    pub fn construct_matrix_sequential(&self, query: &str, reference: &str) -> (Vec<i32>, usize, usize) {
        let n = query.len() + 1;
        let m = reference.len() + 1;
        let mut h = vec![0; n * m];
        let query_chars: Vec<char> = query.chars().collect();
        let reference_chars: Vec<char> = reference.chars().collect();

        for i in 1..n {
            for j in 1..m {
                let score_diagonal = h[(i - 1) * m + (j - 1)]
                    + if query_chars[i - 1] == reference_chars[j - 1] {
                        self.match_score
                    } else {
                        self.mismatch_score
                    };
                let score_up = h[(i - 1) * m + j] + self.gap_score;
                let score_left = h[i * m + (j - 1)] + self.gap_score;
                h[i * m + j] = 0.max(score_diagonal.max(score_up.max(score_left)));
            }
        }
        (h, n, m)
    }
    
    pub fn find_highest_score_sequential(&self, h: &[i32], n: usize, m: usize) -> (usize, usize) {
        let mut max_score = 0;
        let mut max_pos = (0, 0);
        for i in 0..n {
            for j in 0..m {
                let score = h[i * m + j];
                if score > max_score {
                    max_score = score;
                    max_pos = (i, j);
                }
            }
        }
        max_pos
    }

    pub fn traceback(&self, h: &[i32], m: usize, query: &str, reference: &str, start_pos: (usize, usize)) -> AlignmentResult {
        let mut aligned_a = String::new();
        let mut aligned_b = String::new();

        let (mut i, mut j) = start_pos;
        let score = h[i * m + j];

        let mut total_match = 0;
        let mut total_alignment = 0;

        let query_chars: Vec<char> = query.chars().collect();
        let reference_chars: Vec<char> = reference.chars().collect();

        while i > 0 && j > 0 {
            let current_score = h[i * m + j];
            if current_score == 0 { break; }

            let diagonal_score = h[(i - 1) * m + (j - 1)];
            let up_score = h[(i - 1) * m + j];
            let left_score = h[i * m + (j - 1)];

            let expected_diagonal = diagonal_score
                + if query_chars[i - 1] == reference_chars[j - 1] {
                    self.match_score
                } else {
                    self.mismatch_score
                };

            if current_score == expected_diagonal {
                aligned_a.push(query_chars[i - 1]);
                aligned_b.push(reference_chars[j - 1]);
                total_alignment += 1;
                if query_chars[i - 1] == reference_chars[j - 1] { total_match += 1; }
                i -= 1; j -= 1;
            } else if current_score == up_score + self.gap_score {
                aligned_a.push(query_chars[i - 1]);
                aligned_b.push('-');
                total_alignment += 1;
                i -= 1;
            } else if current_score == left_score + self.gap_score {
                aligned_a.push('-');
                aligned_b.push(reference_chars[j - 1]);
                total_alignment += 1;
                j -= 1;
            } else {
                break;
            }
        }

        aligned_a = aligned_a.chars().rev().collect();
        aligned_b = aligned_b.chars().rev().collect();

        let identity = if total_alignment > 0 {
            (total_match as f64 / total_alignment as f64) * 100.0
        } else { 0.0 };

        AlignmentResult { aligned_a, aligned_b, score, identity }
    }

    pub fn find_alignment_parallel(&self, query: &str, reference: &str) -> AlignmentResult {
        let (h, _n, m) = self.construct_matrix_parallel(query, reference);
        let max_pos = self.find_highest_score_parallel(&h, m);
        self.traceback(&h, m, query, reference, max_pos)
    }
    
    pub fn find_alignment_sequential(&self, query: &str, reference: &str) -> AlignmentResult {
        let (h, n, m) = self.construct_matrix_sequential(query, reference);
        let max_pos = self.find_highest_score_sequential(&h, n, m);
        self.traceback(&h, m, query, reference, max_pos)
    }
}
