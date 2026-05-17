use std::fmt::Display;
use std::io::Write;

pub(crate) struct Joiner<'a, 'b, T: Display> {
    sep: &'a str,
    list: &'b[T]
}

impl <'a, 'b, T: Display> Joiner<'a,'b, T> {
    pub(crate) fn new(sep: &'a str, list: &'b[T]) -> Joiner<'a, 'b, T> {
        Joiner { sep, list }
    }
}

impl<'a, 'b, T: Display> Display for Joiner<'a, 'b, T> {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        let mut iter = self.list.iter();
        if let Some(first) = iter.next() {
            write!(f, "{}", first)?;
            for item in iter {
                write!(f, "{}{}", self.sep, item)?;
            }
        }
        Ok(())
    }
}

fn unordered_bfs_data() {
    let seed = 42;
    let mut graph = Graph::new();
    let mut rng = StdRng::seed_from_u64(seed);
    
    let num_nodes = 10;
    
    for from in 1..=num_nodes {
        let mut neighbors: Vec<i32> = (1..=num_nodes).filter(|&to| to != from).collect();

        neighbors.shuffle(&mut rng);
        
        for to in neighbors {
            graph.add_edge(from, to);
        }
    }
    let mut result = Bfs::run(&graph, 1);

    // write the result to a file for use in the test, result is a vector of node ids in BFS order
    // join array with ,
    let mut file = std::fs::File::create("unordered_bfs_data.txt").unwrap();
    write!(file, "{}", Joiner::new(",", &result));
}