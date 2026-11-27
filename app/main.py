import io
import json
import zipfile
from pathlib import Path
from uuid import uuid4

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from app.graph import get_agent
from app.tools import BASE_DIR

MODELS = {
    "GPT-5": "openai:gpt-5",
    "Claude 4.5 Sonnet": "anthropic:claude-sonnet-4-5-20250929",
    "Gemini 2.5 Pro": "google_genai:gemini-2.5-pro",
    "Qwen3 Coder 480B A35B": "openrouter:qwen/qwen3-coder",
}
TODO_ICONS = {"completed": "✅", "in_progress": "⚒️", "pending": "⬜"}
LANGUAGES = {".py": "python", ".go": "go", ".cpp": "cpp", ".hpp": "cpp", ".h": "cpp",
             ".cs": "csharp", ".java": "java", ".rs": "rust", ".md": "markdown", ".json": "json"}


@st.cache_resource
def checkpointer():
    # shortcut: sessions live in server memory and are lost on restart; use SqliteSaver to keep them.
    return MemorySaver()


@st.cache_resource
def agent_for(model_key):
    return get_agent(model_key, checkpointer())


def saved_state(config):
    saved = checkpointer().get_tuple(config)
    return saved.checkpoint["channel_values"] if saved else {}


def language_of(filename):
    return LANGUAGES.get("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else None


def session_files(messages):
    """Names of the files this session wrote and has not removed, in the order they were first written."""
    names = {}  # a dict keeps insertion order and drops repeats
    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        for call in msg.tool_calls:
            name = Path(call["args"].get("filename", "")).name  # write_file saves under the base name
            if call["name"] == "write_file" and name:
                names.setdefault(name, None)
            elif call["name"] == "rm":
                names.pop(name, None)
    return list(names)


def token_totals(messages):
    usage = [m.usage_metadata for m in messages if isinstance(m, AIMessage) and m.usage_metadata]
    return {k: sum(u.get(k, 0) for u in usage) for k in ("input_tokens", "output_tokens", "total_tokens")}


def zip_of(paths):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, p.name)
    return buffer.getvalue()


def render_message(msg):
    if isinstance(msg, AIMessage):
        if msg.text:
            st.markdown(msg.text)
        for call in msg.tool_calls:
            args = call["args"]
            if call["name"] == "write_file":
                name = args.get("filename", "")
                with st.expander(f"📄 write_file • {name}"):
                    st.code(args.get("content", ""), language=language_of(name))
            else:
                with st.expander(f"🧠 Tool call • {call['name']}"):
                    st.code(json.dumps(args, indent=2), language="json")
    elif isinstance(msg, ToolMessage):
        with st.expander(f"🔧 Tool result • {msg.name}"):
            st.code(msg.text)


def render_history(messages):
    turn = None
    for msg in messages:
        if isinstance(msg, HumanMessage):
            st.chat_message("user").code(msg.text, language=None)
            turn = None
        else:
            turn = turn or st.chat_message("assistant")
            with turn:
                render_message(msg)


def show_progress(boxes, state):
    messages = state.get("messages", [])
    todos = state.get("todos", [])
    boxes["todos"].markdown("  \n".join(f"{TODO_ICONS.get(t['status'], '⬜')} {t['content']}" for t in todos)
                            or "_No TODOs yet_")
    boxes["files"].markdown("  \n".join(f"📄 {n}" for n in session_files(messages)) or "_No files yet_")
    u = token_totals(messages)
    boxes["usage"].markdown(f"**Input:** {u['input_tokens']:,}  \n**Output:** {u['output_tokens']:,}  \n"
                            f"**Total:** {u['total_tokens']:,}")


def show_downloads(box, names, session_id):
    paths = [BASE_DIR / n for n in names if (BASE_DIR / n).is_file()]
    if not paths:
        return
    with box.container():
        for p in paths:
            st.download_button(f"📄 {p.name}", p.read_bytes(), file_name=p.name, key=f"file-{p.name}")
        st.download_button("⬇ All files (.zip)", zip_of(paths), file_name=f"session-{session_id[:8]}.zip",
                           mime="application/zip", type="primary")


def app():
    st.title("Sequential to Parallel Algo Converter")
    session_id = st.query_params.get("session") or uuid4().hex
    st.query_params["session"] = session_id
    config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}
    state = saved_state(config)

    with st.sidebar:
        model = st.selectbox("Model", list(MODELS))
        if st.button("New session"):
            st.query_params["session"] = uuid4().hex
            st.rerun()
        st.caption(f"Session {session_id[:8]}")
        st.subheader("TODOs")
        boxes = {"todos": st.empty()}
        st.subheader("Files")
        boxes["files"] = st.empty()
        st.subheader("Usage")
        boxes["usage"] = st.empty()

    show_progress(boxes, state)
    show_downloads(boxes["files"], session_files(state.get("messages", [])), session_id)
    render_history(state.get("messages", []))

    prompt = st.chat_input("Enter your sequential algorithm here and press enter...")
    if not prompt:
        return

    st.chat_message("user").code(prompt, language=None)
    seen = len(state.get("messages", [])) + 1  # the prompt is already drawn
    try:
        agent = agent_for(MODELS[model])
        with st.chat_message("assistant"):
            for state in agent.stream({"messages": [("user", prompt)]}, config, stream_mode="values"):
                for msg in state["messages"][seen:]:
                    render_message(msg)
                seen = len(state["messages"])
                show_progress(boxes, state)
    except Exception as e:
        st.error(f"The run stopped: {e}")
        return
    st.rerun()  # redraw from the saved state so the file downloads appear


if __name__ == "__main__":
    app()
