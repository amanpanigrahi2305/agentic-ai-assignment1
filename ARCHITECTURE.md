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
| Model | `ministral-14b-2512` on Mistral's API, with the same model and settings for every way. It reads the issue and the search results and picks the search terms and the answer (direct call, workflow), or picks every tool call and writes the comment itself (agent) | `settings.yaml:24`; every call goes through `harness/backends.py:212` | present |
| Harness | My loop runs the agent: it calls the model, runs the tools the model asks for, sends all of that step's results back in one turn, and stops at the first bound it hits. The runner sets up each run (new run ID, metered client, tools tied to that run) and then calls the way. All the system prompts get built in one function from the files in `prompts/` | `agent/loop.py:61`, `agent/loop.py:94`, `harness/runner.py:109`, `ways/__init__.py:14` | partial: nothing trims old history, so every step resends the whole conversation (`agent/loop.py:94` only ever appends). That's the same growth I measured in Part 0 |
| Tools | Three tools in a registry tied to one run: `read_issue`, `search_repo` (plain text search that skips `config/` and returns at most 20 results) and `post_comment`, which is the only write and gets stamped with the run ID | `tools/__init__.py:52`, `tools/search_repo.py:29`, `tools/post_comment.py:25` | present |
| Memory & State | Nothing carries over from one run to the next. Every run starts from a single user message, and the model never sees comments from earlier runs. The message list inside a run is just the harness's conversation, and it starts empty every time | `agent/loop.py:58` (where every run starts, empty) | **EMPTY** |
| Control & Policy | The loop's three bounds (steps, tokens and wall clock), checked in code before every model call, plus the harness's hard ceilings per run and per lab behind them | `agent/loop.py:61`, `agent/loop.py:64`, `agent/loop.py:67`, `harness/client.py:118`, `harness/runner.py:148` | partial: the bounds limit how much a run can spend, not what it can do. `post_comment` posts whatever the model writes, nothing checks the content and no person approves it, and "post exactly one comment" is only a sentence in my prompt |
| Observability | One trace line for every model call and every tool call, with tokens (cached and uncached separately), cost, latency and the reason the run ended. My code writes these lines, not the model, and the runner adds `run_start`, `run_end` and the run ledger | `agent/loop.py:72`, `agent/loop.py:92`, `harness/trace.py:38`, `harness/trace.py:65`, `harness/runner.py:155` | present |
| Evaluation | A grounded check that reads the tracker instead of trusting what the agent says, ten runs per issue for each way, and every reported number recomputed from the traces | `eval/check_triage.py:25`, `eval/summarize.py:82`, `checks/check_01.py:258` | partial: only offline, on six issues. Nothing measures quality after release |

**Empty layers:** 1 of 7 (Memory & State), and three more are only partial
(Harness, Control & Policy, Evaluation). Slide 46 says a first build is usually
missing four: memory and state, control and policy, observability, and
evaluation. Mine is missing memory and state, like the slide says. Observability
and evaluation are there because the course harness comes with the trace writer,
and Part B made me write a grounded check and do ten runs per issue before
reporting anything. Control and policy is only half there. My bounds put a
spending limit in code, but the control this system needs most is missing:
RepoMind reads text that anyone can write and posts where that person can read
it, and nothing in code looks at a comment before it gets posted.
