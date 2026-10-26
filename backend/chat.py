"""'Ask the panel why' chat. Answers questions about ONE finished run.

It is grounded: we paste the whole run (scores, debate, verdict) into the prompt,
so the AI answers from the real result, not from imagination.
"""
from llm import chat_reply


def _context(result: dict) -> str:
    """Flatten a saved run into a text record the AI can read."""
    lines = []
    for name, sc in result["scores"].items():
        lines.append(f"{name}: {sc['score']}/10 ({sc['recommendation']}). {sc['reasoning']}")
    lines.append(f"Disagreement: {result['disagreement']['summary']}")
    if result["debate"]:
        for i, rnd in enumerate(result["debate"], 1):
            for name, reb in rnd.items():
                lines.append(f"Round {i} {name}: {reb['argument']}")
    for i, note in enumerate(result.get("chair_notes", []), 1):
        lines.append(f"Chair after round {i}: {note['next_step']} - {note['reason']}")
    v = result["verdict"]
    lines.append(f"FINAL VERDICT: {v['recommendation']} ({v['overall_score']}/10, "
                 f"confidence {v['confidence']}). {v['rationale']}")
    return "\n".join(lines)


def answer(result: dict, history: list) -> str:
    """history = [{"role": "user"/"assistant", "content": "..."}]. Returns the reply."""
    system = (
        "You are the moderator of an AI hiring panel, talking to the user about ONE specific "
        "candidate evaluation. The full record is below. Answer helpfully and specifically using "
        "this record - including why the scores or verdict came out this way, and what the "
        "candidate could improve. Only decline if the question is unrelated to this candidate.\n\n"
        f"=== PANEL RECORD ===\n{_context(result)}\n=== END RECORD ==="
    )
    messages = [{"role": "system", "content": system}]
    for m in history:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": m["content"]})
    return chat_reply(messages)