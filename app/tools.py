import time
import sys
import subprocess
import shutil
from typing import Literal, List, Optional
from typing_extensions import Annotated
from datetime import datetime

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage

from pathlib import Path
from pydantic import BaseModel, Field
from app.prompts import WRITE_TODO_TOOL_DESC, WRITE_FILE_TOOL_DESC, COMPILE_CODE_TOOL_DESC
from app.state import Todo, State
from app._utils import CodeRunner
from app.utils.compiler import CompilerRegistry

BASE_DIR = Path("~/projects/llm-parallel-bench/llm_written").expanduser().resolve()
SETUP_DIR = BASE_DIR / ".setup"
CSHARP_PROJECT_DIR = SETUP_DIR / "llm_written.csproj"
GO_MOD_DIR = SETUP_DIR
TIMEOUT_SEC = 180
MAX_OUTPUT_BYTES = 300_000


_global_runner: Optional[CodeRunner] = None
_global_compiler: Optional[CompilerRegistry] = None

def get_runner() -> CodeRunner:
    """Get or create the global runner instance."""
    global _global_runner
    if _global_runner is None:
        _global_runner = CodeRunner()
    return _global_runner

def get_compiler() -> CompilerRegistry:
    global _global_compiler
    if _global_compiler is None:
        _global_compiler = CompilerRegistry(BASE_DIR, TIMEOUT_SEC, MAX_OUTPUT_BYTES)
    
    return _global_compiler

def configure_runner(
    base_dir: Optional[Path] = None,
    timeout_sec: int = 30,
    max_output_length: int = 10000
):
    """Configure the global runner instance."""
    global _global_runner
    _global_runner = CodeRunner(base_dir, timeout_sec, max_output_length)


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


@tool("write_file", description=WRITE_FILE_TOOL_DESC)
def write_file(filename: str, content: str)-> str:
    """
    Write code block into a file and save it.

    Args:
        filename: filename of the file with extension. eg: linearsearch.py, bfs.go
        content: full code content to be written to the file.
    """
    try:
        safe_name = Path(filename).name
        if not safe_name:
            return "❌ ERROR: Invalid filename."

        # Restrict writing to configuration files
        restricted_files = {"cargo.toml", "go.mod"}
        restricted_extensions = {".csproj"}

        if safe_name.lower() in restricted_files:
            return f"❌ ERROR: Cannot modify configuration file '{safe_name}'. Configuration files like Cargo.toml, go.mod, and .csproj are managed by the system."

        if Path(safe_name).suffix.lower() in restricted_extensions:
            return f"❌ ERROR: Cannot modify .csproj files. Configuration files are managed by the system."

        path = (BASE_DIR / safe_name).resolve()

        if path.parent != BASE_DIR:
            return "❌ ERROR: Invalid filepath."

        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8", newline="\n") as f:
            n = f.write(content)

        return f"✅ SUCCESS: File '{safe_name}' written ({n} bytes) at {path}."

    except Exception as e:
        return f"❌ ERROR: {str(e)}"
    

@tool
def run_code(filenames: List[str], language: Literal['python', 'go', 'cpp', 'csharp', 'java', "rust"]):
    """
    Run a program and capture stdout/stderr.

    Args:
        filenames: List of program entry files or binaries.
                   - Python: Single .py file (list should have 1 element)
                   - Go: One or more .go files to compile and run together
                   - C++: Single compiled binary (list should have 1 element)
                   - C#: One or more .cs files (validated, but all .cs in BASE_DIR are compiled)
                   - Java: One or more .java files
                   - Rust:  One or more .rs files (validated, but only the entry file `main.rs` will be run)
        language: One of 'python' | 'go' | 'cpp' | 'csharp' | 'java' | 'rust.

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
    
    runner = get_runner()
    return runner.run(filenames, language)

@tool("compile_code", description=COMPILE_CODE_TOOL_DESC)
def compile_code(source_files: List[str], output_file: str, language: Literal["C++", "Java"], openmp: Literal["on", "off"] = "off"):
    """
    Compiler tool to compile C++ and Java program into binary file and bytecode.

    Args:
        source_files: List of source filenames.
        output_file: Output binary name
        language: C++ or Java
        openmp: Force OpenMP on/off only for C++

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

    compiler = get_compiler()
    # Convert string paths to Path objects
    src_paths = [_safe_path(src_file) for src_file in source_files]
    # For Java, output_file can be empty string (generates .class files in source directory)
    out_path = BASE_DIR if output_file == "" else _safe_path(output_file)

    result =  compiler.compile(language, src_paths, out_path, openmp=openmp)

    return result.to_dict()

@tool
def compile_code_v0(source_files: List[str], output_file: str, openmp: Literal["on", "off"] = "off"):
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
            "output_path": str(out_path) if out_path else "",
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
        candidate = BASE_DIR / filename
        path = _safe_path(str(candidate))
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
    

@tool(description=WRITE_TODO_TOOL_DESC)
def  write_todos(todos: list[Todo], tool_call_id: Annotated[str, InjectedToolCallId]):
    """
    Create or update the agent's TODO list for task planning and tracking.

    Args:
        todos: List of Todo items with content and status
        tool_call_id: Tool call identifier for message response

    Returns:
        Command to update agent state with new TODO list
    """

    return Command(
        update={
            "todos": todos,
            "messages": [
                ToolMessage(f"Updated TODO list to {todos}.", tool_call_id=tool_call_id)
            ]
        }
    )

@tool(parse_docstring=True)
def read_todos(state: Annotated[State, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]):
    """Read the current TODO list from the agent state.

    This tool allows the agent to retrieve and review the current TODO list
    to stay focused on remaining tasks and track progress through complex workflows.

    Args:
        state: Injected agent state containing the current TODO list
        tool_call_id: Injected tool call identifier for message tracking

    Returns:
        Formatted string representation of the current TODO list
    """
    todos = state.get("todos", [])
    if not todos:
        return "No todos currently in the list."
    
    result = "Current TODO list:\n"
    status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}
    for idx, todo in enumerate(todos, start=1):
        emoji = status_emoji.get(todo["status"], "❓")
        result += f"{idx}. {emoji} {todo['content']} ({todo['status']})\n"
    
    return result.strip()

@tool(parse_docstring=True)
def ls():
    """
    List all files in the working directory.
    """
    file_list = [p.name for p in BASE_DIR.iterdir() if p.is_file()]
    if not file_list:
        return "No files found in the working directory."
    
    result = "Current files in working directory:\n"
    for fname in file_list:
        result += f"📁 {fname}\n"
    
    return result.strip()


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?
    - How complex is the question: Have I reached the number of search limits?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    # if the file don't exist we create it, the dir always exist dont worry
    
    with open(BASE_DIR / ".logs/reflections.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {reflection}\n---\n")
    return f"Reflection recorded: {reflection}"


@tool
def rm(filename: str) -> str:
    """
    Remove a file from the working directory.

    Args:
        filename: Name of the file to remove
    """
    try:
        path = _safe_path(filename)
        if not path.exists():
            return f"❌ ERROR: File '{filename}' does not exist."
        if path.is_dir():
            return f"❌ ERROR: '{filename}' is a directory."

        path.unlink()
        return f"✅ SUCCESS: File '{filename}' removed."
    except Exception as e:
        return f"❌ ERROR: {str(e)}"


configure_runner(base_dir=BASE_DIR, timeout_sec=TIMEOUT_SEC, max_output_length=MAX_OUTPUT_BYTES)