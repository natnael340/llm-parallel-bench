import sys
import time
import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path


class CompilationResult:
    """Structured result from compilation."""

    def __init__(
        self,
        status: str,
        returncode: Optional[int],
        stdout: str,
        stderr: str,
        duration_sec: float,
        cmd: List[str],
        source_paths: List[str],
        output_path: str,
        note: Optional[str] = None
    ):
        self.status = status
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration_sec = duration_sec
        self.cmd = cmd
        self.source_paths = source_paths
        self.output_path = output_path
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for tool response."""
        result = {
            "status": self.status,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_sec": self.duration_sec,
            "cmd": self.cmd,
            "source_paths": self.source_paths,
            "output_path": self.output_path,
        }
        if self.note:
            result["note"] = self.note
        return result


class BaseCompiler(ABC):
    """
    Abstract base class for all language compilers.

    Provides common functionality for compilation while allowing
    language-specific implementations to override as needed.
    """

    def __init__(
        self,
        base_dir: Path,
        timeout_sec: int = 180,
        max_output_bytes: int = 300_000
    ):
        self.base_dir = base_dir
        self.timeout_sec = timeout_sec
        self.max_output_bytes = max_output_bytes

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Human-readable language name."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> Set[str]:
        """Set of supported file extensions (e.g., {'.cpp', '.cc'})."""
        pass

    @abstractmethod
    def build_compile_command(
        self,
        source_paths: List[Path],
        output_path: Path,
        **options
    ) -> List[str]:
        """
        Build the compilation command for this language.

        Args:
            source_paths: List of validated source file paths
            output_path: Validated output file path
            **options: Language-specific compilation options

        Returns:
            Command list ready for subprocess.run()
        """
        pass

    def validate_sources(self, source_paths: List[Path]) -> Tuple[bool, str]:
        """
        Validate that source files have correct extensions.

        Args:
            source_paths: List of source file paths to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        for path in source_paths:
            if path.suffix.lower() not in self.supported_extensions:
                expected = ", ".join(sorted(self.supported_extensions))
                return False, (
                    f"Invalid file extension '{path.suffix}' for {self.language_name}. "
                    f"Expected: {expected}"
                )
        return True, ""

    def resolve_output_path(self, output_path: Path) -> Path:
        """
        Resolve and prepare output path.

        Default implementation removes extension and adds platform-specific
        executable extension if needed. Override for language-specific behavior.

        Args:
            output_path: Raw output path

        Returns:
            Resolved output path
        """
        out = output_path.with_suffix("")
        if sys.platform.startswith("win"):
            out = out.with_suffix(".exe")
        return out

    def truncate_output(self, text: str) -> str:
        """Truncate output if it exceeds maximum size."""
        if text is None:
            return ""

        encoded = text.encode("utf-8", errors="replace")
        if len(encoded) <= self.max_output_bytes:
            return text

        head = self.max_output_bytes // 2
        tail = self.max_output_bytes - head - len("\n...\n".encode())
        truncated = encoded[:head] + b"\n...\n" + encoded[-tail:]
        return truncated.decode("utf-8", errors="replace")

    def compile(
        self,
        source_paths: List[Path],
        output_path: Path,
        **options
    ) -> CompilationResult:
        """
        Execute compilation and return structured result.

        Args:
            source_paths: List of validated source file paths
            output_path: Validated output file path
            **options: Language-specific compilation options

        Returns:
            CompilationResult object
        """
        start = time.monotonic()
        source_strs = [str(p) for p in source_paths]
        output_str = str(output_path)

        try:
            # Validate source files
            is_valid, error_msg = self.validate_sources(source_paths)
            if not is_valid:
                return CompilationResult(
                    status="error",
                    returncode=None,
                    stdout="",
                    stderr=error_msg,
                    duration_sec=round(time.monotonic() - start, 6),
                    cmd=[],
                    source_paths=source_strs,
                    output_path=output_str
                )

            # Resolve output path
            resolved_output = self.resolve_output_path(output_path)

            # Build compilation command
            cmd = self.build_compile_command(source_paths, resolved_output, **options)

            # Execute compilation
            proc = subprocess.run(
                cmd,
                cwd=str(self.base_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout_sec
            )

            duration = round(time.monotonic() - start, 6)

            return CompilationResult(
                status="successful" if proc.returncode == 0 else "error",
                returncode=proc.returncode,
                stdout=self.truncate_output(proc.stdout),
                stderr=self.truncate_output(proc.stderr),
                duration_sec=duration,
                cmd=cmd,
                source_paths=source_strs,
                output_path=str(resolved_output)
            )

        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or "")
            err = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, (bytes, bytearray)) else (e.stderr or "")

            return CompilationResult(
                status="error",
                returncode=None,
                stdout=self.truncate_output(out),
                stderr=self.truncate_output(err) + f"\n[Compilation timeout after {self.timeout_sec}s]",
                duration_sec=round(time.monotonic() - start, 6),
                cmd=getattr(e, "cmd", []),
                source_paths=source_strs,
                output_path=output_str,
                note="Compilation timed out"
            )

        except FileNotFoundError as e:
            return CompilationResult(
                status="error",
                returncode=None,
                stdout="",
                stderr=f"Compiler not found: {e}. Please ensure the compiler is installed and in PATH.",
                duration_sec=round(time.monotonic() - start, 6),
                cmd=[],
                source_paths=source_strs,
                output_path=output_str
            )

        except Exception as e:
            return CompilationResult(
                status="error",
                returncode=None,
                stdout="",
                stderr=f"Unexpected error during compilation: {type(e).__name__}: {e}",
                duration_sec=round(time.monotonic() - start, 6),
                cmd=[],
                source_paths=source_strs,
                output_path=output_str
            )


class CppCompiler(BaseCompiler):
    """C++ compiler using g++."""

    @property
    def language_name(self) -> str:
        return "C++"

    @property
    def supported_extensions(self) -> Set[str]:
        return {".cpp", ".cc", ".cxx", ".c++"}

    def build_compile_command(
        self,
        source_paths: List[Path],
        output_path: Path,
        openmp: str = "off",
        optimization: str = "-O3",
        **kwargs
    ) -> List[str]:
        """
        Build g++ compilation command.

        Args:
            source_paths: C++ source files
            output_path: Output binary path
            openmp: "on" or "off" for OpenMP support
            optimization: Optimization level (default: -O3)
            **kwargs: Additional compiler flags

        Returns:
            Compilation command
        """
        compiler = shutil.which("g++")
        if not compiler:
            raise FileNotFoundError("g++ compiler not found")

        cmd = [compiler, optimization]

        # Add OpenMP flag if requested
        if openmp == "on":
            cmd.append("-fopenmp")

        # Add source files
        cmd.extend([str(src) for src in source_paths])

        # Add output flag
        cmd.extend(["-o", str(output_path)])

        # Add any additional flags
        extra_flags = kwargs.get("extra_flags", [])
        if extra_flags:
            cmd.extend(extra_flags)

        return cmd


class JavaCompiler(BaseCompiler):
    """
    Java compiler using javac.

    Note: Compiles .java files to .class files in the base directory.
    Does not create directories - assumes compilation directory exists.
    """

    @property
    def language_name(self) -> str:
        return "Java"

    @property
    def supported_extensions(self) -> Set[str]:
        return {".java"}

    def build_compile_command(
        self,
        source_paths: List[Path],
        output_path: Path,
        **kwargs
    ) -> List[str]:
        """
        Build javac compilation command.

        Args:
            source_paths: Java source files
            output_path: Output directory (base_dir)
            **kwargs: Additional compiler options

        Returns:
            Compilation command
        """
        compiler = shutil.which("javac")
        if not compiler:
            raise FileNotFoundError("javac compiler not found")

        cmd = [compiler]

        # Add source files
        cmd.extend([str(src) for src in source_paths])

        # Add any additional flags
        extra_flags = kwargs.get("extra_flags", [])
        if extra_flags:
            cmd.extend(extra_flags)

        return cmd


class CompilerRegistry:
    """
    Registry for managing language compilers.

    Provides a centralized way to get the appropriate compiler
    for a given language, making it easy to add new languages.
    """

    def __init__(self, base_dir: Path, timeout_sec: int = 180, max_output_bytes: int = 300_000):
        self.base_dir = base_dir
        self.timeout_sec = timeout_sec
        self.max_output_bytes = max_output_bytes
        self._compilers: Dict[str, BaseCompiler] = {}
        self._initialize_compilers()

    def _initialize_compilers(self):
        """Initialize all available compilers."""
        compiler_classes = [CppCompiler, JavaCompiler]

        for compiler_class in compiler_classes:
            compiler = compiler_class(
                self.base_dir,
                self.timeout_sec,
                self.max_output_bytes
            )
            # Register by language name in lowercase
            language_key = compiler.language_name.lower().replace("+", "p")
            self._compilers[language_key] = compiler

    def get_compiler(self, language: str) -> Optional[BaseCompiler]:
        """
        Get compiler for the specified language.

        Args:
            language: Language name (case-insensitive)

        Returns:
            BaseCompiler instance or None if not supported
        """
        return self._compilers.get(language.lower())

    def supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self._compilers.keys())

    def compile(
        self,
        language: str,
        source_paths: List[Path],
        output_path: Path,
        **options
    ) -> CompilationResult:
        """
        Compile code using the appropriate compiler.

        Args:
            language: Target language
            source_paths: List of source file paths
            output_path: Output file/directory path
            **options: Language-specific compilation options

        Returns:
            CompilationResult object
        """
        compiler = self.get_compiler(language)

        if compiler is None:
            start = time.monotonic()
            supported = ", ".join(self.supported_languages())
            return CompilationResult(
                status="error",
                returncode=None,
                stdout="",
                stderr=f"Unsupported language: {language}. Supported languages: {supported}",
                duration_sec=round(time.monotonic() - start, 6),
                cmd=[],
                source_paths=[str(p) for p in source_paths],
                output_path=str(output_path)
            )

        return compiler.compile(source_paths, output_path, **options)
