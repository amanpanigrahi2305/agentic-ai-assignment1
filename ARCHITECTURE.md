# ARCHITECTURE.md · RepoMind on the seven layers

Assignment 1, Part C item 7 (Week 1, slide 43). For each layer: what does this job,
and where is it enforced. Cite code as a file path and line number joined by a
colon, inside backticks; the checker opens every reference. A layer held only by a
sentence in a prompt (any file under `prompts/`) is **EMPTY**, and so is a layer
nothing does yet. Status is one of: present, partial (say what is missing), or
**EMPTY**. Keep this file current: later assignments fill it in.

What each layer is for (Week 1, slides 40 to 42):

- **Model**: reasoning, choosing tools, generating text.
- **Harness**: runs the loop, builds each prompt, trims old history.
- **Tools**: where the system acts on the world.
- **Memory & State**: what survives a step, a session, a restart.
- **Control & Policy**: what the system may do, and when it must ask.
- **Observability**: a step-by-step record of what it did.
- **Evaluation**: measuring quality, before and after release.

| Layer | What does this job | Where it is enforced | Status |
|---|---|---|---|
| Model | `ministral-14b-2512` through Mistral's API, the same model and settings for every way. It reads the issue and the search results, picks search terms and the answer (direct call, workflow), or picks every tool call and writes the comment itself (agent) | `settings.yaml:24`; every call goes out at `harness/backends.py:212` | present |
| Harness | The bounded loop runs the agent: it calls the model, runs the tools it asks for, sends all of a step's results back in one turn, and stops on the first bound it reaches. The runner builds each run (a fresh run ID, a metered client, tools bound to that run) and calls the way. Every system prompt is assembled in one place, from `prompts/` | `agent/loop.py:61`, `agent/loop.py:94`, `harness/runner.py:109`, `ways/__init__.py:14` | partial: nothing trims old history. Every step resends the whole conversation (`agent/loop.py:94` appends; nothing removes), which is the growth Part 0 measured |
| Tools | Three tools in a registry bound to one run: `read_issue`, `search_repo` (literal text search; `config/` excluded; at most 20 results) and `post_comment`, the only write, stamped with the run's ID | `tools/__init__.py:52`, `tools/search_repo.py:29`, `tools/post_comment.py:25` | present |
| Memory & State | Nothing survives a run. Each run starts from a single user message, and the model never sees an earlier run's comments. The message list inside one run is the harness's conversation, not memory: it is rebuilt from nothing every run | `agent/loop.py:58` (every run starts here, empty) | **EMPTY** |
| Control & Policy | The loop's three bounds, checked in code before every model call: steps, tokens and wall clock. Behind them, the harness's hard ceilings, per run and per lab | `agent/loop.py:61`, `agent/loop.py:64`, `agent/loop.py:67`, `harness/client.py:118`, `harness/runner.py:148` | partial: the bounds limit how much a run may spend, not what it may do. `post_comment` publishes whatever the model writes, with no check of its content and no point where a person approves it; "post exactly one comment" is only a sentence in a prompt |
| Observability | One trace line per model call and per tool call, with tokens (cached and uncached apart), cost, latency and the reason the run ended, written by code, never by the model; `run_start`, `run_end` and the run ledger around them | `agent/loop.py:72`, `agent/loop.py:92`, `harness/trace.py:38`, `harness/trace.py:65`, `harness/runner.py:155` | present |
| Evaluation | A grounded check that reads the tracker, never the agent's words; ten runs per issue per way; every reported number recomputed from the traces | `eval/check_triage.py:25`, `eval/summarize.py:82`, `checks/check_01.py:258` | partial: offline only, on six issues; nothing measures quality after release |

**Empty layers:** 1 of 7 (Memory & State), with three more partial (Harness,
Control & Policy, Evaluation). Slide 46 expects four to be missing from a first
build: memory and state, control and policy, observability, and evaluation.
Memory and state is missing here, as the slide predicts. Observability and
evaluation are not, because the course harness ships the trace writer and
Part B made me write a grounded check and ten runs per issue before I could
report a number. Control and policy is only half there: Part A's bounds put a
spending limit in code, but the control this system needs most is missing.
RepoMind reads text anyone can write and posts where its author can read it,
and nothing in code looks at a comment before it goes out.
