
from typing import List, Literal, Annotated
from typing_extensions import TypedDict
import operator

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class ReviewModel(BaseModel):
    verdict: Literal["DONE", "REVISE"]
    issues: List[str] = Field(default_factory=list)            # short bullets
    required_changes: List[str] = Field(default_factory=list)


class ReviewState(TypedDict):
    verdict: Literal["DONE", "REVISE"]
    issues: List[str]
    required_changes: List[str]


class ManualTestSummary(BaseModel):
    issues: List[str] = []
    required_changes: List[str] = []

class State(TypedDict):
    messages: Annotated[list, add_messages]
    original_src: str
    last_candidate: str
    review: ReviewState
    k: Annotated[int, operator.add]
