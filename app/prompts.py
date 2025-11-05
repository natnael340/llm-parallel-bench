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