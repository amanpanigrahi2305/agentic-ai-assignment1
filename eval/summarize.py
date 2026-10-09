"""Assignment 1, Parts B to D: build the tables in reports/LAB_01.json from your runs. This file is yours.

Read every trace in runs/ and the comments in the tracker, decide each run's
success with your eval/check_triage.check, and compute the `results` entry for
each way (direct, workflow, agent, hybrid) and the computed fields of `analysis`.
Write them into reports/LAB_01.json and leave every other field (part0,
worst_case, verdict) as you set it. Every field is defined in checks/FORMATS.md,
section 7. The checker recomputes the counts and means the same way, so compute
them here, from the traces, never by hand.

    python -m eval.summarize
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from agent.loop import load_bounds
from eval.check_triage import check
from harness.formats import TERMINAL_REASONS
from harness.trace import read_trace
from harness.tracker import Tracker

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "LAB_01.json"
WAYS = ("direct", "workflow", "agent", "hybrid")
RUNS_PER_ISSUE = 10
SCRIPTED = {"never-stops"}
LOOP_REASONS = set(TERMINAL_REASONS) - {"completed", "crashed"}


def load_runs(eval_issues: set[int]) -> dict[str, list[dict]]:
    runs: dict[str, list[dict]] = {way: [] for way in WAYS}
    for path in sorted((ROOT / "runs").glob("*.jsonl")):
        if path.name.startswith("_"):
            continue
        records = read_trace(path)
        start = records[0] if records and records[0]["type"] == "run_start" else None
        end = records[-1] if records and records[-1]["type"] == "run_end" else None
        if not start or not end or start.get("lab") != "01" or start.get("way") not in WAYS:
            continue
        if start.get("backend") in SCRIPTED or start.get("issue") not in eval_issues:
            continue
        runs[start["way"]].append({
            "run_id": start["run_id"], "issue": start["issue"], "sweep": start["sweep"],
            "model_calls": [r for r in records if r["type"] == "model_call"],
            "tool_calls": [r for r in records if r["type"] == "tool_call"],
            "end": next((r for r in records if r["type"] == "end"), {}),
            "run_end": end,
        })
    return runs


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def nearest_rank(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(1, math.ceil(pct / 100 * len(ordered))) - 1]


def rounded(value: float | None, digits: int) -> float | None:
    return None if value is None else round(value, digits)


def way_results(runs: list[dict], passed: dict[str, bool], issues: list[int]) -> dict:
    per_issue_runs, per_issue_pass, per_sweep = defaultdict(int), defaultdict(int), defaultdict(int)
    for run in runs:
        per_issue_runs[run["issue"]] += 1
        per_issue_pass[run["issue"]] += passed[run["run_id"]]
        per_sweep[run["sweep"]] += passed[run["run_id"]]

    def per_run(field: str) -> list[float]:
        return [sum(c["usage"][field] for c in run["model_calls"]) for run in runs]

    tool_counts = [len(run["tool_calls"]) for run in runs]
    elapsed = [run["run_end"]["elapsed_s"] for run in runs]
    return {
        "runs": len(runs),
        "passes": sum(passed[run["run_id"]] for run in runs),
        "per_issue": {str(i): per_issue_pass[i] for i in issues},
        "sweep_min": min(per_sweep.values(), default=None),
        "sweep_max": max(per_sweep.values(), default=None),
        "all_ten": sum(1 for i in issues
                       if per_issue_runs[i] >= RUNS_PER_ISSUE and per_issue_pass[i] == per_issue_runs[i]),
        "mean_prompt_tokens": rounded(mean(per_run("prompt_tokens")), 1),
        "mean_output_tokens": rounded(mean(per_run("output_tokens")), 1),
        "mean_cached_tokens": rounded(mean(per_run("cache_read_input_tokens")), 1),
        "p50_latency_s": nearest_rank(elapsed, 50),
        "p95_latency_s": nearest_rank(elapsed, 95),
        "mean_cost_usd": rounded(mean([sum(c["cost_usd"] or 0 for c in run["model_calls"]) for run in runs]), 8),
        "mean_tool_calls": rounded(mean(tool_counts), 2),
        "max_tool_calls": max(tool_counts, default=None),
    }


def share_agent_earns_it(baseline: dict, agent: dict, issues: list[int]) -> float | None:
    if not baseline["runs"] or not agent["runs"]:
        return None
    won = [i for i in issues if baseline["per_issue"][str(i)] < 5 <= agent["per_issue"][str(i)]]
    return len(won) / len(issues)


def path_entropy(agent_runs: list[dict]) -> dict:
    sequences = Counter(tuple(t["name"] for t in run["tool_calls"]) for run in agent_runs)
    if not agent_runs:
        return {"distinct_sequences": None, "top3_share": None}
    top3 = sum(count for _, count in sequences.most_common(3))
    return {"distinct_sequences": len(sequences), "top3_share": round(top3 / len(agent_runs), 3)}


def measured_worst_case(agent_runs: list[dict], n: int) -> dict:
    prompts = [[c["usage"]["prompt_tokens"] for c in run["model_calls"]] for run in agent_runs if run["model_calls"]]
    f = round(mean([p[0] for p in prompts]), 1)
    a = round(mean([later - earlier for p in prompts for earlier, later in zip(p, p[1:])]), 1)
    return {"F": f, "A": a, "N": n, "cumulative_prompt_tokens": round(n * f + a * n * (n - 1) / 2, 1)}


def analysis_fields(results: dict, runs: dict, issues: list[int]) -> dict:
    direct, workflow, agent = results["direct"], results["workflow"], results["agent"]
    fields = {"path_entropy": path_entropy(runs["agent"])}
    if direct["runs"] and agent["runs"]:
        fields["ratio_agent_over_direct_tokens"] = round(
            (agent["mean_prompt_tokens"] + agent["mean_output_tokens"])
            / (direct["mean_prompt_tokens"] + direct["mean_output_tokens"]), 3)
    if workflow["runs"] and agent["runs"]:
        c = workflow["mean_cost_usd"]
        m = agent["mean_cost_usd"] / c
        f = share_agent_earns_it(workflow, agent, issues)
        fields.update({"m_agent_over_workflow_cost": round(m, 3), "f": round(f, 3),
                       "blended_cost": rounded(c * ((1 - f) + f * m), 8),
                       "all_agent_cost": rounded(c * m, 8), "workflow_cost": c})
    if runs["hybrid"]:
        fields["hybrid_handoffs"] = sum(1 for run in runs["hybrid"] if run["end"].get("terminal_reason") in LOOP_REASONS)
    return fields


def print_report(results: dict, analysis: dict, issues: list[int]) -> None:
    print("| Way | Passes /60 | " + " | ".join(str(i) for i in issues) + " | Sweep min-max | All 10/10 "
          "| Prompt tok | Output tok | Cached tok | p50 s | p95 s | Cost/run $ | Tool calls mean (max) |")
    print("|---" * (len(issues) + 11) + "|")
    for way in WAYS:
        r = results[way]
        if not r["runs"]:
            continue
        print(f"| {way} | {r['passes']}/{r['runs']} | " + " | ".join(str(r["per_issue"][str(i)]) for i in issues)
              + f" | {r['sweep_min']}-{r['sweep_max']} | {r['all_ten']} | {r['mean_prompt_tokens']:,.0f}"
              f" | {r['mean_output_tokens']:,.0f} | {r['mean_cached_tokens']:,.0f} | {r['p50_latency_s']:.1f}"
              f" | {r['p95_latency_s']:.1f} | {r['mean_cost_usd']:.6f} | {r['mean_tool_calls']:.1f} ({r['max_tool_calls']}) |")

    direct, workflow, agent = results["direct"], results["workflow"], results["agent"]
    if not (direct["runs"] and workflow["runs"] and agent["runs"]):
        return
    print(f"\nanalysis: {json.dumps(analysis)}")
    c, m, f = direct["mean_cost_usd"], agent["mean_cost_usd"] / direct["mean_cost_usd"], \
        share_agent_earns_it(direct, agent, issues)
    print(f"slide 31 against the direct call: c={c:.8f}, m={m:.3f}, f={f:.3f}, "
          f"blended={c * ((1 - f) + f * m):.8f}, all-agent={c * m:.8f}")
    for name, base in (("workflow", workflow), ("direct", direct)):
        extra_cost = agent["mean_cost_usd"] - base["mean_cost_usd"]
        extra_passes = (agent["passes"] / agent["runs"]) - (base["passes"] / base["runs"])
        per_triage = f"${extra_cost / extra_passes:.6f}" if extra_passes > 0 else "n/a (the agent passes no more often)"
        print(f"agent over {name}: extra cost per run ${extra_cost:.6f}, extra passes per run {extra_passes:+.3f}, "
              f"cost per extra correct triage {per_triage}")


def main() -> None:
    answers = {int(k): v for k, v in yaml.safe_load((ROOT / "fixtures" / "answers.yaml").read_text())["eval"].items()}
    issues = sorted(answers)
    tracker = Tracker(ROOT)
    runs = load_runs(set(issues))
    passed = {run["run_id"]: check(tracker, run["run_id"], run["issue"], answers[run["issue"]])
              for way in WAYS for run in runs[way]}
    results = {way: way_results(runs[way], passed, issues) for way in WAYS}
    analysis = analysis_fields(results, runs, issues)

    report = json.loads(REPORT.read_text())
    report["results"] = results
    report["analysis"].update(analysis)
    if runs["agent"]:
        report["worst_case"] = measured_worst_case(runs["agent"], load_bounds().max_steps)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print_report(results, report["analysis"], issues)
    print(f"\nworst_case: {report['worst_case']}")


if __name__ == "__main__":
    main()
