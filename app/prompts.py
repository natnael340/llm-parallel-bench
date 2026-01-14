#===============================================================#
#               TOOL PROMPTS                                    #
#===============================================================#


WRITE_TODO_TOOL_DESC = """
Create and manage structured task lists for tracking progress through complex workflows.

## When to Use
- Multi-step or non-trivial tasks requiring coordination
- When user provides multiple tasks or explicitly requests todo list  
- Avoid for single, trivial actions unless directed otherwise

## Structure
- Maintain one list containing multiple todo objects (content, status, id)
- Use clear, actionable content descriptions
- Status must be: pending, in_progress, or completed

## Best Practices  
- Only one in_progress task at a time
- Mark completed immediately when task is fully done
- Always send the full updated list when making changes
- Prune irrelevant items to keep list focused

## Progress Updates
- Call TodoWrite again to change task status or edit content
- Reflect real-time progress; don't batch completions  
- If blocked, keep in_progress and add new task describing blocker

## Parameters
- todos: List of TODO items with content and status fields

## Returns
Updates agent state with new todo list.
"""

WRITE_FILE_TOOL_DESC = """
Create and save files of any type by writing provided content into a specified filename.

## When to Use
- When persistent storage of data, code, or documents is needed
- To save outputs from computations, code generation, or data processing
- For intermediate results that may be read later

## Structure
- Each call writes or updates exactly one file
- Requires both filename (with extension) and full file content
- Supports any text-based file type (e.g., .py, .go, .txt, .json, .md, .csv)

## Best Practices
- Use clear, descriptive filenames with proper extensions
- Ensure content is complete and valid for the intended file type
- Overwrite only when intentional; confirm before replacing critical files
- Keep content formatted and structured for readability and usability

## Progress Updates
- Call WriteFile again to update or replace file content
- Treat each call as an atomic write (no partial updates)
- If blocked (e.g., invalid filename), retry with corrected parameters

## Parameters
- filename: Target filename including extension (e.g., notes.txt, config.json, linearsearch.py)
- content: Full file content to be written

## Returns
A status message string indicating whether the action was successful or not.
"""

COMPILE_CODE_TOOL_DESC = """
Compile C++ or Java source files into a runnable output (C++) or bytecode (.class) (Java).

## When to Use
- When you need to compile existing C++ or Java source files before running/testing
- To compile multiple C++ files into one executable
- To compile one or more Java files into .class files

## Structure
- Each call compiles the provided `source_files` using the selected `language`
- All source files must exist and have extensions valid for that language
- Output behavior depends on language:
  - C++: produces a single executable at `output_file` (adds .exe on Windows)
  - Java: produces `.class` files **in the same directory as each `.java` source file**; `output_file` is **not used**

## Best Practices
- Use clear, descriptive filenames with correct extensions:
  - C++: .cpp, .cc, .cxx, .c++
  - Java: .java
- Keep `language` consistent with the file extensions in `source_files`
- Use `openmp="on"` only for C++ code that uses OpenMP; otherwise keep it "off"
- Do not rely on `output_file` to control Java output; Java outputs `.class` files via `javac -d <base_dir>`

## Progress Updates
- Re-run CompileCode after changing any source file to rebuild outputs
- If compilation fails, fix the sources and retry
- Use `stderr` and `returncode` to guide fixes; `stdout` may include compiler notes/warnings

## Parameters
- source_files: List of source filenames to compile (e.g., ["main.cpp", "utils.cc"] or ["BFS.java"])
- output_file:
  - C++: destination executable name/path (e.g., "bfs", "bin/bfs")
  - Java: accepted but ignored (output is `.class` files in the base directory)
- language: "C++" or "Java"
- openmp: "on" | "off" (C++ only; ignored for Java)

## Returns
A dictionary with:
- status: "successful" | "error"
- returncode: int | None
- stdout: str (truncated if large)
- stderr: str (truncated if large)
- duration_sec: float
- cmd: list[str] (actual command executed)
- source_paths: list[str] (resolved source paths used)
- output_path: str (resolved output path used)
"""
