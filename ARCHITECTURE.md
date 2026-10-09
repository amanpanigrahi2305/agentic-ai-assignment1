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
| Model | `ministral-14b-2512` on Mistral's API, with the same model and settings for every approach. In the direct call and the workflow, it reads the issue and the search results, then picks the search terms and the answer. In the agent, it chooses every tool call and writes the comment itself | `settings.yaml:24`; every call goes through `harness/backends.py:212` | present |
| Harness | My loop runs the agent. It calls the model, runs whatever tools the model asks for, returns all of that step's results in a single turn, and stops at the first bound it hits. For each run, the runner creates a new run ID, a metered client and a set of tools tied to that run, then calls the chosen approach. All system prompts are built by one function from the files in `prompts/` | `agent/loop.py:61`, `agent/loop.py:93`, `harness/runner.py:109`, `ways/__init__.py:14` | partial: nothing trims old history, so each step resends the entire conversation, and `agent/loop.py:93` only ever appends. This is the same growth I measured in Part 0 |
| Tools | Three tools in a registry tied to one run: `read_issue`; `search_repo`, a plain text search that skips `config/` and returns at most 20 results; and `post_comment`, the only tool that writes, which stamps each comment with the run ID | `tools/__init__.py:52`, `tools/search_repo.py:29`, `tools/post_comment.py:25` | present |
| Memory & State | Nothing carries over between runs. Each run starts from a single user message, and the model never sees comments left by earlier runs. Within a run, the message list is just the harness's conversation, and it starts empty every time | `agent/loop.py:58`, where each run starts empty | **EMPTY** |
| Control & Policy | Three bounds in the loop, on steps, tokens and wall-clock time, checked in code before every model call, backed by the harness's hard ceilings per run and per lab. In Part D, one routing rule in code decides when the workflow hands an issue to the agent | `agent/loop.py:61`, `agent/loop.py:63`, `agent/loop.py:66`, `harness/client.py:118`, `harness/runner.py:148`, `ways/hybrid.py:5` | partial: the bounds limit how much a run can spend, not what it can do. `post_comment` posts whatever the model writes; nothing checks the content and no person approves it. "Post exactly one comment" exists only as a sentence in my prompt |
| Observability | One trace line per model call and per tool call, recording cached and uncached tokens separately, plus cost, latency and why the run ended. My code writes these lines, not the model. The runner adds `run_start`, `run_end` and the run ledger | `agent/loop.py:71`, `agent/loop.py:91`, `harness/trace.py:38`, `harness/trace.py:65`, `harness/runner.py:155` | present |
| Evaluation | A grounded check that reads the tracker rather than trusting the agent's own account, ten runs per issue for each approach, and every reported number recomputed from the traces | `eval/check_triage.py:25`, `eval/summarize.py:74`, `checks/check_01.py:258` | partial: offline only, on six issues. Nothing measures quality after release |

**Empty layers:** 1 of 7, Memory & State, and three more, Harness,
Control & Policy, and Evaluation, are only partly built. Slide 46 says a first
build usually lacks four: memory and state, control and policy, observability,
and evaluation. As the slide predicts, I have no memory and state. I do have
observability, and partial evaluation, because the course harness ships with
a trace writer and Part B required me to write a grounded check and run ten
times per issue before reporting anything. Control and policy is only half
there. My bounds enforce a spending limit in code, but the control this system
needs most is missing. RepoMind reads text that anyone can write, has access
to private code, and posts where that same person can read the result, yet no
code checks a comment before it goes out.
