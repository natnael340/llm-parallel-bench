import logging

from langchain_openai import ChatOpenAI
from app.state import State, ReviewModel, ManualTestSummary
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LLM_PARALLELIZER="""
ROLE
You are an expert in parallel computing and HPC. Your sole task is to transform a given sequential program into an efficient, correct parallel version.

PRIME DIRECTIVE
- Correctness first: the parallel program must produce identical outputs to the sequential version for all valid inputs.
- Preserve the public API/I-O (function names, parameters, return values, side effects, ordering). If adaptation is unavoidable, add a thin compatibility wrapper.

DETERMINISM & FLOATING POINT
- Results must be deterministic. For floating-point reductions, enforce a fixed reduction order or use compensated summation to avoid order-dependent drift.

LANGUAGE HANDLING
- **Go**: use goroutines/channels; prefer worker pools; bound concurrency; avoid unbounded goroutine growth.
- **C++**: use **OpenMP** pragmas for loops/sections/tasks; implement correct reductions; avoid false sharing.
- **Python**: use **multiprocessing** (e.g., ProcessPoolExecutor); include `if __name__ == "__main__":` guard; avoid threads for CPU-bound work.

RESOURCE GUARDRAILS
- Bound parallelism to available cores (avoid oversubscription).
- Provide a small-input sequential fast path when parallel execution wouldn’t help.
- Minimize copying; use chunking/tiling and reductions instead of coarse locks.

WHEN NOT TO PARALLELIZE
- If hard dependencies make safe parallelism impossible, keep the logic sequential and (if helpful) apply safe improvements (e.g., vectorization/pipelining), preserving the API. Briefly explain why.

PROCESS (keep concise)
1) Analyze hotspots and data dependencies.
2) Choose the strategy (data/task, divide-and-conquer, pipelining) suited to the detected language + model above.
3) Implement the complete, runnable, well-commented parallel code.
4) Explain how correctness and synchronization are guaranteed (no races/deadlocks; deterministic where required).

INPUT (from user)
- A single fenced code block with the **sequential program** in Go, C++, or Python. No other metadata will be provided.

OUTPUT FORMAT (use exactly these sections)
### 1. Analysis and Parallelization Strategy
- Bottlenecks, dependencies, chosen strategy, brief justification (≤150 words).

### 2. Parallel Algorithm Implementation
```<same-language>
<complete, runnable, commented parallel code that preserves the original API>
"""


LLM_REFLECTION = """
You are **Reflector**, a strict static reviewer of a candidate parallelization.

RETURN FORMAT
- Return **JSON only** that matches this schema: 
  { "verdict": "DONE" | "REVISE", "issues": string[], "required_changes": string[] }
- Do **NOT** include markdown, code fences, or full code. Keep items concise and actionable.

PASS/FAIL CRITERIA (each issue must cite its criterion #):
1) Correctness & API parity (names/params/returns/ordering preserved).
2) Determinism (fixed order or compensated FP reductions when needed).
3) Safety (no races/deadlocks; sufficient synchronization; no shared-state hazards).
4) Language compliance (auto-detect):
   - Go: goroutines/channels, bounded concurrency, proper WaitGroups, no leaks.
   - C++: OpenMP with correct clauses (reduction/private/shared), avoid false sharing.
   - Python: multiprocessing (e.g., ProcessPoolExecutor) under `if __name__ == "__main__":`; tasks picklable; no CPU-bound threads.
5) Resource guardrails: concurrency bounded to cores; avoid unnecessary copying; **small-input sequential fast path** preferred when parallelism likely hurts.
6) Completeness: self-contained; imports/includes present; build/run-ready.

DECISION RULES
- If any criterion fails → `verdict="REVISE"`. Populate `issues` and **minimal** `required_changes` (imperative bullets). Each item must reference a criterion number.
- If all pass → `verdict="DONE"`; leave `issues` and `required_changes` empty.

NOTES
- Do not propose new features beyond the criteria.
- Prefer diffs as short, textual “required_changes” (no code blocks).
"""

LLM_REVISER = """
You are a CODE REVISER. You receive:
1) Original sequential program,
2) Previous candidate (analysis + one fenced code block),
3) Reviewer feedback listing mistakes/required changes.

GOAL
Apply EVERY required change with the MINIMUM edits necessary. Do not re-architect. Preserve the candidate’s structure and formatting.
"""


def _first_human(state: State) -> HumanMessage | None:
    for m in state["messages"]:
        if isinstance(m, HumanMessage):
            return m
    return None

def _last_ai(state: State) -> AIMessage | None:
    for m in reversed(state["messages"]):
        if isinstance(m, AIMessage):
            return m
    return None

def generation_node(state: State):
    model = ChatOpenAI(temperature=0.2, model="gpt-4o")

    if state.get("k", 0)  == 0 or not state.get("review"):
        system = SystemMessage(content=LLM_PARALLELIZER)
        human = HumanMessage(content=state["original_src"])
        message = [system, human]
    else:
        reqs = "\n- ".join(state["review"].get("required_changes", [])) or "(none)"
        prev = state.get("last_candidate", "(no previous candidate)")
        #system= SystemMessage(content=LLM_REVISER)
        human = HumanMessage(content=(
            "You are revising the prior candidate to satisfy the reviewer.\n\n"
            "### Original Sequential Program\n"
            f"{state['original_src']}\n\n"
            "### Previous Candidate\n"
            f"{prev}\n\n"
            "### Reviewer Required Changes\n"
            f"{reqs}\n\n"
            "### Task\n"
            "Produce a corrected revision that addresses **every** required change while preserving the original API, determinism, and safety."
        ))
        message = [human]
    
    result = model.invoke(message)

    return {"messages": [result], "last_candidate": result.content}


def reflection_node(state: State):
    candidate = _last_ai(state)

    if not candidate:
        return {"messages": [HumanMessage(content="Please provide the sequential code to parallelize.")]}
    
    original = state["original_src"]
    content = f"""Review the candidate vs the original.

### Original Sequential Program
{original}

### Candidate Parallel Program
{candidate.content}

Return JSON only (verdict, issues, required_changes)."""
    system = SystemMessage(content=LLM_REFLECTION)

    model = ChatOpenAI(temperature=0.0, model="gpt-4o").with_structured_output(ReviewModel)
    result = model.invoke([system, HumanMessage(content=candidate.content)])

    summary_lines = [f"### Verdict: {result.verdict}"]
    if result.issues:
        summary_lines.append("### Issues:\n- " + "\n- ".join(result.issues))
    if result.required_changes:
        summary_lines.append("### Required Changes:\n- " + "\n- ".join(result.required_changes))

    summary_text = "\n\n".join(summary_lines)

    return {
        "messages": [HumanMessage(content=summary_text)],
        "review": result.model_dump(),
        "k": 1
    }


def triage_manual_output(raw: str) -> ManualTestSummary:
    system = SystemMessage(content=(
        "You are a strict test failure triager for PARALLEL implementations.\n"
        "INPUT: raw compiler/runtime/test output (from unittest/pytest/etc.).\n"
        "OUTPUT: JSON only with keys 'issues' and 'required_changes'. "
        "Make 'required_changes' imperative, specific, and minimal. "
        "Examples: '__main__ guard for multiprocessing', 'match -1 for not-found', "
        "'bound workers to core count', 'add small-input fast path', "
        "'use fixed-order reduction / compensated sum', 'avoid shared mutable state', etc.\n"
        "No code blocks."
    ))
    model = ChatOpenAI(temperature=0.0, model="gpt-4o").with_structured_output(ManualTestSummary)
    return model.invoke([system, HumanMessage(content=raw)])