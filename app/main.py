
import json
from uuid import uuid4
from dataclasses import asdict
from typing import List

import streamlit as st
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.state import TokenUsage, File, Todo, Session
from app.graph import get_agent
    

def app() -> None:
    """Run the Streamlit application."""
    st.title("Sequential to Parallel Algo Converter")
    if "session" not in st.session_state:
        st.session_state.session = Session()

    with st.sidebar:
        st.subheader("Model")
        model = st.selectbox("Choose model:", ["GPT-5", "Claude 4.5 Sonnet", "Gemini 2.5 Pro"])
        model_map = {"GPT-5": "openai:gpt-5", "Claude 4.5 Sonnet": "anthropic:claude-sonnet-4-5-20250929", "Gemini 2.5 Pro": "google-gemini:gemini-2.5-pro"}
        st.subheader("TODOS")
        for item in st.session_state.session.todos:
            todo_icons = {"completed": "✅", "in_progress": "⚒️", "pending": "⬜"}       
            
            st.write(f"{todo_icons.get(item['status'], '⬜')} {item['content']}")

        st.divider()
        st.subheader("FILES")
        for f in st.session_state.session.files:
            st.write(f"📄 {f['file_name']} - {f['size']}")
        st.divider()

        st.subheader("USAGE")
        st.write(f"**Input tokens:** {st.session_state.session.usage.input_tokens}")
        st.write(f"**Output tokens:** {st.session_state.session.usage.output_tokens}")
        st.write(f"**Total tokens:** {st.session_state.session.usage.total_token}")

    config = {"configurable": {"thread_id": st.session_state.session.thread_id}, "recursion_limit": 50}

    
    # Display existing chat history
    # for message in st.session_state.messages:
    #     with st.chat_message(message["role"]):
    #         st.markdown(message["content"])

    # Prompt the user for input
    user_input = st.chat_input(f"Enter your sequential algorithm here and press enter...")
    if user_input:
        agent = get_agent(model_map.get(model))
        # Append the user's message to the session history
        st.session_state.session.messages.append({"role": "user", "content": user_input})
        # Display the user message immediately
        with st.chat_message("user"):
            st.code(user_input, language=None)

        message = {
            "messages": [("user", f"Parallelize the following sequential algorithm and write a test for it\n\n{user_input} Also give me a brief justification for the parallelization")],
        }
               

        with st.chat_message("assistant"):
            for state in agent.stream(message, config=config, stream_usage=True, stream_mode="values"):
                latest_message = state["messages"][-1]
                st.session_state.session.todos = state.get("todos", [])
                st.session_state.session.files = state.get("files", [])

                st.session_state.session.messages.append(latest_message)
                if isinstance(latest_message, AIMessage):
                    st.session_state.session.usage.update(latest_message.response_metadata["token_usage"])
                    if latest_message.content:
                        st.markdown(latest_message.content)
                            
                    if latest_message.tool_calls:
                        for tool_call in latest_message.tool_calls:
                            with st.expander(f"🧠 LLM Tool Call • {tool_call['name']}", expanded=False):
                                st.code(json.dumps(tool_call["args"], indent=2), language="json")
                            
                            
                elif isinstance(latest_message, ToolMessage):
                    with st.expander(f"🔧 Tool Result • {latest_message.name}", expanded=False):
                        st.code(latest_message.content)
                    
            


# When executed as a script, launch the Streamlit app.  This check
# allows the module to be imported without side effects during unit
# testing.
if __name__ == "__main__":
    app()