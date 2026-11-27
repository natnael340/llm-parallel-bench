from typing import List, Literal, NotRequired
from typing_extensions import TypedDict

from langchain.agents import AgentState


class Todo(TypedDict):
    content: str
    status: Literal['pending', 'in_progress', 'completed']


class File(TypedDict):
    file_name: str
    file_path: str
    size: int


class State(AgentState):
    todos: NotRequired[List[Todo]]
    files: NotRequired[List[File]]
