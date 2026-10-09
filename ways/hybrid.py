from ways import agent, workflow


def names_no_file(label: str, file: str | None) -> bool:
    return label != "question" and (file in (None, "none") or file.endswith("/"))


def run(ctx) -> None:
    gathered = workflow.gather(ctx)
    label, file = workflow.choose(ctx, gathered)
    if names_no_file(label, file):
        agent.run(ctx)
    else:
        workflow.post(ctx, label, file)
