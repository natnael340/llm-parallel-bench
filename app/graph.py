from dotenv import load_dotenv
from typing import Optional

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


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
from app.consts import MONO_AGENT, MONO_AGENT_V2, MONO_AGENT_V3, TEMPERATURE
from app.state import State



TOOLS = [write_file, read_file, run_code, compile_code, ls, write_todos, read_todos, think_tool, rm]

def get_model(model: str):
    model_map = {
        "openai:gpt-5": ChatOpenAI(model_name="gpt-5", temperature=TEMPERATURE),
        "anthropic:claude-sonnet-4-5-20250929": ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=TEMPERATURE),
        "google_genai:gemini-2.5-pro": ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=TEMPERATURE),
    }

    return model_map.get(model)

def get_agent(model: str, checkpointer: Optional[BaseCheckpointSaver] = None):
    load_dotenv(".env")

    if checkpointer is None:
        checkpointer = MemorySaver()

    model = get_model(model)
    
    return create_agent(
        model, 
        tools=TOOLS, 
        system_prompt=MONO_AGENT_V3, 
        checkpointer=checkpointer,
        state_schema=State,
    )