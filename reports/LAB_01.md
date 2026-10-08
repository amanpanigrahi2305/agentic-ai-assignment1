# Assignment 1 report · Four ways to triage an issue

Every number here also goes in `reports/LAB_01.json`, which the checker reads
(format: `checks/FORMATS.md`, section 7). Give each number its run count. Mark
any vendor figure you cite with its source type and date.

## Part 0 · The recorded trace
Model calls, tool calls, prompt tokens and the cached share, first and last
prompt size, cumulative over first. One sentence on what the growth means.

From `fixtures/week01_recorded_run.jsonl` (one recorded run), by `eval/part0.py`,
counting calls by distinct `message.id` and a call's prompt as input plus cache
reads plus cache writes:

| Model calls | Tool calls | Prompt tokens | Cache reads | Cached share | First prompt | Last prompt | Cumulative / first |
|---|---|---|---|---|---|---|---|
| 21 | 23 | 399,123 | 388,338 | 0.973 | 13,445 | 24,188 | 29.69 |

The run took 21 calls but read 29.7 times its first prompt, because every call
resends the whole conversation so far: an agent's cost grows with the square of
its steps, not with their number, and only the 97.3% served from cache kept this
one cheap.

## Part A · Your loop's bounds
Your three bounds and why. Your worst case: *F*, *A*, *N*, and the cumulative
prompt tokens at your turn limit.

The bounds live in `agent/bounds.yaml`, and `agent/loop.py` checks all three in
code before every model call:

| Bound | Value | Why |
|---|---|---|
| Steps (`max_steps`) | 12 | A triage takes about 6 calls (read, 2 to 4 searches, post, stop); 12 doubles that and caps a run that searches in circles |
| Tokens (`max_tokens`) | 50,000 | About twice the estimated prompt tokens at the step limit (below), so it binds only if tool results balloon; an eighth of the 400,000 harness ceiling |
| Wall clock (`wall_clock_s`) | 300 s | 12 calls at about 3 s is under a minute; the rest absorbs the free tier's rate-limit back-off (the harness waits 5 to 80 s per retry) and still ends a stuck run |

**Worst case, estimated before any run.** *F*, the first call's prompt, is the
agent's system prompt plus the three tool definitions plus the first message:
about 2,800 characters at four characters a token, so *F* ≈ 700 (the prompt as
first written; dev tuning later lengthened it a little). *A*, what a step adds,
is one tool call plus its result: a `read_issue` result came to about 120 tokens
and `search_repo` results to 120 to 260, so *A* ≈ 220. With *N* = 12, the
cumulative prompt at the step limit is 12 × 700 + 220 × 12 × 11 / 2 =
**22,920 tokens**, about $0.005 at $0.20 per million input tokens. That set the
token budget at roughly twice this number.

**Worst case, measured on the 60 evaluation agent runs:** filled in after Part B.

**Which bound binds.** `make bounds-smoke` runs the agent against `NeverStops`
on the two dev issues: both runs end on `turn_limit` after exactly 12 model
calls, at 16,740 cumulative prompt tokens, below the 50,000-token budget, so the
step limit binds first. The checker's own tests pass too: exactly 12 calls then
`turn_limit` (31,353 cumulative prompt tokens against its worst case of 31,398),
`token_budget` and `wall_clock` when those bind first.

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
