"""
Comprehensive test suite for CodeRunner.

Tests cover:
- All supported languages (Python, Go, C++, C#, Java, Rust)
- Success cases
- Error cases (missing files, validation errors, timeouts, etc.)
- Edge cases
- Configuration options
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Import the module under test
# Adjust import based on your actual module name
from app.tools import run_code, configure_runner, get_runner
from app._utils import (
    CodeRunner,
    PythonHandler,
    GoHandler,
    CppHandler,
    CSharpHandler,
    JavaHandler,
    RustHandler,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace for tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def runner(temp_workspace):
    """Create a CodeRunner instance with temp workspace."""
    return CodeRunner(base_dir=temp_workspace, timeout_sec=5)


@pytest.fixture
def python_script(temp_workspace):
    """Create a simple Python script."""
    script = temp_workspace / "test_script.py"
    script.write_text("print('Hello from Python!')")
    return script


@pytest.fixture
def python_error_script(temp_workspace):
    """Create a Python script that raises an error."""
    script = temp_workspace / "error_script.py"
    script.write_text("raise ValueError('Test error')")
    return script


@pytest.fixture
def python_timeout_script(temp_workspace):
    """Create a Python script that times out."""
    script = temp_workspace / "timeout_script.py"
    script.write_text("""
import time
time.sleep(10)
print('This should not print')
""")
    return script


@pytest.fixture
def go_files(temp_workspace):
    """Create Go source files."""
    # Create go.mod
    go_mod = temp_workspace / "go.mod"
    go_mod.write_text("module testapp\n\ngo 1.21\n")
    
    # Main file
    main_go = temp_workspace / "main.go"
    main_go.write_text("""
package main

import "fmt"

func main() {
    fmt.Println("Hello from Go!")
    fmt.Println(GetMessage())
}
""")
    
    # Utils file
    utils_go = temp_workspace / "utils.go"
    utils_go.write_text("""
package main

func GetMessage() string {
    return "Utils message"
}
""")
    
    return [main_go, utils_go]


@pytest.fixture
def cpp_source(temp_workspace):
    """Create a C++ source file."""
    source = temp_workspace / "test.cpp"
    source.write_text("""
#include <iostream>
int main() {
    std::cout << "Hello from C++!" << std::endl;
    return 0;
}
""")
    return source


@pytest.fixture
def cpp_binary(temp_workspace, cpp_source):
    """Compile and return a C++ binary."""
    import subprocess
    
    binary = temp_workspace / "test_program"
    
    try:
        # Compile
        result = subprocess.run(
            ["g++", str(cpp_source), "-o", str(binary)],
            cwd=str(temp_workspace),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and binary.exists():
            # Make executable
            binary.chmod(binary.stat().st_mode | 0o111)
            return binary
        else:
            pytest.skip(f"C++ compilation failed: {result.stderr}")
    except FileNotFoundError:
        pytest.skip("g++ compiler not found")
    except Exception as e:
        pytest.skip(f"C++ setup failed: {e}")


@pytest.fixture
def csharp_project(temp_workspace):
    """Create a C# project structure."""
    # Create .setup directory
    setup_dir = temp_workspace / ".setup"
    setup_dir.mkdir()
    
    # Create project file
    csproj = setup_dir / "llm_written.csproj"
    csproj.write_text("""
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="../*.cs" />
  </ItemGroup>
</Project>
""")
    
    # Create C# source file
    program_cs = temp_workspace / "Program.cs"
    program_cs.write_text("""
using System;

class Program {
    static void Main() {
        Console.WriteLine("Hello from C#!");
    }
}
""")
    
    return {"project": csproj, "source": program_cs}


# ============================================================================
# Python Tests
# ============================================================================

class TestPython:
    """Test Python code execution."""
    
    def test_python_success(self, runner, python_script):
        """Test successful Python execution."""
        result = runner.run([python_script.name], "python")
        
        assert result["status"] == "successful"
        assert result["returncode"] == 0
        assert "Hello from Python!" in result["stdout"]
        assert result["stderr"] == ""
        assert result["duration_sec"] > 0
        assert result["cmd"] == [sys.executable, str(python_script)]
        assert len(result["paths"]) == 1
    
    def test_python_error(self, runner, python_error_script):
        """Test Python script with runtime error."""
        result = runner.run([python_error_script.name], "python")
        
        assert result["status"] == "error"
        assert result["returncode"] != 0
        assert "ValueError" in result["stderr"]
        assert "Test error" in result["stderr"]
    
    def test_python_timeout(self, runner, python_timeout_script):
        """Test Python script timeout."""
        result = runner.run([python_timeout_script.name], "python")
        
        assert result["status"] == "error"
        assert result["returncode"] is None
        assert "Timeout" in result["stderr"]
        assert result["duration_sec"] >= 5  # Should timeout at 5 seconds
        assert "note" in result and result["note"] == "Process timed out"
    
    def test_python_missing_file(self, runner):
        """Test Python with non-existent file."""
        result = runner.run(["nonexistent.py"], "python")
        
        assert result["status"] == "error"
        assert "not found" in result["stderr"]
        assert result["returncode"] is None
    
    def test_python_multiple_files_rejected(self, runner, python_script, temp_workspace):
        """Test that Python rejects multiple files."""
        script2 = temp_workspace / "script2.py"
        script2.write_text("print('Script 2')")
        
        result = runner.run([python_script.name, script2.name], "python")
        
        assert result["status"] == "error"
        assert "exactly 1 file" in result["stderr"]
        assert "got 2" in result["stderr"]
    
    def test_python_empty_filenames(self, runner):
        """Test Python with no files provided."""
        result = runner.run([], "python")
        
        assert result["status"] == "error"
        assert "No filename provided" in result["stderr"]
    
    def test_python_directory_not_file(self, runner, temp_workspace):
        """Test Python with directory instead of file."""
        test_dir = temp_workspace / "testdir"
        test_dir.mkdir()
        
        result = runner.run(["testdir"], "python")
        
        assert result["status"] == "error"
        assert "not a file" in result["stderr"]
    
    def test_python_output_with_stderr(self, runner, temp_workspace):
        """Test Python script that writes to both stdout and stderr."""
        script = temp_workspace / "mixed_output.py"
        script.write_text("""
import sys
print("Standard output")
print("Error output", file=sys.stderr)
""")
        
        result = runner.run([script.name], "python")
        
        assert result["status"] == "successful"
        assert "Standard output" in result["stdout"]
        assert "Error output" in result["stderr"]


# ============================================================================
# Go Tests
# ============================================================================

class TestGo:
    """Test Go code execution."""
    
    def test_go_single_file(self, runner, temp_workspace):
        """Test Go execution with single file."""
        # Create go.mod
        go_mod = temp_workspace / "go.mod"
        go_mod.write_text("module testapp\n\ngo 1.21\n")
        
        # Create main.go
        main_go = temp_workspace / "main.go"
        main_go.write_text("""
package main
import "fmt"
func main() {
    fmt.Println("Hello from Go!")
}
""")
        
        # Check if Go is available
        import subprocess
        try:
            subprocess.run(["go", "version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("Go compiler not found")
        
        result = runner.run([main_go.name], "go")
        
        assert result["status"] == "successful"
        assert "Hello from Go!" in result["stdout"]
        assert result["returncode"] == 0
    
    def test_go_multiple_files(self, runner, go_files):
        """Test Go execution with multiple files."""
        # Check if Go is available
        import subprocess
        try:
            subprocess.run(["go", "version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("Go compiler not found")
        
        filenames = [f.name for f in go_files]
        result = runner.run(filenames, "go")
        
        assert result["status"] == "successful"
        assert "Hello from Go!" in result["stdout"]
        assert "Utils message" in result["stdout"]
    
    def test_go_missing_file(self, runner):
        """Test Go with non-existent file."""
        result = runner.run(["missing.go"], "go")
        
        assert result["status"] == "error"
        assert "not found" in result["stderr"]
    
    def test_go_compilation_error(self, runner, temp_workspace):
        """Test Go with compilation error."""
        # Check if Go is available
        import subprocess
        try:
            subprocess.run(["go", "version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("Go compiler not found")
        
        # Create go.mod
        go_mod = temp_workspace / "go.mod"
        go_mod.write_text("module testapp\n\ngo 1.21\n")
        
        # Create invalid Go file
        bad_go = temp_workspace / "bad.go"
        bad_go.write_text("""
package main
func main() {
    // Missing closing brace
""")
        
        result = runner.run([bad_go.name], "go")
        
        assert result["status"] == "error"
        assert result["returncode"] != 0


# ============================================================================
# C++ Tests
# ============================================================================

class TestCpp:
    """Test C++ binary execution."""
    
    def test_cpp_success(self, runner, cpp_binary):
        """Test successful C++ binary execution."""
        result = runner.run([cpp_binary.name], "cpp")
        
        assert result["status"] == "successful"
        assert "Hello from C++!" in result["stdout"]
        assert result["returncode"] == 0
    
    def test_cpp_missing_binary(self, runner):
        """Test C++ with non-existent binary."""
        result = runner.run(["nonexistent_binary"], "cpp")
        
        assert result["status"] == "error"
        assert "not found" in result["stderr"]
    
    def test_cpp_multiple_files_rejected(self, runner, cpp_binary, temp_workspace):
        """Test that C++ rejects multiple binaries."""
        binary2 = temp_workspace / "binary2"
        binary2.touch()
        
        result = runner.run([cpp_binary.name, binary2.name], "cpp")
        
        assert result["status"] == "error"
        assert "exactly 1 file" in result["stderr"]
    
    def test_cpp_directory_not_file(self, runner, temp_workspace):
        """Test C++ with directory instead of binary."""
        test_dir = temp_workspace / "testdir"
        test_dir.mkdir()
        
        result = runner.run(["testdir"], "cpp")
        
        assert result["status"] == "error"
        assert "not a file" in result["stderr"]
    
    def test_cpp_non_executable_made_executable(self, runner, temp_workspace):
        """Test that C++ binary is made executable."""
        # Create a non-executable file
        binary = temp_workspace / "test_binary"
        binary.write_text("#!/bin/sh\necho 'Test'")
        
        # Ensure it's not executable
        binary.chmod(0o644)
        
        # Try to run it - should make it executable
        result = runner.run([binary.name], "cpp")
        
        # The chmod should have been called
        assert binary.stat().st_mode & 0o111  # Has execute permission


# ============================================================================
# C# Tests
# ============================================================================

class TestCSharp:
    """Test C# code execution."""
    
    def test_csharp_success(self, runner, csharp_project):
        """Test successful C# execution."""
        # Check if dotnet is available
        import subprocess
        try:
            subprocess.run(["dotnet", "--version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("dotnet runtime not found")
        
        runner_with_timeout = CodeRunner(base_dir=runner.base_dir, timeout_sec=60)
        result = runner_with_timeout.run([csharp_project["source"].name], "csharp")
        
        assert result["status"] == "successful"
        assert "Hello from C#!" in result["stdout"]
        assert result["returncode"] == 0
    
    def test_csharp_missing_project(self, temp_workspace):
        """Test C# without project file."""
        # Create runner without .setup directory
        runner = CodeRunner(base_dir=temp_workspace)
        
        # Create a C# file
        cs_file = temp_workspace / "test.cs"
        cs_file.write_text("class Program { }")
        
        result = runner.run([cs_file.name], "csharp")
        
        assert result["status"] == "error"
        assert "project not found" in result["stderr"]
    
    def test_csharp_missing_source_file(self, runner, csharp_project):
        """Test C# with non-existent source file."""
        result = runner.run(["missing.cs"], "csharp")
        
        assert result["status"] == "error"
        assert "not found" in result["stderr"]
    
    def test_csharp_multiple_files(self, runner, csharp_project, temp_workspace):
        """Test C# with multiple source files."""
        # Check if dotnet is available
        import subprocess
        try:
            subprocess.run(["dotnet", "--version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("dotnet runtime not found")
        
        # Create additional source file
        utils_cs = temp_workspace / "Utils.cs"
        utils_cs.write_text("""
using System;
public class Utils {
    public static string GetMessage() {
        return "Utils message";
    }
}
""")
        
        # Update Program.cs to use Utils
        program_cs = csharp_project["source"]
        program_cs.write_text("""
using System;
class Program {
    static void Main() {
        Console.WriteLine("Hello from C#!");
        Console.WriteLine(Utils.GetMessage());
    }
}
""")
        runner_with_timeout = CodeRunner(base_dir=runner.base_dir, timeout_sec=60)
        result = runner_with_timeout.run([program_cs.name, utils_cs.name], "csharp")
        
        assert result["status"] == "successful"
        assert "Hello from C#!" in result["stdout"]
        assert "Utils message" in result["stdout"]


# ============================================================================
# Java Tests
# ============================================================================

@pytest.fixture
def java_simple_class(temp_workspace):
    """Create a simple Java class file (compiled .class)."""
    # Create source file
    source = temp_workspace / "HelloWorld.java"
    source.write_text("""
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello from Java!");
    }
}
""")

    # Compile it
    import subprocess
    try:
        result = subprocess.run(
            ["javac", str(source)],
            cwd=str(temp_workspace),
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            class_file = temp_workspace / "HelloWorld.class"
            if class_file.exists():
                return {"source": source, "class": class_file}

        pytest.skip(f"Java compilation failed: {result.stderr}")
    except FileNotFoundError:
        pytest.skip("javac compiler not found")
    except Exception as e:
        pytest.skip(f"Java setup failed: {e}")


@pytest.fixture
def java_multiple_classes(temp_workspace):
    """Create multiple Java class files."""
    # Main class
    main_source = temp_workspace / "Main.java"
    main_source.write_text("""
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello from Main!");
        Calculator calc = new Calculator();
        System.out.println("5 + 3 = " + calc.add(5, 3));
    }
}
""")

    # Helper class
    calc_source = temp_workspace / "Calculator.java"
    calc_source.write_text("""
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
""")

    # Compile both
    import subprocess
    try:
        result = subprocess.run(
            ["javac", str(main_source), str(calc_source)],
            cwd=str(temp_workspace),
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            main_class = temp_workspace / "Main.class"
            calc_class = temp_workspace / "Calculator.class"
            if main_class.exists() and calc_class.exists():
                return {
                    "main_source": main_source,
                    "calc_source": calc_source,
                    "main_class": main_class,
                    "calc_class": calc_class
                }

        pytest.skip(f"Java compilation failed: {result.stderr}")
    except FileNotFoundError:
        pytest.skip("javac compiler not found")
    except Exception as e:
        pytest.skip(f"Java setup failed: {e}")


class TestJava:
    """Test Java code execution."""

    def test_java_single_class(self, runner, java_simple_class):
        """Test successful Java execution with single class."""
        # Check if java is available
        import subprocess
        try:
            subprocess.run(["java", "-version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("java runtime not found")

        # Pass the source file name - JavaHandler will use its name for the java command
        result = runner.run([java_simple_class["source"].name], "java")

        assert result["status"] == "successful"
        assert "Hello from Java!" in result["stdout"]
        assert result["returncode"] == 0
        assert "java" in result["cmd"][0]

    def test_java_multiple_classes(self, runner, java_multiple_classes):
        """Test Java execution with multiple classes."""
        # Check if java is available
        import subprocess
        try:
            subprocess.run(["java", "-version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("java runtime not found")

        # Pass the main source file - handler will use stem for class name
        result = runner.run([java_multiple_classes["main_source"].name], "java")

        assert result["status"] == "successful"
        assert "Hello from Main!" in result["stdout"]
        assert "5 + 3 = 8" in result["stdout"]
        assert result["returncode"] == 0

    def test_java_missing_class(self, runner):
        """Test Java with non-existent class file."""
        result = runner.run(["NonExistent"], "java")

        assert result["status"] == "error"
        # Java will error when trying to find the class
        assert result["returncode"] != 0 or "not found" in result["stderr"]

    def test_java_runtime_error(self, runner, temp_workspace):
        """Test Java class with runtime error."""
        # Check if java is available
        import subprocess
        try:
            subprocess.run(["java", "-version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("java runtime not found")

        # Create a class that throws exception
        source = temp_workspace / "ErrorTest.java"
        source.write_text("""
public class ErrorTest {
    public static void main(String[] args) {
        throw new RuntimeException("Test error");
    }
}
""")

        # Compile it
        try:
            compile_result = subprocess.run(
                ["javac", str(source)],
                cwd=str(temp_workspace),
                capture_output=True,
                timeout=10
            )
            if compile_result.returncode != 0:
                pytest.skip("Failed to compile Java error test")
        except Exception as e:
            pytest.skip(f"Java compilation failed: {e}")

        # Pass the source file name
        result = runner.run([source.name], "java")

        assert result["status"] == "error"
        assert result["returncode"] != 0
        assert "RuntimeException" in result["stderr"] or "RuntimeException" in result["stdout"]

    def test_java_with_args(self, runner, temp_workspace):
        """Test Java class that uses command line arguments."""
        # Check if java is available
        import subprocess
        try:
            subprocess.run(["java", "-version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("java runtime not found")

        # Create a class that prints args
        source = temp_workspace / "ArgsTest.java"
        source.write_text("""
public class ArgsTest {
    public static void main(String[] args) {
        System.out.println("Args: " + args.length);
        for (String arg : args) {
            System.out.println("  " + arg);
        }
    }
}
""")

        # Compile it
        try:
            compile_result = subprocess.run(
                ["javac", str(source)],
                cwd=str(temp_workspace),
                capture_output=True,
                timeout=10
            )
            if compile_result.returncode != 0:
                pytest.skip("Failed to compile Java args test")
        except Exception:
            pytest.skip("Java compilation failed")

        # Run without args (should work) - pass source file name
        result = runner.run([source.name], "java")

        assert result["status"] == "successful"
        assert "Args: 0" in result["stdout"]

    def test_java_empty_filenames(self, runner):
        """Test Java with no files provided."""
        result = runner.run([], "java")

        assert result["status"] == "error"
        assert "No filename provided" in result["stderr"]


# ============================================================================
# Rust Tests
# ============================================================================

@pytest.fixture
def rust_project(temp_workspace):
    """Create a Rust project structure."""
    # Create .setup directory
    setup_dir = temp_workspace / ".setup"
    setup_dir.mkdir()

    # Create Cargo.toml (capital C required by cargo)
    cargo_toml = setup_dir / "Cargo.toml"
    cargo_toml.write_text("""
[package]
name = "test_project"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "main"
path = "../main.rs"
""")

    # Create main.rs
    main_rs = temp_workspace / "main.rs"
    main_rs.write_text("""
fn main() {
    println!("Hello from Rust!");
}
""")

    return {"manifest": cargo_toml, "source": main_rs}


@pytest.fixture
def rust_multi_file_project(temp_workspace):
    """Create a Rust project with multiple files."""
    # Create .setup directory
    setup_dir = temp_workspace / ".setup"
    setup_dir.mkdir()

    # Create Cargo.toml (capital C required by cargo)
    cargo_toml = setup_dir / "Cargo.toml"
    cargo_toml.write_text("""
[package]
name = "test_project"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "main"
path = "../main.rs"
""")

    # Create main.rs
    main_rs = temp_workspace / "main.rs"
    main_rs.write_text("""
mod utils;

fn main() {
    println!("Hello from Rust!");
    println!("{}", utils::get_message());
}
""")

    # Create utils.rs
    utils_rs = temp_workspace / "utils.rs"
    utils_rs.write_text("""
pub fn get_message() -> String {
    String::from("Utils message")
}
""")

    return {
        "manifest": cargo_toml,
        "main": main_rs,
        "utils": utils_rs
    }


class TestRust:
    """Test Rust code execution."""

    def test_rust_success(self, temp_workspace, rust_project):
        """Test successful Rust execution."""
        # Check if cargo is available
        import subprocess
        try:
            subprocess.run(["cargo", "--version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("cargo not found")

        # Rust compilation can be slow, use longer timeout
        runner = CodeRunner(base_dir=temp_workspace, timeout_sec=120)
        result = runner.run([rust_project["source"].name], "rust")

        assert result["status"] == "successful"
        assert "Hello from Rust!" in result["stdout"]
        assert result["returncode"] == 0

    def test_rust_multiple_files(self, temp_workspace, rust_multi_file_project):
        """Test Rust execution with multiple source files."""
        # Check if cargo is available
        import subprocess
        try:
            subprocess.run(["cargo", "--version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("cargo not found")

        # Rust compilation can be slow
        runner = CodeRunner(base_dir=temp_workspace, timeout_sec=120)
        result = runner.run(
            [rust_multi_file_project["main"].name, rust_multi_file_project["utils"].name],
            "rust"
        )

        assert result["status"] == "successful"
        assert "Hello from Rust!" in result["stdout"]
        assert "Utils message" in result["stdout"]

    def test_rust_missing_manifest(self, temp_workspace):
        """Test Rust without Cargo.toml."""
        runner = CodeRunner(base_dir=temp_workspace)

        # Create a Rust file without Cargo.toml
        rs_file = temp_workspace / "test.rs"
        rs_file.write_text("fn main() { println!(\"Test\"); }")

        result = runner.run([rs_file.name], "rust")

        assert result["status"] == "error"
        # Should fail because manifest doesn't exist
        assert result["returncode"] != 0 or "not found" in result["stderr"]

    def test_rust_missing_source_file(self, runner, rust_project):
        """Test Rust with non-existent source file."""
        result = runner.run(["missing.rs"], "rust")

        assert result["status"] == "error"
        assert "not found" in result["stderr"]

    def test_rust_compilation_error(self, temp_workspace, rust_project):
        """Test Rust with compilation error."""
        # Check if cargo is available
        import subprocess
        try:
            subprocess.run(["cargo", "--version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("cargo not found")

        # Create invalid Rust code
        bad_rs = temp_workspace / "bad.rs"
        bad_rs.write_text("""
fn main() {
    let x = 5
    println!("{}", x);
}
""")

        # Update Cargo.toml to point to bad.rs
        cargo_toml = rust_project["manifest"]
        cargo_toml.write_text("""
[package]
name = "test_project"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "bad"
path = "../bad.rs"
""")

        runner = CodeRunner(base_dir=temp_workspace, timeout_sec=120)
        result = runner.run([bad_rs.name], "rust")

        assert result["status"] == "error"
        assert result["returncode"] != 0

    def test_rust_runtime_panic(self, temp_workspace, rust_project):
        """Test Rust program that panics."""
        # Check if cargo is available
        import subprocess
        try:
            subprocess.run(["cargo", "--version"], capture_output=True, timeout=5)
        except FileNotFoundError:
            pytest.skip("cargo not found")

        # Create a program that panics
        panic_rs = temp_workspace / "panic.rs"
        panic_rs.write_text("""
fn main() {
    panic!("Test panic!");
}
""")

        # Update Cargo.toml
        cargo_toml = rust_project["manifest"]
        cargo_toml.write_text("""
[package]
name = "test_project"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "panic"
path = "../panic.rs"
""")

        runner = CodeRunner(base_dir=temp_workspace, timeout_sec=120)
        result = runner.run([panic_rs.name], "rust")

        assert result["status"] == "error"
        assert result["returncode"] != 0

    def test_rust_empty_filenames(self, runner):
        """Test Rust with no files provided."""
        result = runner.run([], "rust")

        assert result["status"] == "error"
        assert "No filename provided" in result["stderr"]


# ============================================================================
# General Tests
# ============================================================================

class TestGeneral:
    """Test general CodeRunner functionality."""
    
    def test_unsupported_language(self, runner, temp_workspace):
        """Test with unsupported language."""
        script = temp_workspace / "test.rb"
        script.write_text("puts 'Hello'")
        
        result = runner.run([script.name], "ruby")
        
        assert result["status"] == "error"
        assert "Unsupported language" in result["stderr"]
    
    def test_empty_stdout(self, runner, temp_workspace):
        """Test script with no output."""
        script = temp_workspace / "silent.py"
        script.write_text("# No output")
        
        result = runner.run([script.name], "python")
        
        assert result["status"] == "successful"
        assert result["stdout"] == ""
    
    def test_large_output_truncation(self, temp_workspace):
        """Test that large output is truncated."""
        # Create runner with small max_output
        runner = CodeRunner(base_dir=temp_workspace, max_output_length=100)
        
        script = temp_workspace / "large_output.py"
        script.write_text("print('A' * 1000)")
        
        result = runner.run([script.name], "python")
        
        assert result["status"] == "successful"
        assert len(result["stdout"]) <= 200  # Truncated (50 + middle message + 50)
        assert "truncated" in result["stdout"]
    
    def test_duration_measurement(self, runner, temp_workspace):
        """Test that duration is measured correctly."""
        script = temp_workspace / "sleep.py"
        script.write_text("""
import time
time.sleep(0.1)
print('Done')
""")
        
        result = runner.run([script.name], "python")
        
        assert result["status"] == "successful"
        assert result["duration_sec"] >= 0.1
        assert result["duration_sec"] < 1.0  # Should be quick
    
    def test_paths_in_result(self, runner, python_script):
        """Test that paths are included in result."""
        result = runner.run([python_script.name], "python")
        
        assert "paths" in result
        assert len(result["paths"]) == 1
        assert python_script.name in result["paths"][0]
    
    def test_cmd_in_result(self, runner, python_script):
        """Test that command is included in result."""
        result = runner.run([python_script.name], "python")
        
        assert "cmd" in result
        assert len(result["cmd"]) > 0
        assert sys.executable in result["cmd"]


# ============================================================================
# Configuration Tests
# ============================================================================

class TestConfiguration:
    """Test CodeRunner configuration."""
    
    def test_custom_timeout(self, temp_workspace):
        """Test custom timeout configuration."""
        runner = CodeRunner(base_dir=temp_workspace, timeout_sec=1)
        
        script = temp_workspace / "timeout.py"
        script.write_text("""
import time
time.sleep(5)
""")
        
        result = runner.run([script.name], "python")
        
        assert result["status"] == "error"
        assert "Timeout" in result["stderr"]
        assert result["duration_sec"] >= 1
        assert result["duration_sec"] < 2
    
    def test_custom_base_dir(self, tmp_path):
        """Test custom base directory."""
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        
        runner = CodeRunner(base_dir=custom_dir)
        
        script = custom_dir / "test.py"
        script.write_text("print('Custom dir')")
        
        result = runner.run([script.name], "python")
        
        assert result["status"] == "successful"
        assert "Custom dir" in result["stdout"]
    
    def test_custom_max_output_length(self, temp_workspace):
        """Test custom max output length."""
        runner = CodeRunner(base_dir=temp_workspace, max_output_length=50)
        
        script = temp_workspace / "output.py"
        script.write_text("print('A' * 200)")
        
        result = runner.run([script.name], "python")
        
        assert "truncated" in result["stdout"]


# ============================================================================
# Global Function Tests
# ============================================================================

class TestGlobalFunctions:
    """Test global functions (run_code, configure_runner, get_runner)."""
    
    def test_run_code_function(self, temp_workspace):
        """Test the global run_code function."""
        # Configure global runner
        configure_runner(base_dir=temp_workspace)
        
        # Create test script
        script = temp_workspace / "test.py"
        script.write_text("print('Global function')")
        
        # Use global function
        if hasattr(run_code, 'func'):
            # It's a StructuredTool, get the underlying function
            result = run_code.func(filenames=[script.name], language="python")
        elif callable(run_code):
            # It's a direct function
            result = run_code([script.name], "python")
        else:
            pytest.fail(f"run_code is neither callable nor a StructuredTool: {type(run_code)}")
        
        assert result["status"] == "successful"
        assert "Global function" in result["stdout"]
    
    def test_get_runner_singleton(self):
        """Test that get_runner returns singleton."""
        runner1 = get_runner()
        runner2 = get_runner()
        
        assert runner1 is runner2
    
    def test_configure_runner_creates_new_instance(self, temp_workspace):
        """Test that configure_runner creates new instance."""
        runner1 = get_runner()
        
        configure_runner(base_dir=temp_workspace, timeout_sec=100)
        
        runner2 = get_runner()
        
        assert runner2.timeout_sec == 100
    
    def test_run_code_uses_configuration(self, temp_workspace):
        """Test that run_code uses global configuration."""
        configure_runner(base_dir=temp_workspace, timeout_sec=1)
        
        script = temp_workspace / "timeout.py"
        script.write_text("""
import time
time.sleep(5)
""")
        
        if hasattr(run_code, 'func'):
            # It's a StructuredTool
            result = run_code.func(filenames=[script.name], language="python")
        else:
            # It's a direct function
            result = run_code([script.name], "python")
        
        assert result["status"] == "error"
        assert "Timeout" in result["stderr"]


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and unusual inputs."""
    
    def test_absolute_path(self, runner, temp_workspace):
        """Test with absolute path."""
        script = temp_workspace / "test.py"
        script.write_text("print('Absolute path')")
        
        result = runner.run([str(script.absolute())], "python")
        
        assert result["status"] == "successful"
        assert "Absolute path" in result["stdout"]
    
    def test_relative_path(self, runner, temp_workspace):
        """Test with relative path."""
        script = temp_workspace / "test.py"
        script.write_text("print('Relative path')")
        
        # Change to workspace directory
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_workspace)
            result = runner.run(["test.py"], "python")
            
            assert result["status"] == "successful"
            assert "Relative path" in result["stdout"]
        finally:
            os.chdir(original_cwd)
    
    def test_unicode_output(self, runner, temp_workspace):
        """Test script with unicode output."""
        script = temp_workspace / "unicode.py"
        script.write_text("print('Hello 世界 🌍')")
        
        result = runner.run([script.name], "python")
        
        assert result["status"] == "successful"
        assert "世界" in result["stdout"]
        assert "🌍" in result["stdout"]
    
    def test_exit_code_nonzero_without_exception(self, runner, temp_workspace):
        """Test script that exits with non-zero code."""
        script = temp_workspace / "exit.py"
        script.write_text("""
import sys
print('Exiting with code 42')
sys.exit(42)
""")
        
        result = runner.run([script.name], "python")
        
        assert result["status"] == "error"
        assert result["returncode"] == 42
        assert "Exiting with code 42" in result["stdout"]
    
    def test_permission_error_handling(self, runner, temp_workspace):
        """Test handling of permission errors."""
        # This test might not work on all systems
        script = temp_workspace / "noperm.py"
        script.write_text("print('Test')")
        script.chmod(0o000)  # Remove all permissions
        
        try:
            result = runner.run([script.name], "python")
            
            # Depending on the system, this might succeed or fail
            # Just ensure we don't crash
            assert result["status"] in ["successful", "error"]
        finally:
            # Restore permissions for cleanup
            script.chmod(0o644)


# ============================================================================
# Write File Tests
# ============================================================================

class TestWriteFile:
    """Test write_file tool restrictions."""

    def test_write_file_blocks_cargo_toml(self):
        """Test that write_file blocks writing to Cargo.toml."""
        from app.tools import write_file, BASE_DIR

        if hasattr(write_file, 'func'):
            result = write_file.func(
                filename="Cargo.toml",
                content="[package]\nname = \"test\""
            )
        else:
            result = write_file("Cargo.toml", "[package]\nname = \"test\"")

        assert "ERROR" in result
        assert "Cannot modify configuration file" in result
        assert not (BASE_DIR / "Cargo.toml").exists()

    def test_write_file_blocks_cargo_toml_case_insensitive(self):
        """Test that write_file blocks Cargo.toml case-insensitively."""
        from app.tools import write_file

        if hasattr(write_file, 'func'):
            result = write_file.func(
                filename="cargo.toml",
                content="[package]\nname = \"test\""
            )
        else:
            result = write_file("cargo.toml", "[package]\nname = \"test\"")

        assert "ERROR" in result
        assert "Cannot modify configuration file" in result

    def test_write_file_blocks_go_mod(self):
        """Test that write_file blocks writing to go.mod."""
        from app.tools import write_file, BASE_DIR

        if hasattr(write_file, 'func'):
            result = write_file.func(
                filename="go.mod",
                content="module test\n\ngo 1.21"
            )
        else:
            result = write_file("go.mod", "module test\n\ngo 1.21")

        assert "ERROR" in result
        assert "Cannot modify configuration file" in result
        assert not (BASE_DIR / "go.mod").exists()

    def test_write_file_blocks_csproj(self):
        """Test that write_file blocks writing to .csproj files."""
        from app.tools import write_file, BASE_DIR

        if hasattr(write_file, 'func'):
            result = write_file.func(
                filename="test.csproj",
                content="<Project>...</Project>"
            )
        else:
            result = write_file("test.csproj", "<Project>...</Project>")

        assert "ERROR" in result
        assert "Cannot modify .csproj files" in result
        assert not (BASE_DIR / "test.csproj").exists()

    def test_write_file_allows_normal_files(self, temp_workspace):
        """Test that write_file allows writing normal source files."""
        from app.tools import write_file, BASE_DIR

        # Test various allowed file types
        test_files = [
            ("test_write_py.py", "print('hello')"),
            ("test_write_cpp.cpp", "#include <iostream>"),
            ("test_write_java.java", "public class Test {}"),
            ("test_write_rs.rs", "fn main() {}"),
            ("test_write_go.go", "package main"),
        ]

        for filename, content in test_files:
            if hasattr(write_file, 'func'):
                result = write_file.func(filename=filename, content=content)
            else:
                result = write_file(filename, content)

            assert "SUCCESS" in result
            # write_file uses BASE_DIR, not temp_workspace
            assert (BASE_DIR / filename).exists()

            # Clean up
            (BASE_DIR / filename).unlink()


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])