import streamlit as st
import json
import os
import logging
from uuid import uuid4

from app.state import State
from app.graph import agent_executor
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from app.utils import content_to_text


def _short(obj, n=800):
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= n else s[: n//2] + " … " + s[- n//2 :]

def app() -> None:
    """Run the Streamlit application."""
    st.title("Sequential to Parallel Code Converter")

    # Ensure session state exists for chat messages
    if "messages" not in st.session_state:
        st.session_state.messages: List[dict] = []  # type: ignore

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid4())
    
    
    config = {"configurable": {"thread_id": st.session_state.thread_id}, "recursion_limit": 50}

    # Display existing chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Prompt the user for input
    user_input = st.chat_input("Enter your sequential algorithm here and press enter...")
    if user_input:
        # Append the user's message to the session history
        st.session_state.messages.append({"role": "user", "content": user_input})
        # Display the user message immediately
        with st.chat_message("user"):
            st.markdown(user_input)

        message: State = {
            "messages": [("user", f"Parallelize the following sequential algorithm and write a test for it\n\n{user_input} Also give me a brief justification for the parallelization")],
        }

        with st.chat_message("assistant"):
            text_ph = st.empty()
            acc = ""
            
            with st.status("Tool calls...", state="running") as status:
                logs = st.container()
                
                for mode, chunk in agent_executor.stream(message, stream_mode=["updates", "messages"], config=config):
                    if mode == "messages":
                        msg, _meta = chunk
                        delta = getattr(msg, "content", None)

                        if delta:
                            acc += content_to_text(msg)
                            text_ph.markdown(acc)
                        continue
                        
                    elif mode == "updates":
                        update = chunk
                        for node, patch in update.items():
                            msgs = patch.get("messages", []) or []
                            for m in msgs:
                                
                                if isinstance(m, AIMessage) and m.tool_calls:
                                    with logs.expander(f"🧠 LLM tool calls @ {node}", expanded=True):
                                        st.code(_short(m.tool_calls), language="json")
                                # Tool finished and returned output
                                if isinstance(m, ToolMessage):
                                    with logs.expander(f"🔧 Tool result @ {node} ({m.name})"):
                                        st.code(_short(m.content), language="json")
            status.update(label="Done", state="complete", expanded=False)
            


# When executed as a script, launch the Streamlit app.  This check
# allows the module to be imported without side effects during unit
# testing.
if __name__ == "__main__":
    app()