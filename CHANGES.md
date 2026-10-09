# CHANGES.md

Three lines per assignment: what it added, what it removed, what it constrained.
Removals are logged like additions.

## Assignment 1
- **Added:** a loop in `agent/loop.py`; a model, `ministral-14b-2512` on
  Mistral's API; and three tools, `read_issue`, `search_repo` and
  `post_comment`, used in four approaches: direct call, workflow, agent and
  hybrid.
- **Removed:** nothing.
- **Constrained:** the agent loop, with three bounds that code checks before
  every model call: 12 steps, 50,000 tokens and 300 seconds per run. All three
  are set in `agent/bounds.yaml`.
