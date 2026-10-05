# Base Agent Prompt Template

## Purpose
Prompt and configuration for the LangGraph BaseAgent that defines shared state, tool registry, and common patterns.

## ReviewState Definition
The single source of truth for all agent state:

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

## Tool Registry Pattern
All tools must be:
- Pure functions with Pydantic I/O
- Registered in `base.ToolRegistry`
- Validated for inputs/outputs
- Documented with clear purpose

## LLM Configuration
- Provider: `llm_provider` from Settings
- Model: `llm_model` from Settings
- Temperature: `llm_temperature` from Settings (default: 0.1)
- Use `PydanticOutputParser` + `RunnableWithFallbacks` in every tool

## Checkpointing
- Prod: `PostgresSaver` with `checkpoint_db_url`
- Dev: `MemorySaver` 
- See `graph/checkpointer.py` for implementation details

## Recursion Limit
Always set `recursion_limit=25` in `graph/builder.py` to prevent infinite loops.
Log `current_agent` at each graph step for debugging.