#!/bin/bash
# Build script for GEMM parallel implementation

# Check if we're in a Cargo project
if [ ! -f "Cargo.toml" ]; then
    echo "Creating Cargo.toml..."
    cat > Cargo.toml << 'EOF'
[package]
name = "gemm_parallel"
version = "0.1.0"
edition = "2021"

[dependencies]

[[bin]]
name = "run_gemm"
path = "main.rs"
EOF
fi

# Build and run
cargo run --release
