from langchain_core.messages import AIMessage, HumanMessage

from app.main import session_files, token_totals


def call(name, filename):
    return {"name": name, "args": {"filename": filename}, "id": filename + name}


def test_session_files_keeps_first_order_and_drops_removed():
    messages = [
        HumanMessage("parallelize this"),
        AIMessage("", tool_calls=[call("write_file", "algo.py"), call("write_file", "src/test.py")]),
        AIMessage("", tool_calls=[call("write_file", "algo.py"), call("rm", "test.py")]),
        AIMessage("", tool_calls=[call("write_file", "notes.md")]),
    ]
    assert session_files(messages) == ["algo.py", "notes.md"]


def test_token_totals_sums_all_replies():
    usage = {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14}
    messages = [AIMessage("a", usage_metadata=usage), HumanMessage("b"), AIMessage("c", usage_metadata=usage)]
    assert token_totals(messages) == {"input_tokens": 20, "output_tokens": 8, "total_tokens": 28}
