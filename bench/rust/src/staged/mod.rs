// Placeholder so `pub mod staged;` in lib.rs resolves on a fresh clone.
//
// bench/recipes/rust.py:stage() overwrites this file on every run with the
// real module list for the staged implementation, so the working copy will
// differ from the committed version after any benchmark run. Only `cargo
// build --lib`, `cargo check` and rust-analyzer see this version; the bin
// targets need the generated one and are always built after staging.
