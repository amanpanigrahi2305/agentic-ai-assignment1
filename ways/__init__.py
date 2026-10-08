"""The four ways of doing Assignment 1's task: direct, workflow, agent, and Part D's
hybrid, which you create. Each module has run(ctx) -> None.

ctx is a harness.runner.WayContext: ctx.issue_number, ctx.client, ctx.tools,
ctx.trace, ctx.call_tool(step, name, input), ctx.prompt(name), ctx.repo_summary. A way succeeds only if, when it
returns, the tracker holds exactly one comment from this run on this issue,
with the lines `label: <label>` and `file: <path or none>`.
"""


from harness.formats import parse_triage_comment


def system_prompt(ctx, name: str) -> str:
    """prompts/<name>, then the label definitions every prompt shares (prompts/labels.md)."""
    return f"{ctx.prompt(name).strip()}\n\n{ctx.prompt('labels.md').strip()}"


def read_answer(text: str) -> tuple[str, str | None]:
    """The label and file in a model's two-line answer, for the ways whose code posts the comment.
    Markdown emphasis is dropped first; a missing label posts as "unknown" and fails the check."""
    label, file = parse_triage_comment(text.replace("*", ""))
    return label or "unknown", file
