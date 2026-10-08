"""Way 2, the workflow. Your code decides every step, in advance, in this order:

    read_issue  ->  one call to extract search terms  ->  search_repo
                ->  one call to choose the label and the file  ->  post_comment

A fixed sequence, no loop: the model never chooses a tool. Trace every model
call (ctx.trace.model_call); call every tool through ctx.call_tool(step, name,
input), which traces it. Keep your prompts in prompts/.

Part D reuses this way: its first half (read, extract, search) and its second
half (choose, post) are easier to reuse as two functions.
"""

from __future__ import annotations

import re

from harness.formats import format_triage_comment
from ways import read_answer, system_prompt

MAX_TERMS = 4  # one search per term, so this caps the workflow's tool calls at 6
QUOTES = " `'\"*"  # what a model wraps a term in: spaces, backticks, quotes, markdown emphasis


def search_terms(text: str) -> list[str]:
    """The model's search terms, one per line or comma-separated: bullets, numbering,
    quotes and headings dropped, duplicates removed, at most MAX_TERMS."""
    terms: list[str] = []
    for line in text.splitlines():
        if line.strip().endswith(":"):  # a heading such as "Search terms:"
            continue
        for piece in line.split(","):
            term = re.sub(r"^\s*(?:[-*•]\s+|\d+[.)]\s*)", "", piece)
            term = term.strip(QUOTES).rstrip(".;:").strip(QUOTES)
            if term and term.lower() not in {t.lower() for t in terms}:
                terms.append(term)
    return terms[:MAX_TERMS]


def gather(ctx) -> dict:
    """The first half, steps 0 and 1: read the issue, one call for search terms, one search per term."""
    issue = ctx.call_tool(0, "read_issue", {"number": ctx.issue_number}).content
    response = ctx.client.create(
        system=system_prompt(ctx, "workflow_terms.md"),
        messages=[{"role": "user", "content": f"Issue:\n{issue}"}],
    )
    ctx.trace.model_call(1, response)
    searches = {term: ctx.call_tool(1, "search_repo", {"query": term}).content
                for term in search_terms(response.text)}
    return {"issue": issue, "searches": searches}


def result_paths(searches: dict) -> list[str]:
    """Every file the searches found, in the order they first appear. A result line is path:line: text."""
    paths: list[str] = []
    for found in searches.values():
        for line in found.splitlines():
            path = line.split(":", 1)[0] if ":" in line else ""
            if path and path not in paths:
                paths.append(path)
    return paths


def choose(ctx, gathered: dict) -> tuple[str, str | None]:
    """The second half's model call, step 2: the label and the file, from the issue and the search results."""
    results = "\n\n".join(f"Search: {term}\n{found}" for term, found in gathered["searches"].items())
    files = "\n".join(f"- {path}" for path in result_paths(gathered["searches"]))
    response = ctx.client.create(
        system=system_prompt(ctx, "workflow_choose.md"),
        messages=[{"role": "user", "content": f"Issue:\n{gathered['issue']}\n\n"
                                              f"Search results:\n{results or 'No searches were run.'}\n\n"
                                              f"Files in the results:\n{files or 'none'}"}],
    )
    ctx.trace.model_call(2, response)
    return read_answer(response.text)


def post(ctx, label: str, file: str | None) -> None:
    ctx.call_tool(2, "post_comment", {"number": ctx.issue_number, "body": format_triage_comment(label, file)})


def run(ctx) -> None:
    gathered = gather(ctx)
    label, file = choose(ctx, gathered)
    post(ctx, label, file)
