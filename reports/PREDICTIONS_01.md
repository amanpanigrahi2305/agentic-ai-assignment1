# Predictions · Assignment 1

I wrote these before running any evaluation issue. The only tuning I did was on
the two dev issues (4191 and 4192), and the model stayed the same the whole time
(`ministral-14b-2512` on Mistral's API). After tuning, the dev results were:
direct call 3 of 6, workflow 6 of 6, agent 6 of 6.

| Way | Passes I expect (out of 60) | Hardest issue |
|---|---|---|
| Direct call | 25 | 4206 |
| Workflow | 30 | 4204 |
| Agent | 32 | 4206 |

**Direct call (25/60, hardest 4206).** It can't search the code, so it can only
name files that appear in the repo summary, and on 4206 I think it will just
trust the reporter that `src/export/csv.ts` is the broken file instead of finding
where the rows really get merged.

**Workflow (30/60, hardest 4204).** Its fixed searches use the issue's own words,
which should work when the issue quotes something that is in the code (an error
message, a format name, "localhost"), but the Monday email that arrives on
Tuesday is a time zone calculation that probably shares no words with the issue,
so I expect the searches to miss the right file.

**Agent (32/60, hardest 4206).** It can follow a lead that the workflow's fixed
searches would miss, so I expect it to do a little better than the workflow at
around six times the cost, but on 4206 the title already names
`src/export/csv.ts` and my prompt tells it to stop at the first line that matches
the issue, so I think it will post that file instead of looking for the step that
actually merges the rows.
