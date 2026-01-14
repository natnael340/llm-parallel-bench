import sys
import time
import subprocess
from typing import List, Union, Dict, Tuple, Any, Literal, Optional, Annotated
from pathlib import Path
from abc import ABC, abstractmethod

from langchain_core.messages.ai import AIMessageChunk
from langchain_core.messages.tool import ToolMessage


def content_to_text(content: Union[str, List[Dict[str, str]], AIMessageChunk]) -> str:
    if content is None:
        return ""
    
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                continue

            btype = getattr(block, "type", None)
            if btype == "text":
                parts.append(getattr(block, "text", "") or "")

        return "".join(parts)
    elif isinstance(content, AIMessageChunk):
        return content.text()
    else:
         print(content)
    
    return ""


def validate_single_file(paths: List[Path], language: str) -> Tuple[bool, str, Path]:
    """
    Validate that exactly one file is provided and it exists.
    
    :param paths: List of file paths.
    :param language: Language of the file.

    :return is_valid: True if valid, False otherwise.
    :return error_message: Error message if not valid, empty string otherwise.
    :return file_path: The valid file path if valid, None otherwise.
    """
    if len(paths) != 1:
        return False, f"[{language}] execution expects exactly 1 file, got {len(paths)}", paths[0] if paths else None

    file_path = paths[0]

    if not file_path.exists():
        return False, f"[{language}] file not found: {file_path}", file_path
    
    if not file_path.is_file():
        return False, f"[{language}] Path is not a file: {file_path}", file_path
    
    return True, "", file_path


def validate_multiple_files(paths: List[Path], language: str) -> Tuple[bool, str]:
    """
    Validate that all provided files exist.

    :param paths: List of file paths.
    :param language: Language of the files.

    :return is_valid: True if all files are valid, False otherwise.
    :return error_message: Error message if not valid, empty string otherwise.
    """
    for path in paths:
        if not path.exists():
            return False, f"[{language}] file not found: {path}"
        if not path.is_file():
            return False, f"[{language}] Path is not a file: {path}"
    
    return True, ""


def handle_python(paths: List[Path], path_str: List[str]) -> Dict[str, Any]:
    is_valid, error_message, file_path = validate_single_file(paths, "Python")

    if not is_valid:
        return {
            "success": False,
            "error": error_message,
            "path": str(file_path) if file_path else "",
        }
    
    return {
        "": True,
        "error": "",
        "path": str(file_path),
    }


class LanguageHandler(ABC):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
    
    @abstractmethod
    def validate_and_setup(self, paths: List[Path]) -> Dict[str, Any]:
        pass

    def _validate_single_file(self, paths: List[Path], lang_name: str):
        """Validate that exactly one file is provided and it exists."""
        if len(paths) != 1:
            return False, f"{lang_name} execution expects exactly 1 file, got {len(paths)}", None
        
        file_path = paths[0]
        if not file_path.exists():
            return False, f"{lang_name} file not found: {file_path}", file_path
        if not file_path.is_file():
            return False, f"Path is not a file: {file_path}", file_path
        
        return True, "", file_path
    
    def _validate_multiple_files(self, paths: List[Path], lang_name: str):
        """Validate that all provided files exist."""
        for path in paths:
            if not path.exists():
                return False, f"{lang_name} file not found: {path}"
            if not path.is_file():
                return False, f"Path is not a file: {path}"
        return True, ""

class PythonHandler(LanguageHandler):
    def validate_and_setup(self, paths: List[Path]) -> Dict[str, Any]:
        is_valid, error_msg, py_file = self._validate_single_file(paths, "Python")
        if not is_valid:
            return {"error": error_msg}
        
        return {
            "cmd": [sys.executable, str(py_file)],
            "cwd": str(self.base_dir),
        }

class GoHandler(LanguageHandler):
    """Handler for Go code execution."""
    
    def validate_and_setup(self, paths: List[Path]) -> Dict[str, Any]:
        is_valid, error_msg = self._validate_multiple_files(paths, "Go")
        if not is_valid:
            return {"error": error_msg}
        
        return {
            "cmd": ["go", "run"] + [p.name for p in paths],
            "cwd": str(self.base_dir),
        }

class CppHandler(LanguageHandler):
    """Handler for C++ binary execution."""
    
    def validate_and_setup(self, paths: List[Path]) -> Dict[str, Any]:
        is_valid, error_msg, binary_path = self._validate_single_file(paths, "C++")
        if not is_valid:
            return {"error": error_msg}
        
        # Make executable
        try:
            binary_path.chmod(binary_path.stat().st_mode | 0o111)
        except Exception as e:
            return {"error": f"Could not make binary executable: {e}"}
        
        return {
            "cmd": [str(binary_path)],
            "cwd": str(self.base_dir),
        }
    
class CSharpHandler(LanguageHandler):
    """Handler for C# code execution."""
    
    def __init__(self, base_dir: Path, project_dir: Path):
        super().__init__(base_dir)
        self.project_dir = project_dir
    
    def validate_and_setup(self, paths: List[Path]) -> Dict[str, Any]:
        if not self.project_dir.exists():
            return {
                "error": f"C# project not found at {self.project_dir}. "
                        f"Please ensure .setup/llm_written.csproj exists."
            }
        
        is_valid, error_msg = self._validate_multiple_files(paths, "C#")
        if not is_valid:
            return {"error": error_msg}
        
        return {
            "cmd": ["dotnet", "run", "--project", str(self.project_dir)],
            "cwd": str(self.base_dir),
        }


class JavaHandler(LanguageHandler):
    """Handler for Java code execution."""

    def validate_and_setup(self, paths: List[Path]) -> Dict[str, Any]:
        is_valid, error_msg = self._validate_multiple_files(paths, "Java")
        if not is_valid:
            return {"error": error_msg}

        # Use stem to get class name without extension (.java or .class)
        return {
            "cmd": ["java"] + [p.stem for p in paths],
            "cwd": str(self.base_dir),
        }

class RustHandler(LanguageHandler):
    """Handler for Rust code execution."""
    def __init__(self, base_dir: Path, manifest_path: Path):
        super().__init__(base_dir)
        self.manifest_path = manifest_path

    def validate_and_setup(self, paths: List[Path]) -> Dict[str, Any]:
        # Validate source files exist
        is_valid, error_msg = self._validate_multiple_files(paths, "Rust")
        if not is_valid:
            return {"error": error_msg}

        # cargo run doesn't need file paths - they're specified in Cargo.toml
        return {
            "cmd": ["cargo", "run", "--manifest-path", str(self.manifest_path)],
            "cwd": str(self.base_dir),
        }

class CodeRunner:
    """Internal code runner implementation."""
    
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        timeout_sec: int = 30,
        max_output_length: int = 10000
    ):
        self.base_dir = base_dir or Path.cwd()
        self.timeout_sec = timeout_sec
        self.max_output_length = max_output_length
        
        # Setup language handlers
        csharp_project_dir = self.base_dir / ".setup"
        rust_manifest_path = self.base_dir / ".setup/Cargo.toml" 
        self.handlers: Dict[str, LanguageHandler] = {
            "python": PythonHandler(self.base_dir),
            "go": GoHandler(self.base_dir),
            "cpp": CppHandler(self.base_dir),
            "csharp": CSharpHandler(self.base_dir, csharp_project_dir),
            "java": JavaHandler(self.base_dir),
            "rust": RustHandler(self.base_dir, rust_manifest_path),
        }
    
    def run(
        self,
        filenames: List[str],
        language: str
    ) -> Dict[str, Any]:
        """Execute code and return result dictionary."""
        start = time.monotonic()
        
        # Validate input
        if not filenames:
            return self._error_result(
                "No filename provided",
                start_time=start,
                paths=[]
            )
        
        # Convert to paths
        paths = [self._safe_path(filename) for filename in filenames]
        paths_str = [str(p) for p in paths]
        
        # Get language handler
        handler = self.handlers.get(language)
        if not handler:
            return self._error_result(
                f"Unsupported language: {language}",
                start_time=start,
                paths=paths_str
            )
        
        # Setup command using language handler
        setup_result = handler.validate_and_setup(paths)
        
        # Check if handler returned an error
        if "error" in setup_result:
            return self._error_result(
                setup_result["error"],
                start_time=start,
                paths=paths_str
            )
        
        # Execute the command
        return self._execute_command(
            setup_result["cmd"],
            setup_result["cwd"],
            paths_str
        )
    
    def _safe_path(self, filename: str) -> Path:
        """Convert filename to safe Path object."""
        path = Path(filename)

        if path.is_absolute():
            return path.resolve()
    
        resolved = (self.base_dir / path).resolve()

        return resolved
    
    def _truncate(self, text: str) -> str:
        """Truncate text if too long."""
        if len(text) <= self.max_output_length:
            return text
        half = self.max_output_length // 2
        return (
            text[:half] +
            f"\n... [truncated {len(text) - self.max_output_length} chars] ...\n" +
            text[-half:]
        )
    
    def _error_result(
        self,
        error_msg: str,
        start_time: float,
        paths: List[str],
        cmd: Optional[List[str]] = None,
        returncode: Optional[int] = None,
        stdout: str = "",
        note: str = ""
    ) -> Dict[str, Any]:
        """Create an error result."""
        duration = round(time.monotonic() - start_time, 6)
        result = {
            "status": "error",
            "returncode": returncode,
            "stdout": stdout,
            "stderr": error_msg,
            "duration_sec": duration,
            "cmd": cmd or [],
            "paths": paths,
        }
        if note:
            result["note"] = note
        return result
    
    def _execute_command(
        self,
        cmd: List[str],
        cwd: str,
        paths: List[str]
    ) -> Dict[str, Any]:
        """Execute a command and return structured result."""
        start = time.monotonic()
        
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec
            )
            
            duration = round(time.monotonic() - start, 6)
            
            return {
                "status": "successful" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
                "stdout": self._truncate(proc.stdout),
                "stderr": self._truncate(proc.stderr),
                "duration_sec": duration,
                "cmd": cmd,
                "paths": paths,
            }
            
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or "")
            err = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, (bytes, bytearray)) else (e.stderr or "")
            
            return self._error_result(
                self._truncate(err) + f"\n[Timeout after {self.timeout_sec}s]",
                start_time=start,
                paths=paths,
                cmd=cmd,
                stdout=self._truncate(out),
                note="Process timed out"
            )
        
        except FileNotFoundError as e:
            return self._error_result(
                f"Command not found: {e}. Make sure the required runtime is installed.",
                start_time=start,
                paths=paths,
                cmd=cmd
            )
        
        except PermissionError as e:
            return self._error_result(
                f"Permission error: {e}",
                start_time=start,
                paths=paths,
                cmd=cmd
            )
        
        except Exception as e:
            return self._error_result(
                f"Unexpected error: {type(e).__name__}: {e}",
                start_time=start,
                paths=paths,
                cmd=cmd
            )