import os

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

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_model(model: str):
    # Built lazily so a missing key for one provider does not break the others.
    model_map = {
        "openai:gpt-5": lambda: ChatOpenAI(model_name="gpt-5", temperature=TEMPERATURE),
        "anthropic:claude-sonnet-4-5-20250929": lambda: ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=TEMPERATURE),
        "google_genai:gemini-2.5-pro": lambda: ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=TEMPERATURE),
        "openrouter:qwen/qwen3-coder": lambda: ChatOpenAI(
            model_name="qwen/qwen3-coder",
            temperature=TEMPERATURE,
            base_url=os.getenv("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL),
            api_key=os.environ["OPENROUTER_API_KEY"],
        ),
    }

    build_model = model_map.get(model)

    return build_model() if build_model else None

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