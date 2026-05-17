// Parallel Smith-Waterman (deterministic), using anti-diagonal wavefront and std::thread scoped workers
// Public API matches the sequential version. For small inputs or single-core, falls back to sequential.

use std::cmp::max;
use std::thread;

pub struct SmithWaterman {
    match_score: i32,
    mismatch_score: i32,
    gap_score: i32,
}

#[derive(Debug, Clone)]
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

    fn construct_matrix_sequential(&self, query: &str, reference: &str) -> Vec<Vec<i32>> {
        let n = query.len() + 1;
        let m = reference.len() + 1;

        let mut h = vec![vec![0; m]; n];

        if n == 0 || m == 0 {
            return h;
        }

        let query_chars: Vec<char> = query.chars().collect();
        let reference_chars: Vec<char> = reference.chars().collect();

        for i in 1..n {
            for j in 1..m {
                let score_diagonal = h[i - 1][j - 1]
                    + if query_chars[i - 1] == reference_chars[j - 1] {
                        self.match_score
                    } else {
                        self.mismatch_score
                    };

                let score_up = h[i - 1][j] + self.gap_score;
                let score_left = h[i][j - 1] + self.gap_score;

                h[i][j] = 0.max(score_diagonal.max(score_up.max(score_left)));
            }
        }

        h
    }

    pub fn construct_matrix(&self, query: &str, reference: &str) -> Vec<Vec<i32>> {
        let n = query.len() + 1;
        let m = reference.len() + 1;

        let total = n.saturating_mul(m);
        let threads = std::thread::available_parallelism().map(|nz| nz.get()).unwrap_or(4);
        let min_work_for_parallel: usize = 1_000_000; // raise threshold to avoid overhead on moderate sizes

        if threads <= 1 || total < min_work_for_parallel || n <= 1 || m <= 1 {
            return self.construct_matrix_sequential(query, reference);
        }

        let query_chars: Vec<char> = query.chars().collect();
        let reference_chars: Vec<char> = reference.chars().collect();

        // Matrix initialized with zeros
        let mut h = vec![vec![0_i32; m]; n];

        // Process anti-diagonals k = 2..=(n-1 + m-1)
        let first_k = 2_usize;
        let last_k = (n - 1) + (m - 1);

        for k in first_k..=last_k {
            // Determine range of i for this diagonal
            let i_start = 1.max(k.saturating_sub(m - 1));
            let i_end = (n - 1).min(k - 1);
            if i_start > i_end {
                continue;
            }

            // Prepare indices in deterministic order (increasing i)
            let mut diag_indices: Vec<(usize, usize)> = Vec::with_capacity(i_end - i_start + 1);
            for i in i_start..=i_end {
                let j = k - i;
                if j >= 1 && j <= m - 1 {
                    diag_indices.push((i, j));
                }
            }
            if diag_indices.is_empty() {
                continue;
            }

            let work_len = diag_indices.len();
            let used_threads = threads.min(work_len);
            let chunk_size = (work_len + used_threads - 1) / used_threads;

            let mut results: Vec<(usize, i32)> = Vec::with_capacity(work_len);

            // Scoped threads so we can borrow h/query/reference immutably
            thread::scope(|s| {
                let h_ref: &Vec<Vec<i32>> = &h; // read-only during this diagonal
                let q_ref: &Vec<char> = &query_chars;
                let r_ref: &Vec<char> = &reference_chars;
                let mut handles = Vec::with_capacity(used_threads);
                for t in 0..used_threads {
                    let start = t * chunk_size;
                    if start >= work_len {
                        break;
                    }
                    let end = ((t + 1) * chunk_size).min(work_len);
                    let slice = &diag_indices[start..end];
                    let handle = s.spawn(move || -> Vec<(usize, i32)> {
                        let mut local: Vec<(usize, i32)> = Vec::with_capacity(slice.len());
                        for (offset, &(i, j)) in slice.iter().enumerate() {
                            let pos = start + offset; // position within diagonal
                            let diagonal_score = h_ref[i - 1][j - 1]
                                + if q_ref[i - 1] == r_ref[j - 1] {
                                    self.match_score
                                } else {
                                    self.mismatch_score
                                };
                            let up_score = h_ref[i - 1][j] + self.gap_score;
                            let left_score = h_ref[i][j - 1] + self.gap_score;
                            let val = 0.max(max(diagonal_score, max(up_score, left_score)));
                            local.push((pos, val));
                        }
                        local
                    });
                    handles.push(handle);
                }
                for handle in handles {
                    let mut part = handle.join().expect("thread panicked");
                    results.append(&mut part);
                }
            });

            // Place results in deterministic order (by position within diagonal)
            results.sort_by_key(|&(pos, _)| pos);
            for (idx_in_diag, &(_, val)) in results.iter().enumerate() {
                let (i, j) = diag_indices[idx_in_diag];
                h[i][j] = val;
            }
        }

        h
    }

    pub fn find_highest_score(&self, h: &[Vec<i32>]) -> (usize, usize) {
        let mut max_score = 0;
        let mut max_pos = (0, 0);

        for (i, row) in h.iter().enumerate() {
            for (j, &val) in row.iter().enumerate() {
                if val > max_score {
                    max_score = val;
                    max_pos = (i, j);
                }
            }
        }

        max_pos
    }

    pub fn traceback(&self, h: &[Vec<i32>], query: &str, reference: &str) -> AlignmentResult {
        let mut aligned_a = String::new();
        let mut aligned_b = String::new();

        let (mut i, mut j) = self.find_highest_score(h);
        let score = h[i][j];

        let mut total_match = 0;
        let mut total_alignment = 0;

        let query_chars: Vec<char> = query.chars().collect();
        let reference_chars: Vec<char> = reference.chars().collect();

        while i > 0 && j > 0 {
            let current_score = h[i][j];

            if current_score == 0 {
                break;
            }

            let diagonal_score = h[i - 1][j - 1];
            let up_score = h[i - 1][j];
            let left_score = h[i][j - 1];

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

                if query_chars[i - 1] == reference_chars[j - 1] {
                    total_match += 1;
                }
                i -= 1;
                j -= 1;
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

        let percentage_identity = if total_alignment > 0 {
            (total_match as f64 / total_alignment as f64) * 100.0
        } else {
            0.0
        };

        AlignmentResult {
            aligned_a,
            aligned_b,
            score,
            identity: percentage_identity,
        }
    }

    pub fn find_alignment(&self, query: &str, reference: &str) -> AlignmentResult {
        let h = self.construct_matrix(query, reference);
        self.traceback(&h, query, reference)
    }
}
