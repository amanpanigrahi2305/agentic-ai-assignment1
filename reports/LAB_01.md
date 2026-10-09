# Assignment 1 report · Four ways to triage an issue

Every number here also goes in `reports/LAB_01.json`, which the checker reads
(format: `checks/FORMATS.md`, section 7). Give each number its run count. Mark
any vendor figure you cite with its source type and date.

## Part 0 · The recorded trace
Model calls, tool calls, prompt tokens and the cached share, first and last
prompt size, cumulative over first. One sentence on what the growth means.

These come from one recorded run, `fixtures/week01_recorded_run.jsonl`, and were
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
| Steps, `max_steps` | 12 | A triage takes about 6 calls: one read, 2 to 4 searches, a post and a stop. 12 gives double that and still stops a run that searches in circles |
| Tokens, `max_tokens` | 50,000 | About twice my estimate of the prompt tokens at the step limit, which I work out below, so it should only kick in if tool results get much bigger than expected. It's an eighth of the 400,000 harness ceiling |
| Wall clock, `wall_clock_s` | 300 s | 12 calls at about 3 s each is under a minute. The extra time covers the free tier's rate-limit waits, where the harness waits 5 to 80 s per retry, but it still ends a run that gets stuck |

**Worst case, estimated before any run.** *F* is the first call's prompt: the
agent's system prompt, the three tool definitions and the first message. That
was about 2,800 characters, so roughly 700 tokens at 4 characters per token.
That was the first version of the prompt, and it got a little longer during dev
tuning. *A* is what one step adds, a tool call plus its result. A `read_issue`
result was about 120 tokens and `search_repo` results were 120 to 260, so I used
*A* ≈ 220. With *N* = 12, that gives 12 × 700 + 220 × 12 × 11 / 2 =
22,920 tokens at the step limit, about $0.005 at $0.20 per million input
tokens. I set the token budget at about twice that.

**Worst case, measured on the 60 evaluation agent runs.** *F* is the mean
first-call prompt, 758.0 tokens, and *A* is the mean increase in prompt tokens
from one call to the next, 153.9. With *N* = 12 that gives
12 × 758.0 + 153.9 × 12 × 11 / 2 = 19,253 tokens, which is the value in
`reports/LAB_01.json`. My estimate of 22,920 was a bit high. *F* came out higher
than I guessed because dev tuning made the prompt longer, but *A* came out lower,
because about a fifth of the agent's 408 searches returned `No matches.` and the
average result was only 445 characters. The biggest real run read 20,546 prompt
tokens. That's a little over the formula, since *A* is an average and the runs
that hit the step limit had longer results than average, but it's still far
below the 50,000 token budget, which never fired.

**Which bound binds.** `make bounds-smoke` runs my agent against `NeverStops` on
the two dev issues. Both runs ended on `turn_limit` after exactly 12 model calls,
at 16,740 cumulative prompt tokens. That's under the 50,000 token budget, so the
step limit binds first. The checker's own bounds tests pass too. It got 12 calls
then `turn_limit`, at 31,353 cumulative prompt tokens against its worst case of
31,398, and it got `token_budget` and `wall_clock` when those were set to bind
first.

## Part B · Results
The table for all three ways: passes out of 60, per issue out of 10, the spread
(lowest and highest sweep), issues solved in every run, tokens, p50 and p95
latency, cost, tool calls.

All numbers below come from 60 runs per approach: 10 sweeps over the six
evaluation issues. Every run used `ministral-14b-2512` with identical settings.
`eval/summarize.py` builds the tables from `runs/` and `tracker/comments.jsonl`.
For cost, I used the rates in `pricing.yaml`, which I copied from Mistral's API
pricing page on 2026-10-07: $0.20 per million input tokens, $0.02 per million
cached input tokens, and $0.20 per million output tokens.

| Approach | Passes (of 60) | 4201 | 4202 | 4203 | 4204 | 4205 | 4206 | Per-sweep range (of 6) | Issues solved 10/10 |
|---|---|---|---|---|---|---|---|---|---|
| Direct call | 40 | 10 | 10 | 10 | 0 | 10 | 0 | 4–4 | 4 |
| Workflow | 32 | 10 | 0 | 9 | 0 | 8 | 5 | 2–4 | 1 |
| Agent | 31 | 10 | 3 | 9 | 0 | 9 | 0 | 2–4 | 1 |

| Approach | Prompt tokens per run (uncached + cached) | Output tokens per run | Latency p50 / p95 | Cost per run | Tool calls per run, mean (max) |
|---|---|---|---|---|---|
| Direct call | 1,114.0 (845.2 + 268.8) | 12.2 | 0.6 s / 1.2 s | $0.000177 | 2.0 (2) |
| Workflow | 1,625.2 (1,279.6 + 345.6) | 21.8 | 1.2 s / 9.9 s | $0.000267 | 6.0 (6) |
| Agent | 11,720.6 (6,028.9 + 5,691.7) | 154.2 | 7.2 s / 51.2 s | $0.001350 | 9.1 (21) |

What I noticed:

- The direct call didn't change its answer once. On every issue it gave the
  same result in all 10 sweeps, so it scored exactly 4 of 6 each time. The
  workflow and the agent both moved around, landing anywhere from 2 to 4 per
  sweep.
- Mistral caches repeated prompts automatically, and the agent got the most
  out of that. Roughly half its prompt tokens, 5,692 of 11,721 per run, came
  from cache. For the direct call it was about a quarter, and for the
  workflow about a fifth.
- Most of the agent's 51 s p95 is time spent waiting on the rate limit, not
  model time. 45 of its 60 runs finished in under 15 s. The other 15 took
  more than 30 s because they hit Mistral's free-tier cap of 0.5 requests per
  second, which made the harness back off and retry. That limit comes from
  the limits page in my Mistral account, checked 2026-10-07. The slowest run
  took 91.6 s, and a single call accounted for 84 s of it.
- 47 agent runs ended with `model_stopped` and 13 with `turn_limit`: all 10
  runs on 4206, 2 on 4202 and 1 on 4203. No run ended on `token_budget` or
  `wall_clock`. A run that hit the turn limit never posted a comment, so it
  counted as a fail.

## Part C · The decision
1. Find the diamond, for each way.

None of my three approaches has a person approving any step. `post_comment`
publishes the moment it's called, so none of them counts as a chatbot or a
copilot. What separates them is who chooses the next step and who decides
when the run is over.

| Approach | Who chooses the next step | Who ends the run | What that makes it |
|---|---|---|---|
| Direct call | My code. It reads the issue, makes one model call, and posts. There's no decision point anywhere | My code, right after posting | A script |
| Workflow | My code, always in the same order: read, a terms call, up to 4 searches with one per term, a choose call, then post. The model only supplies the content: the terms, the label and the file | My code, after posting | A workflow |
| Agent | The model, at every step. It decides which tool to call, what to pass it, whether to post, and when to stop | Normally the model, which ends with `model_stopped`. But my code can cut it off first through `turn_limit`, `token_budget` or `wall_clock` | An agent with outside limits, what the slide calls "bounded outside". It's like the slide's trading bot: the model chooses the steps, but code can still stop the run |

If you look at individual parts, the lines blur a bit. Even in the agent, the
limits and the trace are plain code. And in the workflow, the model does make
one choice that affects what happens next: its search terms decide which
searches run, though not the order of the steps. Still, only in the agent does
the decision point itself belong to the model.

2. Your multipliers, and two differences from the vendor's 4×.

Per run, the agent used (11,720.6 + 154.2) / (1,114.0 + 12.2) = 10.5 times as
many tokens as the direct call, averaged over 60 runs each. The lecture puts
this at about 4×, on slide 30, which compares agents with chat interactions, a
figure Anthropic reported in 2025 for one team and its own workload. My ratio is
more than twice that. I think there are two reasons the numbers don't measure
the same thing:

- **Different baselines.** Their 4× compares agents to chat across everything
  a team works on. My baseline is a single narrow task handled in one short
  call of about 1,126 tokens, repo summary included. That makes my denominator
  very small, while the agent's long runs on the hard issues make the
  numerator very large.
- **Different models and different counting.** Theirs is a number the vendor
  reported for its own frontier models, with no run counts given. Mine is
  measured on one 14B model over 60 runs per approach. I count prompt plus
  output tokens per run, including the roughly half that Mistral served from
  cache. On top of that, 13 of my agent runs kept searching until they hit the
  turn limit.

For cost, *m* = agent cost / workflow cost = $0.001350 / $0.000267 = 5.05.

3. *f*, the blended cost, and the comparison with all-agent and all-workflow;
   then the slide's version, with *c*, *m* and *f* against the direct call.

**f = 0.** The workflow got fewer than 5 of 10 on two issues, scoring 0 of 10 on
both 4202 and 4204. The agent didn't reach 5 of 10 on either of those, scoring
3 and 0. That means the blended cost c × [(1 − f) + f × m] comes out to just the
workflow's own cost:

| | Formula | Cost per run |
|---|---|---|
| Workflow alone | c | $0.000267 |
| Blended (f = 0) | c × [(1 − 0) + 0 × 5.05] | $0.000267 |
| Everything through the agent | c × m | $0.001350 |

With *f* at 0, I looked instead at what each extra correct triage costs. Across
all issues there aren't any, because the agent passed slightly less often than
the workflow, 31 vs 32 of 60. It costs $0.00108 more per run and gets 0.017
fewer passes per run. Issue by issue, the picture is mixed. On 4202 the agent
beat the workflow 3 of 10 to 0 of 10, at $0.00170 more per run, or about $0.0057
per extra correct triage. On 4205 it won 9 of 10 to 8 of 10, at about $0.0047 per
extra correct triage. But on 4206 it dropped from the workflow's 5 of 10 to 0.
For Part D, I use 4202 and 4205, the two issues where the agent passed more
often.

**The slide's version, using the direct call as the baseline:** c = $0.000177,
m = 7.64 and f = 0. The direct call fails 4204 and 4206, and the agent gets 0 of
10 on both, so it rescues neither. The blended cost is $0.000177 and sending
everything through the agent costs $0.001350.

The two versions use different values of *c* and *m*, but they reach the same
answer. Gate 4 should compare against whatever I'd actually ship if the agent
lost. The assignment assumes that's the workflow. On my numbers, though, the
direct call beat the workflow, 40 vs 32 of 60, at about two-thirds of the cost,
so my real fallback is the direct call. Against it, the agent costs about 7.6
times as much and solves fewer issues. And since *f* = 0 against either
baseline, paying the multiplier buys me nothing in both cases.

4. Path entropy.

The agent's 60 runs produced 20 different sequences of tool calls. The three
most common account for 29 runs, or 0.483 of the total. The most frequent, seen
in 12 runs, was one read, 6 searches and a post. Second was a read, 1 search and
a post, in 10 runs, and third was a read, 7 searches and a post, in 7 runs.

Most of that variety is mistakes, not choices. In 13 runs the agent sent calls
to tools that don't exist, 32 in all, putting a piece of JSON such as
`{"max_results": 1}` where the tool name should go, and every one came back as
an error. Those 13 runs make up 13 of the 20 distinct sequences. If I ignore the
broken calls, there are only 8 sequences, and every one follows the same
pattern: read the issue once, search *k* times, then post once. Runs that hit
the turn limit never post. That happened 13 times, for example a read followed
by 11 searches, and 7 of those 13 also had broken calls.

So the agent never used its freedom to call the real tools in a different order.
Each run followed the same order my workflow fixes in code. Apart from the
broken calls, the only things that varied were *k* and the search terms. The
part that isn't paying for itself is the loop's stopping decision: knowing when
it has searched enough. That's where the extra calls pile up on the hard issues,
with about 10 to 12 model calls per run on 4202, 4203, 4204 and 4206, compared
with 4 on 4201. It's also where the agent failed outright, in the 13 runs that
never posted.

5. The four gates, one line of evidence each, and your verdict: agent,
   workflow or hybrid. If hybrid, where the line sits.

1. **Does the task vary from case to case?** The answers do, but the steps
   don't. Every agent run used the real tools in the same order, read, then
   search, then post, as shown in item 4. And a single fixed call solved 4 of
   the 6 issues in every sweep.
2. **Can you limit the damage of a mistake?** Mostly. A run can only post a
   comment. My bounds cap it at 12 calls and 50,000 tokens, so the worst case
   costs about $0.01, and a wrong label is easy to fix. The catch is that the
   comment is public.
3. **Will you catch a mistake in time?** No. Nothing checks a comment before
   it goes out, and no person sees it first. I only found the agent's 29 failed
   runs, 16 wrong comments and 13 runs that posted nothing, after the fact, by
   checking the tracker against an answer key that production won't have. A
   wrong label alone would land in the slide's "automate it" corner, since it's
   visible and easy to change. But RepoMind posts a public comment written by a
   model that reads untrusted issue text and private code. That's the lethal
   trifecta, and once someone has read a comment that leaks code, deleting it
   doesn't help.
4. **Is it worth the multiplier?** No. *m* is 5.05 against the workflow and
   7.6 against the direct call, *f* = 0, and the agent passed fewer runs than
   either. It's also the slowest, with a 51 s p95 compared with 1.2 s for the
   direct call. That's far beyond the roughly 10 s the lecture gives as the
   point where you need a workflow or a progress display.

**Verdict: workflow.** The control flow should stay in my code. Of my three
approaches, I'd ship the direct call: 40 of 60 at $0.000177 a run, with a 1.2 s
p95, because the repo summary already points to the right file for four of the
six issues. If I added an agent at all, it would come after the workflow's
choose step. Reading, searching and choosing would stay fixed in code, and only
runs whose answer names no file would go to the agent. Part D tests that.

6. Your predictions: each one in `reports/PREDICTIONS_01.md` that missed, what
   you believed, and which trace shows why it was wrong.

- **Direct call: predicted 25/60, got 40/60.** My reasoning was that without
  search it could only name a file if the summary happened to list it, and I
  assumed the summary was too general for that. I was wrong. The summary's
  layout table names the exact file for four of the six issues, and the direct
  call copied those rows every time. For example, `direct-4202-s01-0cd320`
  posted `feature` and `src/exportUtils.ts`, taken straight from the row "Export
  formats, column order and delimited output". I did call 4206 correctly: it
  scored 0/10 for the reason I gave, and `direct-4206-s01-5ff1fa` posted
  `src/export/csv.ts`. What I didn't predict was 4204, which also scored 0/10.
  It posted `src/notifications/rollup.ts` instead of `src/util/dates.ts`.
- **Workflow: predicted 30/60, got 32/60.** The total was close, but I misjudged
  which issues would be hard. 4204 scored 0/10 as expected, and
  `workflow-4204-s01-2c7e61` actually had `src/util/dates.ts` in its search
  results, then picked `rollup.ts` anyway. 4202 surprised me at 0/10, since I'd
  thought naming the format would be enough. `workflow-4202-s02-977497` shows
  what went wrong: its terms, `feature`, `TSV`, `export` and `format`, filled the
  10-result cap with README and docs lines, so `src/exportUtils.ts` never showed
  up, and it answered with the folder `src/export/`. On 4206 it did better than
  I expected, at 5/10. In the five runs where it searched for `dedupe`, such as
  `workflow-4206-s01-563c54`, it found `src/ingest/dedupe.ts`.
- **Agent: predicted 32/60, got 31/60.** I was right that 4206 would be its
  hardest issue, at 0/10, but wrong about why. I expected my
  stop-at-the-first-match rule to make it post `src/export/csv.ts`. Instead it
  never posted at all: all 10 runs hit the 12-call turn limit.
  `agent-4206-s01-454dfd` searched `csv.ts`, `transactions`, `merge`,
  `same date`, `amount`, `description`, `currency`, `src/export/csv.ts`, `csv`,
  `writer` and `key`, but never `dedupe`. It kept circling the file the reporter
  had named and ignored the prompt's instruction to decide after at most 6
  searches. I had also expected it to finish slightly ahead of the workflow at
  about six times the cost. It actually finished one pass behind, at 5.05 times
  the cost.

7. The seven-layer audit: how many layers are empty (`ARCHITECTURE.md`).

Of the 7 layers, one is missing entirely, Memory & State, and three are only
partly built: Harness, Control & Policy, and Evaluation. The full table, with
references to the code, is in `ARCHITECTURE.md`. Slide 46 says a first build
usually lacks four layers: memory and state, control and policy, observability
and evaluation. I have observability and some evaluation because the harness
ships with a trace writer and Part B made me write a grounded check. For this
task, the gap that matters most is Control & Policy. My bounds cap spending, but
nothing reviews a comment before it's posted. That's exactly how the agent's 16
wrong comments got out.

## Part D · The hybrid
Your hand-off rule, and the Part B traces that led you to it (written before you
measure). Its row beside the three ways (the same columns as Part B's table), how many of
its runs handed the issue to the agent, and its measured cost per run beside your
blended cost from Part C, item 3. Does it change your Part C verdict? Which of
the four would you ship, and why?

**My hand-off rule, written before I measured the hybrid.** Send the issue to
the agent when the workflow's choice doesn't name a file, meaning it answers
`none` or a folder, which is a path ending in `/`, for any label other than
`question`.

To choose this rule, I started from Part C. With *f* at 0, I aimed at the
issues where the agent passed more often than the workflow: 4202, with 3 of 10
vs 0 of 10, and 4205, with 9 of 10 vs 8 of 10. For each candidate rule, I
counted how often it would have fired on the workflow's 60 Part B runs, of
which 28 failed and 32 passed:

| Candidate rule | Fires on failing runs | Fires on passing runs |
|---|---|---|
| Every `search_repo` call returned `No matches.` | 0 | 0 |
| The chosen file isn't in any search result | 15 (4202 ×10, 4206 ×5) | 9 (all on 4203) |
| No file named, for anything other than a question | 0 | 0 |
| Same as above, with a folder counting as no file | 9 (all on 4202) | 0 |

The traces explain the choice. In `workflow-4202-s02-977497`, the workflow
searched `feature`, `TSV`, `export` and `format`. README and docs lines filled
the 10-result cap, `src/exportUtils.ts` never appeared, and it answered
`file: src/export/`, a folder. It did this in 9 of its 10 runs on 4202. The
"not in results" rule would catch 6 more failures, but five of those are on
4206, where the agent scored 0 of 10. The sixth is the single 4202 run that
answered `src/export/csv.ts`. That rule would also hand off the 9 runs on 4203
that the workflow already got right, at about five times the cost each. As for
the 4204 failures, where `src/util/dates.ts` was in the results and it still
picked `rollup.ts`, and the two 4205 runs labelled docs, nothing the workflow
can see sets them apart, so no rule here helps with those.

My prediction: about 9 hand-offs, all on 4202. At the agent's 4202 pass rate,
roughly 3 of them become passes, giving about 34 or 35 of 60. Cost would be
about $0.000267 + 9/60 × $0.00194 ≈ $0.00056 per run. One caveat: I chose the
rule by looking at the same six issues I'm measuring it on. So the prediction
is optimistic. The rule fires on exactly the failure I designed it for, and it
hasn't been tried on any new issue.

**Results.** These are 60 runs of `python run.py --way hybrid --set eval --runs 10`,
without a `make reset` beforehand, measured after I wrote the rule above. The
three approaches from Part B are shown for comparison:

| Approach | Passes (of 60) | 4201 | 4202 | 4203 | 4204 | 4205 | 4206 | Per-sweep range (of 6) | Issues solved 10/10 |
|---|---|---|---|---|---|---|---|---|---|
| Direct call | 40 | 10 | 10 | 10 | 0 | 10 | 0 | 4–4 | 4 |
| Workflow | 32 | 10 | 0 | 9 | 0 | 8 | 5 | 2–4 | 1 |
| Agent | 31 | 10 | 3 | 9 | 0 | 9 | 0 | 2–4 | 1 |
| Hybrid | 39 | 10 | 3 | 10 | 0 | 7 | 9 | 3–5 | 2 |

| Approach | Prompt tokens per run (uncached + cached) | Output tokens per run | Latency p50 / p95 | Cost per run | Tool calls per run, mean (max) |
|---|---|---|---|---|---|
| Direct call | 1,114.0 (845.2 + 268.8) | 12.2 | 0.6 s / 1.2 s | $0.000177 | 2.0 (2) |
| Workflow | 1,625.2 (1,279.6 + 345.6) | 21.8 | 1.2 s / 9.9 s | $0.000267 | 6.0 (6) |
| Agent | 11,720.6 (6,028.9 + 5,691.7) | 154.2 | 7.2 s / 51.2 s | $0.001350 | 9.1 (21) |
| Hybrid | 3,211.7 (2,471.4 + 740.3) | 42.4 | 1.6 s / 42.9 s | $0.000518 | 7.1 (22) |

**Hand-offs: 6 of 60, all on 4202.** The rule fired only on the issue I aimed
it at, never anywhere else. But none of the 6 hand-offs passed. Four times the
agent posted the same folder, `src/export/`, for example in
`hybrid-4202-s03-66839c`, and twice it hit the turn limit without posting, for
example in `hybrid-4202-s07-884caf`. All 39 passes came from the 54 runs that
stayed in the workflow.

So the hybrid's 39 vs the workflow's 32 wasn't the agent's doing. The workflow
itself behaved differently this time. On 4206, its search terms included
`dedupe` in 9 of 10 runs, up from 5 of 10 in Part B. On 4202, it found
`src/exportUtils.ts` on its own in 3 runs, for example in
`hybrid-4202-s01-2ca768`, which it never did in Part B. Same code, same
settings: 32 of 60 the first time, the equivalent of 39 the second. Even 10
runs per issue leaves a lot of spread, and a 7-pass gap between two approaches
could be noise.

**Cost: $0.000518 per run measured, vs $0.000267 blended** from Part C, item 3.
The blended figure uses *f* = 0, so it assumes a hybrid that never hands off
and costs the same as the workflow. Almost all of the $0.000251 gap comes from
the 6 hand-offs. Each one paid for the workflow's two calls plus about ten
agent calls, averaging $0.00262 per handed-off run. So 10% of the runs
accounted for 51% of the hybrid's total cost. I had estimated $0.00056 with 9
hand-offs. With only 6, the real cost came in a bit lower. The 42.9 s p95 is
mostly the rate limit again, since the runs that stayed in the workflow had the
same p95.

**Does this change my Part C verdict?** No. As a detector, the rule worked: it
fired only on runs the workflow was getting wrong. But the agent couldn't fix
them, so the hand-off added cost without adding passes. That's Part C's *f* = 0
playing out in practice: on the issue where the workflow fails, the agent does
no better.

**Which of the four would I ship?** The direct call. It scored 40 of 60, gave
the same answer every sweep, costs $0.000177 a run, about a third of the
hybrid's cost, and has a 1.2 s p95. The catch is that it only works because the
repo summary describes the files well, so someone has to keep that summary
current. If it went stale, I'd fall back to the workflow, not the agent. My
final verdict in `analysis.verdict` is workflow: the control flow stays in my
code.

## Assistance
Which AI tool, what it wrote, what you checked.

I used Claude Code, in VS Code throughout this assignment. I set up the repository and environment myself and ran make setup, make test and make ping. I compared free and paid model options, checked the rate limits in my own Google and Mistral accounts, chose ministral-14b-2512, and set up its API key. I wrote the code in agent/, ways/ and eval/ and the prompts in prompts/ with assistance from Claude Code, tuned the prompts on the two dev issues, and ran the dev and evaluation runs. I drafted the predictions with assistance from Claude Code, then reviewed and approved them and pushed them myself before the first evaluation run. I asked Claude Code to explain each part of the assignment. I drafted this report, ARCHITECTURE.md and CHANGES.md entirely myself, and Claude Code only helped correct my grammar and checked every number against the traces, which caught three factual errors that I then corrected. I set the writing style, edited some of the code comments, wrote a small amount of code myself, made every commit and push, and ran make check-01 before submitting.
