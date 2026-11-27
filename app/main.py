import io
import json
import threading
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
POLL_SECONDS = 1.5


@st.cache_resource
def checkpointer():
    # shortcut: sessions live in server memory and are lost on restart; use SqliteSaver to keep them.
    return MemorySaver()


@st.cache_resource
def agent_for(model_key):
    return get_agent(model_key, checkpointer())


@st.cache_resource
def runs():
    """Agent runs by session id. Each runs in a thread, so the page stays usable while the agent works."""
    return {}


def start_run(session_id, agent, prompt, config):
    run = {"error": None}

    def work():
        try:
            agent.invoke({"messages": [("user", prompt)]}, config)
        except Exception as e:
            run["error"] = str(e)

    run["thread"] = threading.Thread(target=work, daemon=True)
    runs()[session_id] = run
    run["thread"].start()


def is_running(session_id):
    run = runs().get(session_id)
    return run is not None and run["thread"].is_alive()


def saved_state(config):
    saved = checkpointer().get_tuple(config)
    return saved.checkpoint["channel_values"] if saved else {}


def language_of(filename):
    return LANGUAGES.get(Path(filename).suffix.lower())


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


@st.dialog("File", width="large")
def show_file(name):
    path = BASE_DIR / name
    if not path.is_file():
        st.warning(f"{name} no longer exists.")
        return
    st.markdown(f"**{name}**")
    st.code(path.read_text(errors="replace"), language=language_of(name), line_numbers=True)
    st.download_button("Download", path.read_bytes(), file_name=name, on_click="ignore")


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


@st.fragment(run_every=POLL_SECONDS)
def chat_live(session_id, config):
    turn = None
    for msg in saved_state(config).get("messages", []):
        if isinstance(msg, HumanMessage):
            st.chat_message("user").code(msg.text, language=None)
            turn = None
        else:
            turn = turn or st.chat_message("assistant")
            with turn:
                render_message(msg)

    running = is_running(session_id)
    run = runs().get(session_id)
    if running:
        st.caption("⏳ The agent is working...")
    elif run and run["error"]:
        st.error(f"The run stopped: {run['error']}")
    if st.session_state.get("was_running") and not running:
        st.session_state.was_running = False
        st.rerun()  # re-enable the chat input


@st.fragment(run_every=POLL_SECONDS)
def sidebar_live(session_id, config):
    state = saved_state(config)
    messages = state.get("messages", [])

    st.subheader("TODOs")
    todos = state.get("todos", [])
    st.markdown("  \n".join(f"{TODO_ICONS.get(t['status'], '⬜')} {t['content']}" for t in todos)
                or "_No TODOs yet_")

    st.subheader("Files")
    names = [n for n in session_files(messages) if (BASE_DIR / n).is_file()]
    for name in names:
        if st.button(f"📄 {name}", key=f"open-{name}"):
            st.session_state.viewing = name
            st.rerun()  # the dialog opens from a full run, so the polling does not close it
    if names:
        st.download_button("⬇ All files (.zip)", zip_of([BASE_DIR / n for n in names]),
                           file_name=f"session-{session_id[:8]}.zip", mime="application/zip",
                           type="primary", on_click="ignore")
    else:
        st.markdown("_No files yet_")

    st.subheader("Usage")
    u = token_totals(messages)
    st.markdown(f"**Input:** {u['input_tokens']:,}  \n**Output:** {u['output_tokens']:,}  \n"
                f"**Total:** {u['total_tokens']:,}")


def app():
    st.title("Sequential to Parallel Algo Converter")
    session_id = st.query_params.get("session") or uuid4().hex
    st.query_params["session"] = session_id
    config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}

    with st.sidebar:
        model = st.selectbox("Model", list(MODELS))
        if st.button("New session"):
            st.query_params["session"] = uuid4().hex
            st.rerun()
        st.caption(f"Session {session_id[:8]}")
        sidebar_live(session_id, config)

    chat_live(session_id, config)
    if name := st.session_state.pop("viewing", None):
        show_file(name)

    prompt = st.chat_input("Enter your sequential algorithm here and press enter...",
                           disabled=is_running(session_id))
    if prompt:
        try:
            agent = agent_for(MODELS[model])
        except Exception as e:
            st.error(f"Could not start {model}: {e}")
            return
        start_run(session_id, agent, prompt, config)
        st.session_state.was_running = True
        st.rerun()


if __name__ == "__main__":
    app()
