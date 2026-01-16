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

    pub fn construct_matrix(&self, query: &str, reference: &str) -> Vec<Vec<i32>> {
        let n = query.len() + 1;
        let m = reference.len() + 1;

        // Initialize matrix with zeros
        let mut h = vec![vec![0; m]; n];

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

        // Reverse the strings
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
