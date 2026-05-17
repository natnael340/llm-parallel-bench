#!/bin/bash

# Compile if needed
if [ ! -f "TestGemm.class" ]; then
    javac Gemm.java GemmParallel.java TestGemm.java
fi

# Run all tests
java TestGemm all
