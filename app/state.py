
from uuid import uuid4
from typing import List, Literal, NotRequired, Dict
from typing_extensions import TypedDict
from dataclasses import dataclass, field

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


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_token: int = 0

    def update(self, usage: Dict[str, int]):
        self.input_tokens = usage.get("prompt_tokens", 0)
        self.output_tokens = usage.get("completion_tokens", 0)
        self.total_tokens = usage.get("total_tokens", 0)


@dataclass
class Session:
    thread_id: str = field(default_factory=lambda: uuid4().hex)
    messages: List[Dict] = field(default_factory=list)
    todos: List[Todo] = field(default_factory=list)
    files: List[File] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)