# Assignment 1 report · Four ways to triage an issue

Every number here also goes in `reports/LAB_01.json`, which the checker reads
(format: `checks/FORMATS.md`, section 7). Give each number its run count. Mark
any vendor figure you cite with its source type and date.

## Part 0 · The recorded trace
Model calls, tool calls, prompt tokens and the cached share, first and last
prompt size, cumulative over first. One sentence on what the growth means.

These come from `fixtures/week01_recorded_run.jsonl` (one recorded run) and were
computed by `eval/part0.py`. I counted model calls by distinct `message.id` and
took each call's prompt as input + cache reads + cache writes.

| Model calls | Tool calls | Prompt tokens | Cache reads | Cached share | First prompt | Last prompt | Cumulative / first |
|---|---|---|---|---|---|---|---|
| 21 | 23 | 399,123 | 388,338 | 0.973 | 13,445 | 24,188 | 29.69 |

The agent only made 21 calls but read 29.7 times its first prompt in total,
because every call sends the whole conversation again, so the cost grows roughly
with the square of the number of steps, and the run only stayed cheap because
97.3% of those tokens were cache reads.

## Part A · Your loop's bounds
Your three bounds and why. Your worst case: *F*, *A*, *N*, and the cumulative
prompt tokens at your turn limit.

My three bounds are in `agent/bounds.yaml`, and `agent/loop.py` checks all of
them in code before every model call.

| Bound | Value | Why |
|---|---|---|
| Steps (`max_steps`) | 12 | A triage takes about 6 calls (read, 2 to 4 searches, post, stop). 12 gives double that and still stops a run that searches in circles |
| Tokens (`max_tokens`) | 50,000 | About twice my estimate of the prompt tokens at the step limit (below), so it should only kick in if tool results get much bigger than expected. It's an eighth of the 400,000 harness ceiling |
| Wall clock (`wall_clock_s`) | 300 s | 12 calls at about 3 s each is under a minute. The extra time covers the free tier's rate-limit waits (the harness waits 5 to 80 s per retry) but still ends a run that gets stuck |

**Worst case, estimated before any run.** *F* is the first call's prompt: the
agent's system prompt, the three tool definitions and the first message. That
was about 2,800 characters, so roughly 700 tokens at 4 characters per token (this
was the first version of the prompt; it got a little longer during dev tuning).
*A* is what one step adds, a tool call plus its result. A `read_issue` result
was about 120 tokens and `search_repo` results were 120 to 260, so I used
*A* ≈ 220. With *N* = 12, that gives 12 × 700 + 220 × 12 × 11 / 2 =
**22,920 tokens** at the step limit, about $0.005 at $0.20 per million input
tokens. I set the token budget at about twice that.

**Worst case, measured on the 60 evaluation agent runs:** to be filled in after
Part B.

**Which bound binds.** `make bounds-smoke` runs my agent against `NeverStops` on
the two dev issues. Both runs ended on `turn_limit` after exactly 12 model calls,
at 16,740 cumulative prompt tokens. That's under the 50,000 token budget, so the
step limit binds first. The checker's own bounds tests pass too: 12 calls then
`turn_limit` (31,353 cumulative prompt tokens against its worst case of 31,398),
and `token_budget` and `wall_clock` when those are set to bind first.

## Part B · Results
The table for all three ways: passes out of 60, per issue out of 10, the spread
(lowest and highest sweep), issues solved in every run, tokens, p50 and p95
latency, cost, tool calls.

## Part C · The decision
1. Find the diamond, for each way.
2. Your multipliers, and two differences from the vendor's 4×.
3. *f*, the blended cost, and the comparison with all-agent and all-workflow;
   then the slide's version, with *c*, *m* and *f* against the direct call.
4. Path entropy.
5. The four gates, one line of evidence each, and your verdict: agent,
   workflow or hybrid. If hybrid, where the line sits.
6. Your predictions: each one in `reports/PREDICTIONS_01.md` that missed, what
   you believed, and which trace shows why it was wrong.
7. The seven-layer audit: how many layers are empty (`ARCHITECTURE.md`).

## Part D · The hybrid
Your hand-off rule, and the Part B traces that led you to it (written before you
measure). Its row beside the three ways (the same columns as Part B's table), how many of
its runs handed the issue to the agent, and its measured cost per run beside your
blended cost from Part C, item 3. Does it change your Part C verdict? Which of
the four would you ship, and why?

## Assistance
Which AI tool, what it wrote, what you checked.
