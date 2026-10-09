import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORDING = ROOT / "fixtures" / "week01_recorded_run.jsonl"
REPORT = ROOT / "reports" / "LAB_01.json"


def prompt_tokens(usage: dict) -> int:
    return (usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0))


def measure(path: Path = RECORDING) -> dict:
    calls = {}
    tool_calls = 0
    for line in path.read_text().splitlines():
        record = json.loads(line)
        if record.get("type") != "assistant":
            continue
        message = record["message"]
        calls.setdefault(message["id"], message.get("usage", {}))
        tool_calls += sum(1 for block in message.get("content", []) if block.get("type") == "tool_use")

    prompts = [prompt_tokens(usage) for usage in calls.values()]
    total = sum(prompts)
    cache_read = sum(usage.get("cache_read_input_tokens", 0) for usage in calls.values())
    return {
        "model_calls": len(calls),
        "tool_calls": tool_calls,
        "prompt_tokens": total,
        "cache_read_tokens": cache_read,
        "cache_read_share": round(cache_read / total, 3),
        "first_prompt": prompts[0],
        "last_prompt": prompts[-1],
        "cumulative_over_first": round(total / prompts[0], 2),
    }


def main() -> None:
    numbers = measure()
    print(json.dumps(numbers, indent=2))
    report = json.loads(REPORT.read_text())
    report["part0"] = numbers
    REPORT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
