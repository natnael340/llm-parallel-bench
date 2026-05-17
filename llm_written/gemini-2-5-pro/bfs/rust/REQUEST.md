use std::collections::{HashMap, HashSet, VecDeque};

pub struct Graph {
    vertices: HashMap<i32, Vec<i32>>,
}

impl Graph {
    pub fn new() -> Self {
        Graph {
            vertices: HashMap::new(),
        }
    }

    pub fn add_edge(&mut self, from_vertex: i32, to_vertex: i32) {
        self.vertices.entry(from_vertex).or_insert_with(Vec::new);
        self.vertices.entry(to_vertex).or_insert_with(Vec::new);

        self.vertices.get_mut(&from_vertex).unwrap().push(to_vertex);
        self.vertices.get_mut(&to_vertex).unwrap().push(from_vertex);
    }

    pub fn vertices(&self) -> &HashMap<i32, Vec<i32>> {
        &self.vertices
    }
}

impl Default for Graph {
    fn default() -> Self {
        Self::new()
    }
}

pub struct Bfs;

impl Bfs {
    pub fn run(graph: &Graph, start_vertex: i32) -> Vec<i32> {
        if !graph.vertices().contains_key(&start_vertex) {
            return Vec::new();
        }

        let mut visited = HashSet::new();
        let mut result = Vec::new();
        let mut queue = VecDeque::new();

        queue.push_back(start_vertex);

        while let Some(current) = queue.pop_front() {
            if !visited.contains(&current) {
                visited.insert(current);
                result.push(current);

                if let Some(neighbors) = graph.vertices().get(&current) {
                    for &neighbor in neighbors {
                        if !visited.contains(&neighbor) {
                            queue.push_back(neighbor);
                        }
                    }
                }
            }
        }

        result
    }
}
