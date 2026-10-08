# CHANGES.md

Three lines per assignment: what it added, what it removed, what it constrained.
Removals are logged like additions.

## Assignment 1
- **Added:** a loop (`agent/loop.py`), a model (`ministral-14b-2512`, through Mistral's API) and three tools (`read_issue`, `search_repo`, `post_comment`), run four ways: a direct call, a workflow, an agent and a hybrid.
- **Removed:** nothing.
- **Constrained:** the loop, by three bounds enforced in code before every model call: 12 steps, 50,000 tokens and 300 seconds per run (`agent/bounds.yaml`).
