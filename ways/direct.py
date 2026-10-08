"""Way 1, the direct call. Nobody decides the next step: there is one step.

Read the issue (ctx.call_tool(0, "read_issue", {"number": ctx.issue_number})),
make ONE model call that gets the issue plus ctx.repo_summary and no tools, turn
its answer into a comment with harness.formats.format_triage_comment, and post it
with ctx.call_tool(1, "post_comment", ...). Your code posts the comment, not the
model.

Trace every model call (ctx.trace.model_call(step, response)). ctx.call_tool
calls a tool and traces it in one go; its step is the model call it belongs to,
0 before the first.
Keep your prompt in prompts/ and load it with ctx.prompt("direct.md").
"""

from harness.formats import format_triage_comment
from ways import read_answer, system_prompt


def run(ctx) -> None:
    issue = ctx.call_tool(0, "read_issue", {"number": ctx.issue_number}).content
    response = ctx.client.create(
        system=system_prompt(ctx, "direct.md"),
        messages=[{"role": "user", "content": f"Issue:\n{issue}\n\nRepository summary:\n{ctx.repo_summary}"}],
    )
    ctx.trace.model_call(1, response)
    label, file = read_answer(response.text)
    ctx.call_tool(1, "post_comment", {"number": ctx.issue_number, "body": format_triage_comment(label, file)})
