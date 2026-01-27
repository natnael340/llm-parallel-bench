from dotenv import load_dotenv
from typing import Optional

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.tools import (
    read_todos,
    write_todos,
    write_file, 
    read_file,
    compile_code,
    run_code,
    ls,
    rm,
    think_tool,
)
from app.consts import MONO_AGENT, MONO_AGENT_V2
from app.state import State



TOOLS = [write_file, read_file, run_code, compile_code, ls, write_todos, read_todos, think_tool, rm]

def get_agent(model: str, checkpointer: Optional[BaseCheckpointSaver] = None):
    load_dotenv(".env")

    if checkpointer is None:
        checkpointer = MemorySaver()
    
    return create_agent(
        model, 
        tools=TOOLS, 
        system_prompt=MONO_AGENT_V2, 
        checkpointer=checkpointer,
        state_schema=State,
    )