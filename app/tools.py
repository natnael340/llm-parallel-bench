import time
import sys
import subprocess
import shutil
from langchain_core.tools import tool
from typing import Literal, List, Dict
from pathlib import Path
from pydantic import BaseModel, Field, constr

BASE_DIR = Path("~/projects/llm-parallel-bench/llm_written").expanduser().resolve()
TIMEOUT_SEC = 60
MAX_OUTPUT_BYTES = 300_000


class WriteCodeArgs(BaseModel):
    filename: str = Field(
        ..., description="Target file path to write. Include extension, e.g. 'main.cpp'.", min_length=1, strip_whitespace=True
    )
    content: str = Field(
        ..., description="The FULL file contents to write (overwrite).", min_length=1
    )


def _safe_path(filename: str) -> Path:
    """
    Resolve a path under BASE_DIR; strip any path traversal.
    Accepts either a bare filename or an absolute path already inside BASE_DIR.
    """
    p = Path(filename).expanduser()
    if not p.is_absolute():
        p = (BASE_DIR / p.name).resolve()
    else:
        p = p.resolve()
    if p == BASE_DIR:
        raise FileNotFoundError("Empty or invalid filename.")
    if BASE_DIR not in p.parents:
        raise PermissionError("Path escapes workspace.")
    return p


def _truncate(s: str, limit: int = MAX_OUTPUT_BYTES) -> str:
    if s is None:
        return ""
    b = s.encode("utf-8", errors="replace")
    if len(b) <= limit:
        return s
    head = limit // 2
    tail = limit - head - len("\n...\n".encode())
    return (b[:head] + b"\n...\n" + b[-tail:]).decode("utf-8", errors="replace")


@tool("write_code", args_schema=WriteCodeArgs)
def write_code(filename: str, content: str)-> Dict:
    """
    Write code block into a file and save it.

    Args:
        filename: filename of the file with extension. eg: linearsearch.py, bfs.go
        content: full code content to be written to the file.
    """
    try:
        safe_name = Path(filename).name
        if not safe_name:
            return {"status": "error", "error": "Empty filename"}
        path = (BASE_DIR / safe_name).resolve()

        if BASE_DIR not in path.parents and path != BASE_DIR / safe_name:
            return {"status": "error", "error": "Invalid path"}

        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8", newline="\n") as f:
            n = f.write(content)

        extra = {}
        if safe_name.endswith(".go"):
            extra["go_module"] = "github.com/natnael340/llm-parallel-bench"

        result = {"status": "successful", "bytes_written": n, "path": str(path)}
        result.update(extra)

        return result
    
    except Exception as e:
        return {"status": "error", "error": str(e)}
    

@tool
def run_code(filename: str, language: Literal['python', 'go', 'cpp']):
    """
    Run a program and capture stdout/stderr.

    Args: 
        filename: Program entry file or binary.
        language: One of 'python' | 'go' | 'cpp'.

    Returns: dict with keys:
        - status: "successful" | "error"
        - returncode: int | None
        - stdout: str (truncated if large)
        - stderr: str (truncated if large)
        - duration_sec: float
        - cmd: list[str] (actual command executed)
        - path: str (resolved path used)
        - note: str (optional details)
    """
    print("run_code", filename)
    start = time.monotonic()
    try:
        path = _safe_path(filename)

        if language == "python":
            cmd = [sys.executable, str(path)]
        elif language == "go":
            cmd = ["go", "test", "-v", "."]
        elif language == "cpp":
            cmd = [str(path)]
        else:
            return {
                "status": "error",
                "returncode":None,
                "stdout": "",
                "stderr": f"Unsupported language (f{language})",
                "duration_sec": duration,
                "cmd": "",
                "path": str(path),
            }
        
        proc = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC
        )

        duration = round(time.monotonic() - start, 6)

        return {
            "status": "successful" if proc.returncode == 0 else "error",
            "returncode": proc.returncode,
            "stdout": _truncate(proc.stdout),
            "stderr": _truncate(proc.stderr),
            "duration_sec": duration,
            "cmd": cmd,
            "path": str(path),
        }
    except subprocess.TimeoutExpired as e:
        duration = round(time.monotonic() - start, 6)
        out = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or "")
        err = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, (bytes, bytearray)) else (e.stderr or "")

        return {
            "status": "error",
            "returncode": None,
            "stdout": _truncate(out),
            "stderr": _truncate(err) + "\n[Timeout]",
            "duration_sec": duration,
            "cmd": getattr(e, "cmd", []),
            "path": filename,
        }
    
    except FileNotFoundError as e:
        duration = round(time.monotonic() - start, 6)
        return {
            "status": "error",
            "returncode": None,
            "stdout": "",
            "stderr": str(e),
            "duration_sec": duration,
            "cmd": [],
            "path": filename,
        }
    except PermissionError as e:
        duration = round(time.monotonic() - start, 6)
        return {
            "status": "error",
            "returncode": None,
            "stdout": "",
            "stderr": f"Permission error: {e}",
            "duration_sec": duration,
            "cmd": [],
            "path": filename,
        }
    except Exception as e:
        duration = round(time.monotonic() - start, 6)
        return {
            "status": "error",
            "returncode": None,
            "stdout": "",
            "stderr": f"Unexpected error: {e}",
            "duration_sec": duration,
            "cmd": [],
            "path": filename,
        }

@tool
def compile_code(source_files: List[str], output_file: str, openmp: Literal["on", "off"] = "off"):
    """
    Compile C++ program into binary file.

    Args:
        source_files: List of C++ source filenames.
        output_file: Output binary name
        openmp: Force OpenMP on/off, 
    
    Returns: dict with keys:
        - status: "successful" | "error"
        - returncode: int | None
        - stdout: str (truncated if large)
        - stderr: str (truncated if large)
        - duration_sec: float
        - cmd: list[str] (actual command executed)
        - source_paths: list[str] (resolved source paths used)
        - output_path: str (resolved output path used)
    """

    start = time.monotonic()
    try:
        if not source_files:
            return {
                "status": "error",
                "returncode": None,
                "stdout": "",
                "stderr": "No source file provided",
                "duration_sec": round(time.monotonic() - start, 6),
                "cmd": [],
                "source_paths": source_files,
                "output_path": output_file,
            }
        
        src_paths = [_safe_path(src_file) for src_file in source_files]
        out_path = _safe_path(output_file)
        if any([src_path.suffix.lower() not in {".cpp", ".cc", ".cxx", 'c++'} for src_path in src_paths]):
            return {
                "status": "error",
                "returncode": None,
                "stdout": "",
                "stderr": "Expected a C++ source file (.cpp).",
                "duration_sec": round(time.monotonic() - start, 6),
                "cmd": [],
                "source_paths": [str(path) for path in src_paths],
                "output_path": str(out_path),
            } 
        
        out = out_path.with_suffix("")
        if sys.platform.startswith("win"):
            out = out.with_suffix("exe")
        
        cxx = shutil.which("g++")
        base_cmd = [cxx, "-O3"]
        if openmp == "on":
            base_cmd.append("-fopenmp")
        base_cmd.extend([str(src) for src in src_paths])
        base_cmd += ["-o", str(out)]


        
        try:
            proc = subprocess.run(
                base_cmd,
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SEC,
            )
            duration = round(time.monotonic() - start, 6)
            if proc.returncode == 0:
                return {
                    "status": "successful",
                    "returncode": 0,
                    "stdout": _truncate(proc.stdout),
                    "stderr": _truncate(proc.stderr),
                    "duration_sec": duration,
                    "cmd": base_cmd,
                    "source_paths": [str(path) for path in src_paths],
                    "output_path": str(out_path),
                }
            return {
                "status": "error",
                "returncode": proc.returncode,
                "stdout": _truncate(proc.stdout),
                "stderr": _truncate(proc.stderr),
                "duration_sec": duration,
                "cmd": base_cmd,
                "source_paths": [str(path) for path in src_paths],
                "output_path": str(out_path),
            }
        except subprocess.TimeoutExpired as e:
            duration = round(time.monotonic() - start, 6)
            out_s = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or "")
            err_s = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, (bytes, bytearray)) else (e.stderr or "")
            return {
                "status": "error",
                "returncode": None,
                "stdout": _truncate(out_s),
                "stderr": _truncate(err_s) + "\n[Timeout]",
                "duration_sec": duration,
                "cmd": getattr(e, "cmd", base_cmd),
                "source_paths": [str(path) for path in src_paths],
                "output_path": str(out_path),
            }
    except FileNotFoundError as e:
        return {
            "status": "error",
            "returncode": None,
            "stdout": "",
            "stderr": str(e),
            "duration_sec": round(time.monotonic() - start, 6),
            "cmd": [],
            "source_paths": [str(path) for path in src_paths],
            "output_path": str(out_path),
        }
    except PermissionError as e:
        return {
            "status": "error",
            "returncode": None,
            "stdout": "",
            "stderr": f"Permission error: {e}",
            "duration_sec": round(time.monotonic() - start, 6),
            "cmd": [],
            "source_paths": [str(path) for path in src_paths],
            "output_path": str(out_path),
        }
    except Exception as e:
        return {
            "status": "error",
            "returncode": None,
            "stdout": "",
            "stderr": f"Unexpected error: {e}",
            "duration_sec": round(time.monotonic() - start, 6),
            "cmd": [],
            "source_paths": [str(path) for path in src_paths],
            "output_path": str(out_path),
        }
    

@tool
def list_files():
    """
    List files in current directory.

    Returns:
        status: successful | error
        files: List[str] filenames in current directory
        stderr(optional): error report if an error occurred
    """
    try:
        files = sorted(
            [p.name for p in BASE_DIR.iterdir() if p.is_file()],
            key=str.lower,
        )
        return {"status": "successful", "files": files}
    except PermissionError as e:
        return {"status": "error", "files": [], "stderr": f"Permission error: {e}"}
    except Exception as e:
        return {"status": "error", "files": [], "stderr": f"Unexpected error: {e}"}


@tool
def read_file(filename: str):
    """
    Read content of a file

    Args:
        - filename: str filename
    Returns: 
        - status: successful | error
        - content: str content of the file
        - stderr(optional): str error
    """

    try:
        path = _safe_path(filename)
        if not path.exists():
            return {"status": "error", "content": "", "stderr": "File does not exist"}
        elif path.is_dir():
            return {"status": "error", "content": "", "stderr": "File is a directory."}

        with open(path, "r") as file:
            content = file.read()

        return {"status": "successful", "content": content, "stderr": ""}
    except PermissionError as e:
        return {"status": "error", "path": str(path), "stderr": f"Permission error: {e}"}
    except Exception as e:
        return {"status": "error", "path": str(path), "stderr": f"Unexpected error: {e}"}
    