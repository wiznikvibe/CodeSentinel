# Test Generator Prompt Template

## Purpose
Prompt for the LangGraph test generator agent that suggests test cases based on PR diffs and existing findings.

## Core Directives
1. **Analyze the diff** provided in the state to identify new logic and functions
2. **Identify edge cases** and error conditions for the changed code
3. **Address security vulnerabilities** from existing findings
4. **Prioritize** test coverage for high-risk areas and recently modified code
5. **Suggest** tests that follow best practices for readability and maintainability

## Input Variables
- `pr_number`: int — Pull request number
- `repo_url`: str — Repository URL
- `diff`: str — The full diff to analyze
- `files`: list[str] — List of changed files
- `existing_findings`: accumulated findings from code_reviewer and security_auditor

## Output Expectations
- `test_suggestions`: List[dict] — Accumulated test suggestions annotated in state
- Each suggestion has: title, description, file, line, test_type
- Current agent tracking: `current_agent: str`
- Metadata: `metadata: dict`

## Test Type Categories
- `unit`: Individual function/method tests
- `integration`: Integration between components
- `security`: Security-focused test cases
- `edge_case`: Boundary conditions and error handling
- `regression`: Tests to prevent previously fixed bugs

## Versioning
Version this prompt template when updating review logic or criteria.
Store version in prompt metadata or as a comment at the top of the file.