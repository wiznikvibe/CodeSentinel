# Master Architecture Plan — Orchestration Layer

## Overview
Build the orchestration layer around existing worker nodes (`code_reviewer`, `security_auditor`, `test_generator`) using a `supervisor` node and a `graph/builder.py` compilation function.

The architecture must follow the repository's established patterns from `AGENTS.md` and the existing agent implementations.

---

## 1. ReviewState (Source of Truth)

```python
class ReviewState(TypedDict):
    pr_number: int
    repo_url: str
    diff: str
    files: list[str]
    findings: Annotated[list[Finding], add_messages]  # accumulated
    current_agent: str
    metadata: dict
```

- All workers read/write this state.
- `findings` accumulates via `add_messages`-style annotation.
- Node functions return **partial state dictionaries** (e.g., `{"findings": new_findings}`), relying on the LangGraph reducer.
- No field should be casually modified; existing fields must be preserved.

---

## 2. Supervisor

### Purpose
Decide which worker should execute next based on `ReviewState`. The supervisor is the "router" of the graph.

### LLM Abstraction
- Use the repository's existing `get_llm()` pattern (injected at runtime, same as `code_reviewer.py`, `security_auditor.py`, `test_generator.py`).
- LLM config comes from `core/config.py` Settings: `llm_provider`, `llm_model`, `llm_temperature`.
- The supervisor does **not** create its own LLM client; it reuses the injected `get_llm()`.

### Routing Representation
- Use the installed LangGraph `Command` class from `langgraph.types`:
  ```python
  Command(goto="node_name")  # route to a worker
  Command(goto=END)          # terminate
  ```
- `goto` accepts a **string** (node name) or `END` constant.
- **Do not** accept arbitrary graph node names from the LLM — only pre-approved destinations.
- Define an explicit routing schema (literals/enum) constrained to: `code_reviewer`, `security_auditor`, `test_generator`, `END`.

### Allowed Routing Destinations
1. `code_reviewer` — run code review
2. `security_auditor` — run security audit
3. `test_generator` — generate test suggestions
4. `END` — graph termination (no more work needed)

### State Evaluation Logic
The supervisor evaluates `ReviewState` to determine the next step:

| Condition | Action |
|---|---|
| No workers have run yet | Route to `code_reviewer` (first step) |
| `code_reviewer` has run but `security_auditor` has not | Route to `security_auditor` |
| `security_auditor` has run but `test_generator` has not | Route to `test_generator` |
| All three have run | Terminate (`END`) |
| Repeated dispatch of same worker | Terminate (prevent infinite loops) |
| Insufficient state to determine | Default to `code_reviewer` or terminate |

### Preventing Repeated Execution
- Track which workers have completed using `metadata` or the `current_agent` field.
- If the last `current_agent` matches the candidate worker, skip and terminate.
- Use `metadata` to record: `{"completed": ["code_reviewer", "security_auditor"]}`.
- Never route to a worker that has already completed in the current cycle.

### Handling Invalid/Unexpected LLM Output
- If the LLM returns a name outside the approved set (`code_reviewer`, `security_auditor`, `test_generator`, `END`), default to `END` (terminate).
- If the LLM response is empty or malformed, default to `END`.
- Use `Command(goto=END)` as the safe fallback.
- Log a warning when falling back to termination.

### Supervisor Return Value
- Must return a `Command` from `langgraph.types`:
  ```python
  from langgraph.types import Command
  
  # Route to next worker
  return Command(goto="security_auditor")
  
  # Terminate
  return Command(goto=END)
  ```
- May also include `update` to modify state if needed, but the minimal pattern returns just `Command(goto=...)`.

### Prompt Template
- Create `core/prompts/supervisor.md` (already exists, review its content).
- The prompt should guide the LLM to output one of the four approved routing destinations.
- Use structured output constraints if supported, or few-shot examples.

---

## 3. Graph Builder

### Purpose
Compile the LangGraph with the supervisor and worker nodes, entry point, conditional edges, and checkpointer.

### Graph Structure
- **Nodes**: `supervisor`, `code_reviewer`, `security_auditor`, `test_generator`
- **Entry point**: `START` → supervisor
- **Routing**: supervisor → worker (conditional edges based on state)
- **Termination**: when supervisor returns `Command(goto=END)`
- **Checkpointer**: `MemorySaver()` for dev; `PostgresSaver` for prod

### Entry Point
- `START` edges to supervisor node.

### Supervisor Integration
- The supervisor node is called at `START`.
- After the supervisor returns a `Command(goto=...)`, the graph routes to the named node.
- After the worker node completes, the graph routes back to the supervisor for the next decision.

### Conditional Transitions
- After each worker node completes, the graph routes back to the supervisor.
- The supervisor re-evaluates the state and decides the next step.
- This creates a loop: supervisor → worker → supervisor → worker → ... → END.

### Termination Path
- When the supervisor returns `Command(goto=END)`, the graph stops.
- The final state is returned to the caller.

### Checkpointer
- **Dev**: `MemorySaver()` — in-memory, lost between invocations.
- **Prod**: `PostgresSaver` with `checkpoint_db_url` from Settings.
- The `build_graph()` function should accept an optional `checkpointer` parameter:
  ```python
  def build_graph(checkpointer=None):
      if checkpointer is None:
          checkpointer = MemorySaver()
      ...
  ```
- Tests can pass `MemorySaver()` to verify persistence across invocations.
- The implementation should **expose a factory/helper** rather than a global singleton, so tests can inject a fresh saver.

### Recursion-Limit Strategy
- Set `recursion_limit=25` in the graph builder (as noted in AGENTS.md pitfalls).
- Log `current_agent` at each step for debugging (as per AGENTS.md).

### Graph Builder Function Signature
```python
def build_graph(checkpointer=None):
    """
    Build and return a compiled LangGraph.
    
    Args:
        checkpointer: Optional checkpoint saver. Defaults to MemorySaver().
    
    Returns:
        Compiled Langraph graph ready for execution.
    """
```

---

## 4. Integration Summary

| Component | File | Responsibility |
|---|---|---|
| **Supervisor Node** | `agents/supervisor.py` | Evaluates ReviewState, returns Command(goto=...) |
| **Prompt Template** | `core/prompts/supervisor.md` | Guides LLM routing decision |
| **Graph Builder** | `graph/builder.py` | Compiles StateGraph with nodes/edges/checkpointer |
| **Worker Nodes** | `agents/code_reviewer.py`, `agents/security_auditor.py`, `agents/test_generator.py` | Read state, call LLM, append findings/suggestions |
| **Configuration** | `core/config.py` | LLM provider/model/temperature, checkpoint_db_url |
| **Checkpointer** | `langgraph.checkpoint.memory.MemorySaver` | Dev persistence |

### Data Flow
```
START → supervisor → (LLM routing decision) → worker node → 
findings/suggestions appended to ReviewState → back to supervisor → 
... loop ... → supervisor → END (termination)
```

### State Mutation Semantics
- Worker nodes return `{"findings": new_findings}` or `{"test_suggestions": new_suggestions}`.
- LangGraph reducer appends to existing list via `add_messages`-style annotation.
- Supervisor does **not** modify `findings`; it only routes.
- All state preservation relies on the LangGraph reducer, not manual copying.

### Error Handling
- If LLM fails (exception), supervisor should default to `Command(goto=END)`.
- If state is missing required fields, supervisor should handle gracefully (default to END or log error).
- No infinite loops possible due to: (a) explicit routing schema, (b) completion tracking via metadata, (c) recursion_limit=25.

---