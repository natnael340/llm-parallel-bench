
import logging

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

from app.tools import write_code, run_code, compile_code, list_files, read_file
from app.consts import AGENT_PROMPT

load_dotenv(".env")


# Choose the LLM that will drive the agent
#llm = ChatOpenAI(model="gpt-5") # openai
# llm = ChatAnthropic(model_name="claude-3-7-sonnet-latest")
# bound_llm = llm.bind_tools([write_code, run_code, compile_code, list_files, read_file])

llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")

checkpointer = MemorySaver()

agent_executor = create_react_agent(
    llm, 
    tools=[write_code, run_code, compile_code, list_files, read_file], 
    prompt=AGENT_PROMPT, 
    checkpointer=checkpointer
)