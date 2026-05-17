#!/bin/bash

# Create temporary Cargo project
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# Create Cargo.toml
cat > Cargo.toml << 'EOF'
[package]
name = "smith_waterman_test"
version = "0.1.0"
edition = "2021"

[dependencies]
rayon = "1.7"
sha2 = "0.10"
EOF

# Copy source files
cp "$OLDPWD/algo_sequential.rs" src/
cp "$OLDPWD/algo_parallel.rs" src/
cp "$OLDPWD/main.rs" src/

# Create src directory
mkdir -p src

# Move files to src
mv algo_sequential.rs src/ 2>/dev/null || true
mv algo_parallel.rs src/ 2>/dev/null || true
mv main.rs src/ 2>/dev/null || true

# Build and run
cargo run --release 2>&1

# Capture exit code
EXIT_CODE=$?

# Cleanup
cd "$OLDPWD"
rm -rf "$TEMP_DIR"

exit $EXIT_CODE
