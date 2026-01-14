"""Comprehensive tests for app/utils/compiler.py - Real compilation tests without mocking"""

import sys
import os
import shutil
import pytest
from pathlib import Path

from app.utils.compiler import (
    CompilationResult,
    BaseCompiler,
    CppCompiler,
    JavaCompiler,
    CompilerRegistry
)


# Check which compilers are available
HAS_GPP = shutil.which("g++") is not None
HAS_JAVAC = shutil.which("javac") is not None


# ============================================================================
# CompilationResult Tests
# ============================================================================

class TestCompilationResult:
    """Tests for CompilationResult data class."""

    def test_initialization(self):
        """Test basic initialization of CompilationResult."""
        result = CompilationResult(
            status="successful",
            returncode=0,
            stdout="Build successful",
            stderr="",
            duration_sec=1.23,
            cmd=["g++", "test.cpp"],
            source_paths=["test.cpp"],
            output_path="test"
        )

        assert result.status == "successful"
        assert result.returncode == 0
        assert result.stdout == "Build successful"
        assert result.stderr == ""
        assert result.duration_sec == 1.23
        assert result.cmd == ["g++", "test.cpp"]
        assert result.source_paths == ["test.cpp"]
        assert result.output_path == "test"
        assert result.note is None

    def test_initialization_with_note(self):
        """Test initialization with optional note field."""
        result = CompilationResult(
            status="error",
            returncode=None,
            stdout="",
            stderr="Timeout",
            duration_sec=180.0,
            cmd=["g++", "test.cpp"],
            source_paths=["test.cpp"],
            output_path="test",
            note="Compilation timed out"
        )

        assert result.note == "Compilation timed out"

    def test_to_dict_without_note(self):
        """Test to_dict conversion without note."""
        result = CompilationResult(
            status="successful",
            returncode=0,
            stdout="output",
            stderr="",
            duration_sec=1.0,
            cmd=["g++", "test.cpp"],
            source_paths=["test.cpp"],
            output_path="test"
        )

        result_dict = result.to_dict()

        assert result_dict == {
            "status": "successful",
            "returncode": 0,
            "stdout": "output",
            "stderr": "",
            "duration_sec": 1.0,
            "cmd": ["g++", "test.cpp"],
            "source_paths": ["test.cpp"],
            "output_path": "test"
        }
        assert "note" not in result_dict

    def test_to_dict_with_note(self):
        """Test to_dict conversion with note."""
        result = CompilationResult(
            status="error",
            returncode=None,
            stdout="",
            stderr="error",
            duration_sec=1.0,
            cmd=[],
            source_paths=[],
            output_path="",
            note="Test note"
        )

        result_dict = result.to_dict()

        assert "note" in result_dict
        assert result_dict["note"] == "Test note"


# ============================================================================
# BaseCompiler Tests
# ============================================================================

class ConcreteCompiler(BaseCompiler):
    """Concrete implementation of BaseCompiler for testing."""

    @property
    def language_name(self) -> str:
        return "Test Language"

    @property
    def supported_extensions(self):
        return {".test", ".tst"}

    def build_compile_command(self, source_paths, output_path, **options):
        return ["echo", "test-compiler"] + [str(p) for p in source_paths]


class TestBaseCompiler:
    """Tests for BaseCompiler abstract base class."""

    def test_initialization(self, tmp_path):
        """Test BaseCompiler initialization."""
        compiler = ConcreteCompiler(tmp_path, timeout_sec=60, max_output_bytes=1000)

        assert compiler.base_dir == tmp_path
        assert compiler.timeout_sec == 60
        assert compiler.max_output_bytes == 1000

    def test_default_initialization(self, tmp_path):
        """Test BaseCompiler initialization with defaults."""
        compiler = ConcreteCompiler(tmp_path)

        assert compiler.timeout_sec == 180
        assert compiler.max_output_bytes == 300_000

    def test_validate_sources_valid(self, tmp_path):
        """Test validate_sources with valid extensions."""
        compiler = ConcreteCompiler(tmp_path)
        sources = [tmp_path / "file1.test", tmp_path / "file2.tst"]

        is_valid, error_msg = compiler.validate_sources(sources)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_sources_invalid(self, tmp_path):
        """Test validate_sources with invalid extensions."""
        compiler = ConcreteCompiler(tmp_path)
        sources = [tmp_path / "file1.txt"]

        is_valid, error_msg = compiler.validate_sources(sources)

        assert is_valid is False
        assert "Invalid file extension '.txt'" in error_msg
        assert "Test Language" in error_msg
        assert ".test" in error_msg
        assert ".tst" in error_msg

    def test_validate_sources_case_insensitive(self, tmp_path):
        """Test validate_sources is case-insensitive."""
        compiler = ConcreteCompiler(tmp_path)
        sources = [tmp_path / "file1.TEST", tmp_path / "file2.TST"]

        is_valid, error_msg = compiler.validate_sources(sources)

        assert is_valid is True
        assert error_msg == ""

    def test_resolve_output_path_removes_extension(self, tmp_path):
        """Test resolve_output_path removes extension."""
        compiler = ConcreteCompiler(tmp_path)
        output = compiler.resolve_output_path(tmp_path / "program.out")

        # On Windows it should have .exe, on Linux no extension
        if sys.platform.startswith("win"):
            assert output.suffix == ".exe"
        else:
            assert output.suffix == ""

    def test_truncate_output_none(self, tmp_path):
        """Test truncate_output with None input."""
        compiler = ConcreteCompiler(tmp_path)
        result = compiler.truncate_output(None)

        assert result == ""

    def test_truncate_output_short_text(self, tmp_path):
        """Test truncate_output with text shorter than max."""
        compiler = ConcreteCompiler(tmp_path, max_output_bytes=1000)
        text = "Short output"

        result = compiler.truncate_output(text)

        assert result == text

    def test_truncate_output_long_text(self, tmp_path):
        """Test truncate_output with text longer than max."""
        compiler = ConcreteCompiler(tmp_path, max_output_bytes=100)
        text = "A" * 200

        result = compiler.truncate_output(text)

        assert len(result.encode("utf-8")) <= 100
        assert "..." in result
        assert result.startswith("A")
        assert result.endswith("A")

    def test_truncate_output_exact_boundary(self, tmp_path):
        """Test truncate_output at exact boundary."""
        compiler = ConcreteCompiler(tmp_path, max_output_bytes=100)
        text = "B" * 100

        result = compiler.truncate_output(text)

        assert result == text

    def test_compile_invalid_extension(self, tmp_path):
        """Test compile with invalid file extension."""
        compiler = ConcreteCompiler(tmp_path)
        sources = [tmp_path / "test.invalid"]
        output = tmp_path / "program"

        result = compiler.compile(sources, output)

        assert result.status == "error"
        assert result.returncode is None
        assert "Invalid file extension" in result.stderr
        assert result.cmd == []


# ============================================================================
# C++ Compiler Real Tests
# ============================================================================

@pytest.mark.skipif(not HAS_GPP, reason="g++ not available")
class TestCppCompilerReal:
    """Real compilation tests for C++ compiler."""

    def test_language_name(self, tmp_path):
        """Test language_name property."""
        compiler = CppCompiler(tmp_path)
        assert compiler.language_name == "C++"

    def test_supported_extensions(self, tmp_path):
        """Test supported_extensions property."""
        compiler = CppCompiler(tmp_path)
        expected = {".cpp", ".cc", ".cxx", ".c++"}
        assert compiler.supported_extensions == expected

    def test_compile_simple_program(self, tmp_path):
        """Test compiling a simple C++ program."""
        # Create a simple C++ program
        source = tmp_path / "hello.cpp"
        source.write_text("""
#include <iostream>

int main() {
    std::cout << "Hello, World!" << std::endl;
    return 0;
}
""")

        compiler = CppCompiler(tmp_path)
        output = tmp_path / "hello"

        result = compiler.compile([source], output)

        assert result.status == "successful"
        assert result.returncode == 0
        assert result.duration_sec > 0
        assert "g++" in result.cmd[0]

        # Check that binary was created
        expected_binary = compiler.resolve_output_path(output)
        assert expected_binary.exists()
        assert os.access(expected_binary, os.X_OK)  # Check it's executable

    def test_compile_with_syntax_error(self, tmp_path):
        """Test compiling C++ code with syntax error."""
        # Create C++ program with syntax error
        source = tmp_path / "broken.cpp"
        source.write_text("""
#include <iostream>

int main() {
    std::cout << "Missing semicolon"
    return 0;
}
""")

        compiler = CppCompiler(tmp_path)
        output = tmp_path / "broken"

        result = compiler.compile([source], output)

        assert result.status == "error"
        assert result.returncode != 0
        assert len(result.stderr) > 0
        assert "error" in result.stderr.lower()

    def test_compile_with_openmp(self, tmp_path):
        """Test compiling with OpenMP flag."""
        source = tmp_path / "openmp.cpp"
        source.write_text("""
#include <iostream>
#include <omp.h>

int main() {
    #pragma omp parallel
    {
        #pragma omp single
        std::cout << "Threads: " << omp_get_num_threads() << std::endl;
    }
    return 0;
}
""")

        compiler = CppCompiler(tmp_path)
        output = tmp_path / "openmp"

        result = compiler.compile([source], output, openmp="on")

        assert result.status == "successful"
        assert result.returncode == 0
        assert "-fopenmp" in result.cmd

        expected_binary = compiler.resolve_output_path(output)
        assert expected_binary.exists()

    def test_compile_multiple_files(self, tmp_path):
        """Test compiling multiple C++ files."""
        # Main file
        main = tmp_path / "main.cpp"
        main.write_text("""
#include <iostream>

extern int add(int a, int b);

int main() {
    std::cout << "5 + 3 = " << add(5, 3) << std::endl;
    return 0;
}
""")

        # Helper file
        helper = tmp_path / "math.cpp"
        helper.write_text("""
int add(int a, int b) {
    return a + b;
}
""")

        compiler = CppCompiler(tmp_path)
        output = tmp_path / "program"

        result = compiler.compile([main, helper], output)

        assert result.status == "successful"
        assert result.returncode == 0
        assert str(main) in result.source_paths
        assert str(helper) in result.source_paths

        expected_binary = compiler.resolve_output_path(output)
        assert expected_binary.exists()

    def test_compile_with_optimization(self, tmp_path):
        """Test compiling with different optimization levels."""
        source = tmp_path / "optimize.cpp"
        source.write_text("""
#include <iostream>

int main() {
    int sum = 0;
    for (int i = 0; i < 1000; i++) {
        sum += i;
    }
    std::cout << sum << std::endl;
    return 0;
}
""")

        compiler = CppCompiler(tmp_path)
        output = tmp_path / "optimize"

        result = compiler.compile([source], output, optimization="-O2")

        assert result.status == "successful"
        assert "-O2" in result.cmd
        assert "-O3" not in result.cmd

    def test_compile_with_extra_flags(self, tmp_path):
        """Test compiling with extra compiler flags."""
        source = tmp_path / "warnings.cpp"
        source.write_text("""
#include <iostream>

int main() {
    int unused = 42;  // This will trigger warning with -Wunused-variable
    std::cout << "Hello" << std::endl;
    return 0;
}
""")

        compiler = CppCompiler(tmp_path)
        output = tmp_path / "warnings"

        result = compiler.compile([source], output, extra_flags=["-Wall", "-Wextra"])

        # Should still compile successfully but with warnings
        assert "-Wall" in result.cmd
        assert "-Wextra" in result.cmd

    def test_compile_invalid_extension(self, tmp_path):
        """Test compiling file with invalid extension."""
        source = tmp_path / "test.txt"
        source.write_text("not c++ code")

        compiler = CppCompiler(tmp_path)
        output = tmp_path / "program"

        result = compiler.compile([source], output)

        assert result.status == "error"
        assert "Invalid file extension" in result.stderr


# ============================================================================
# Java Compiler Real Tests
# ============================================================================

@pytest.mark.skipif(not HAS_JAVAC, reason="javac not available")
class TestJavaCompilerReal:
    """Real compilation tests for Java compiler."""

    def test_language_name(self, tmp_path):
        """Test language_name property."""
        compiler = JavaCompiler(tmp_path)
        assert compiler.language_name == "Java"

    def test_supported_extensions(self, tmp_path):
        """Test supported_extensions property."""
        compiler = JavaCompiler(tmp_path)
        assert compiler.supported_extensions == {".java"}

    def test_compile_simple_program(self, tmp_path):
        """Test compiling a simple Java program."""
        # Create a simple Java program
        source = tmp_path / "HelloWorld.java"
        source.write_text("""
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
""")

        compiler = JavaCompiler(tmp_path)
        output = tmp_path

        result = compiler.compile([source], output)

        assert result.status == "successful"
        assert result.returncode == 0
        assert result.duration_sec > 0
        assert "javac" in result.cmd[0]

        # Check that .class file was created
        class_file = tmp_path / "HelloWorld.class"
        assert class_file.exists()

    def test_compile_with_syntax_error(self, tmp_path):
        """Test compiling Java code with syntax error."""
        # Create Java program with syntax error
        source = tmp_path / "Broken.java"
        source.write_text("""
public class Broken {
    public static void main(String[] args) {
        System.out.println("Missing semicolon")
    }
}
""")

        compiler = JavaCompiler(tmp_path)
        output = tmp_path

        result = compiler.compile([source], output)

        assert result.status == "error"
        assert result.returncode != 0
        assert len(result.stderr) > 0

    def test_compile_multiple_classes(self, tmp_path):
        """Test compiling multiple Java files."""
        # Main class
        main = tmp_path / "Main.java"
        main.write_text("""
public class Main {
    public static void main(String[] args) {
        Calculator calc = new Calculator();
        System.out.println("5 + 3 = " + calc.add(5, 3));
    }
}
""")

        # Helper class
        helper = tmp_path / "Calculator.java"
        helper.write_text("""
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
""")

        compiler = JavaCompiler(tmp_path)
        output = tmp_path

        result = compiler.compile([main, helper], output)

        assert result.status == "successful"
        assert result.returncode == 0

        # Check both class files were created
        assert (tmp_path / "Main.class").exists()
        assert (tmp_path / "Calculator.class").exists()

    def test_compile_with_extra_flags(self, tmp_path):
        """Test compiling with extra compiler flags."""
        source = tmp_path / "Test.java"
        source.write_text("""
public class Test {
    public static void main(String[] args) {
        System.out.println("Test");
    }
}
""")

        compiler = JavaCompiler(tmp_path)
        output = tmp_path

        result = compiler.compile([source], output, extra_flags=["-g"])

        assert result.status == "successful"
        assert "-g" in result.cmd

    def test_compile_invalid_extension(self, tmp_path):
        """Test compiling file with invalid extension."""
        source = tmp_path / "Test.txt"
        source.write_text("not java code")

        compiler = JavaCompiler(tmp_path)
        output = tmp_path

        result = compiler.compile([source], output)

        assert result.status == "error"
        assert "Invalid file extension" in result.stderr


# ============================================================================
# CompilerRegistry Tests
# ============================================================================

class TestCompilerRegistry:
    """Tests for CompilerRegistry class."""

    def test_initialization(self, tmp_path):
        """Test CompilerRegistry initialization."""
        registry = CompilerRegistry(tmp_path, timeout_sec=60, max_output_bytes=1000)

        assert registry.base_dir == tmp_path
        assert registry.timeout_sec == 60
        assert registry.max_output_bytes == 1000
        assert len(registry._compilers) > 0

    def test_get_compiler_cpp(self, tmp_path):
        """Test getting C++ compiler."""
        registry = CompilerRegistry(tmp_path)
        compiler = registry.get_compiler("cpp")

        assert compiler is not None
        assert isinstance(compiler, CppCompiler)
        assert compiler.language_name == "C++"

    def test_get_compiler_java(self, tmp_path):
        """Test getting Java compiler."""
        registry = CompilerRegistry(tmp_path)
        compiler = registry.get_compiler("java")

        assert compiler is not None
        assert isinstance(compiler, JavaCompiler)
        assert compiler.language_name == "Java"

    def test_get_compiler_case_insensitive(self, tmp_path):
        """Test get_compiler is case-insensitive."""
        registry = CompilerRegistry(tmp_path)

        cpp1 = registry.get_compiler("cpp")
        cpp2 = registry.get_compiler("CPP")
        cpp3 = registry.get_compiler("Cpp")

        assert cpp1 is cpp2 is cpp3

    def test_get_compiler_unsupported(self, tmp_path):
        """Test getting unsupported compiler."""
        registry = CompilerRegistry(tmp_path)
        compiler = registry.get_compiler("python")

        assert compiler is None

    def test_supported_languages(self, tmp_path):
        """Test supported_languages method."""
        registry = CompilerRegistry(tmp_path)
        languages = registry.supported_languages()

        assert isinstance(languages, list)
        assert "cpp" in languages
        assert "java" in languages

    def test_compile_unsupported_language(self, tmp_path):
        """Test compile with unsupported language."""
        registry = CompilerRegistry(tmp_path)
        sources = [tmp_path / "test.py"]
        output = tmp_path / "program"

        result = registry.compile("python", sources, output)

        assert result.status == "error"
        assert result.returncode is None
        assert "Unsupported language: python" in result.stderr
        assert "cpp" in result.stderr
        assert "java" in result.stderr

    def test_compiler_inherits_settings(self, tmp_path):
        """Test that compilers inherit registry settings."""
        registry = CompilerRegistry(tmp_path, timeout_sec=99, max_output_bytes=999)
        cpp_compiler = registry.get_compiler("cpp")

        assert cpp_compiler.timeout_sec == 99
        assert cpp_compiler.max_output_bytes == 999

    def test_language_name_normalization(self, tmp_path):
        """Test that C++ is normalized to 'cpp' key."""
        registry = CompilerRegistry(tmp_path)

        # C++ should be accessible as 'cpp' (+ replaced with p)
        compiler = registry.get_compiler("cpp")
        assert compiler is not None
        assert compiler.language_name == "C++"

    @pytest.mark.skipif(not HAS_GPP, reason="g++ not available")
    def test_compile_cpp_through_registry(self, tmp_path):
        """Test C++ compilation through registry."""
        source = tmp_path / "test.cpp"
        source.write_text("""
#include <iostream>
int main() {
    std::cout << "Test" << std::endl;
    return 0;
}
""")

        registry = CompilerRegistry(tmp_path)
        output = tmp_path / "test"

        result = registry.compile("cpp", [source], output)

        assert result.status == "successful"
        assert result.returncode == 0

    @pytest.mark.skipif(not HAS_JAVAC, reason="javac not available")
    def test_compile_java_through_registry(self, tmp_path):
        """Test Java compilation through registry."""
        source = tmp_path / "Test.java"
        source.write_text("""
public class Test {
    public static void main(String[] args) {
        System.out.println("Test");
    }
}
""")

        registry = CompilerRegistry(tmp_path)
        output = tmp_path

        result = registry.compile("java", [source], "")
        assert result.status == "successful"
        assert result.returncode == 0


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.skipif(not HAS_GPP, reason="g++ not available")
class TestCppIntegration:
    """Integration tests for C++ compilation."""

    def test_full_cpp_workflow_with_options(self, tmp_path):
        """Test full C++ compilation workflow with OpenMP and custom optimization."""
        source = tmp_path / "parallel.cpp"
        source.write_text("""
#include <iostream>
#include <omp.h>

int main() {
    int sum = 0;
    #pragma omp parallel for reduction(+:sum)
    for (int i = 0; i < 100; i++) {
        sum += i;
    }
    std::cout << "Sum: " << sum << std::endl;
    return 0;
}
""")

        registry = CompilerRegistry(tmp_path)
        output = tmp_path / "parallel"

        result = registry.compile("cpp", [source], output, openmp="on", optimization="-O2")

        assert result.status == "successful"
        assert result.returncode == 0
        assert result.duration_sec > 0
        assert "-fopenmp" in result.cmd
        assert "-O2" in result.cmd

        # Verify to_dict works
        result_dict = result.to_dict()
        assert result_dict["status"] == "successful"
        assert result_dict["returncode"] == 0

    def test_compilation_error_handling(self, tmp_path):
        """Test comprehensive error handling."""
        source = tmp_path / "errors.cpp"
        source.write_text("""
#include <iostream>

int main() {
    undeclared_variable = 5;  // Error: undeclared variable
    std::cout << "Should not compile" << std::endl
    return 0;  // Error: missing semicolon above
}
""")

        registry = CompilerRegistry(tmp_path)
        output = tmp_path / "errors"

        result = registry.compile("cpp", [source], output)

        assert result.status == "error"
        assert result.returncode != 0
        assert len(result.stderr) > 0

        # Verify error is properly serialized
        result_dict = result.to_dict()
        assert result_dict["status"] == "error"
        assert len(result_dict["stderr"]) > 0


@pytest.mark.skipif(not HAS_JAVAC, reason="javac not available")
class TestJavaIntegration:
    """Integration tests for Java compilation."""

    def test_full_java_workflow(self, tmp_path):
        """Test full Java compilation workflow."""
        source = tmp_path / "Application.java"
        source.write_text("""
public class Application {
    public static void main(String[] args) {
        for (int i = 0; i < 10; i++) {
            System.out.println("Number: " + i);
        }
    }
}
""")

        registry = CompilerRegistry(tmp_path)
        output = tmp_path

        result = registry.compile("java", [source], output)

        assert result.status == "successful"
        assert result.returncode == 0
        assert result.duration_sec > 0

        # Verify class file created
        assert (tmp_path / "Application.class").exists()

        # Verify to_dict works
        result_dict = result.to_dict()
        assert result_dict["status"] == "successful"


# ============================================================================
# Tool Function Tests (tools.py)
# ============================================================================

class TestCompileCodeTool:
    """Tests for the compile_code tool function from tools.py."""

    def test_compile_code_converts_strings_to_paths_cpp(self, tmp_path):
        """Test that compile_code correctly converts string paths to Path objects for C++."""
        from app.tools import compile_code, configure_runner, BASE_DIR

        # Create a simple C++ source in BASE_DIR
        source = BASE_DIR / "test_tool.cpp"
        source.write_text("""
#include <iostream>
int main() {
    std::cout << "Test" << std::endl;
    return 0;
}
""")

        try:
            # Call compile_code with string arguments (as the tool would receive)
            if HAS_GPP:
                result = compile_code.func(
                    source_files=["test_tool.cpp"],
                    output_file="test_tool_output",
                    language="C++",
                    openmp="off"
                )

                # Should succeed without AttributeError
                assert result["status"] in ["successful", "error"]
                assert "source_paths" in result
                assert "output_path" in result

                # Clean up if successful
                if result["status"] == "successful":
                    output_path = BASE_DIR / "test_tool_output"
                    if sys.platform.startswith("win"):
                        output_path = output_path.with_suffix(".exe")
                    if output_path.exists():
                        output_path.unlink()
            else:
                pytest.skip("g++ not available")
        finally:
            # Clean up source file
            if source.exists():
                source.unlink()

    def test_compile_code_handles_empty_output_for_java(self, tmp_path):
        """Test that compile_code handles empty output path for Java."""
        from app.tools import compile_code, BASE_DIR

        # Create a simple Java source in BASE_DIR
        source = BASE_DIR / "TestTool.java"
        source.write_text("""
public class TestTool {
    public static void main(String[] args) {
        System.out.println("Test");
    }
}
""")

        try:
            if HAS_JAVAC:
                # Call compile_code with empty output_file (as Java uses)
                result = compile_code.func(
                    source_files=["TestTool.java"],
                    output_file="",  # Empty string for Java
                    language="Java",
                    openmp="off"
                )

                # Should succeed without FileNotFoundError
                assert result["status"] in ["successful", "error"]
                assert "source_paths" in result
                assert "output_path" in result

                # Clean up .class file if created
                class_file = BASE_DIR / "TestTool.class"
                if class_file.exists():
                    class_file.unlink()
            else:
                pytest.skip("javac not available")
        finally:
            # Clean up source file
            if source.exists():
                source.unlink()

    @pytest.mark.skipif(not HAS_GPP, reason="g++ not available")
    def test_compile_code_with_openmp_flag(self, tmp_path):
        """Test that compile_code correctly passes OpenMP flag."""
        from app.tools import compile_code, BASE_DIR

        source = BASE_DIR / "test_openmp_tool.cpp"
        source.write_text("""
#include <iostream>
#include <omp.h>

int main() {
    #pragma omp parallel
    {
        #pragma omp single
        std::cout << "Threads: " << omp_get_num_threads() << std::endl;
    }
    return 0;
}
""")

        try:
            result = compile_code.func(
                source_files=["test_openmp_tool.cpp"],
                output_file="test_openmp_tool",
                language="C++",
                openmp="on"
            )

            assert result["status"] == "successful"
            assert result["returncode"] == 0
            assert "-fopenmp" in result["cmd"]

            # Clean up
            output_path = BASE_DIR / "test_openmp_tool"
            if sys.platform.startswith("win"):
                output_path = output_path.with_suffix(".exe")
            if output_path.exists():
                output_path.unlink()
        finally:
            if source.exists():
                source.unlink()

    @pytest.mark.skipif(not HAS_GPP, reason="g++ not available")
    def test_compile_code_multiple_sources(self, tmp_path):
        """Test that compile_code handles multiple source files."""
        from app.tools import compile_code, BASE_DIR

        # Create main file
        main = BASE_DIR / "main_tool.cpp"
        main.write_text("""
#include <iostream>
extern int add(int a, int b);

int main() {
    std::cout << "5 + 3 = " << add(5, 3) << std::endl;
    return 0;
}
""")

        # Create helper file
        helper = BASE_DIR / "math_tool.cpp"
        helper.write_text("""
int add(int a, int b) {
    return a + b;
}
""")

        try:
            result = compile_code.func(
                source_files=["main_tool.cpp", "math_tool.cpp"],
                output_file="multi_tool",
                language="C++",
                openmp="off"
            )

            assert result["status"] == "successful"
            assert result["returncode"] == 0
            assert len(result["source_paths"]) == 2

            # Clean up
            output_path = BASE_DIR / "multi_tool"
            if sys.platform.startswith("win"):
                output_path = output_path.with_suffix(".exe")
            if output_path.exists():
                output_path.unlink()
        finally:
            if main.exists():
                main.unlink()
            if helper.exists():
                helper.unlink()

    def test_compile_code_invalid_file(self):
        """Test compile_code with non-existent file."""
        from app.tools import compile_code

        result = compile_code.func(
            source_files=["nonexistent.cpp"],
            output_file="output",
            language="C++",  # Tool accepts C++, which gets normalized to cpp
            openmp="off"
        )

        assert result["status"] == "error"
        # Error could be from path validation or compilation
        assert len(result["stderr"]) > 0

    def test_compile_code_unsupported_language(self):
        """Test compile_code with unsupported language."""
        from app.tools import compile_code, BASE_DIR

        source = BASE_DIR / "test.py"
        source.write_text("print('test')")

        try:
            # Try to compile Python (not supported by compiler)
            # This should fail because Python is not a valid Literal choice
            # But if we bypass that, it should still fail gracefully
            # For now, just test with an invalid extension for C++
            result = compile_code.func(
                source_files=["test.py"],
                output_file="output",
                language="C++",  # C++ but .py extension
                openmp="off"
            )

            assert result["status"] == "error"
        finally:
            if source.exists():
                source.unlink()


# ============================================================================
# Report missing compilers
# ============================================================================

def test_report_missing_compilers():
    """Report which compilers are missing (not a failure, just info)."""
    missing = []
    if not HAS_GPP:
        missing.append("g++")
    if not HAS_JAVAC:
        missing.append("javac")

    if missing:
        pytest.skip(f"Some compilers not available: {', '.join(missing)}")
