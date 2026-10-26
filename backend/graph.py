r"""LangGraph flowchart. This is the orchestration layer (resume bullet 2).

    panel -> disagreement -> (fork) --disagree--> debate -> chair --(again)--> debate ...
                                \                                  \--(finish)--> moderator
                                 \--agree-------------------------------------> moderator

The fork is plain code (cheap, predictable). After each debate round, a CHAIR AGENT (an LLM)
decides whether another round is worth it. The round limit stays as a hard safety cap, so the
agent can stop early but can never loop forever.
"""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from agents import score_all, debate_round
from disagreement import detect
from moderator import decide, chair_decide


class State(TypedDict):
    # inputs
    resume: str
    jd: str
    sensitivity: str
    max_rounds: int
    # filled in as it runs
    scores: dict
    disagreement: dict
    debate: list
    round_number: int
    next_step: str        # the chair agent's latest decision: "debate_again" or "finish"
    chair_notes: list     # one {"next_step", "reason"} per round, so you can see why it stopped
    verdict: object


def panel_node(state: State):
    return {"scores": score_all(state["resume"], state["jd"])}


def disagreement_node(state: State):
    return {"disagreement": detect(state["scores"], state["sensitivity"])}


def debate_node(state: State):
    prior = state.get("debate", [])
    # pass all prior rounds so agents remember the whole debate (their memory)
    new_round = debate_round(state["scores"], prior, state["resume"], state["jd"])
    history = prior + [new_round]
    return {"debate": history, "round_number": len(history)}


def chair_node(state: State):
    """The chair agent decides what to do next. The round cap is a hard safety limit."""
    notes = state.get("chair_notes", [])
    if state["round_number"] >= state["max_rounds"]:
        # Safety cap reached: finish without asking the LLM (saves a call, can't loop forever).
        note = {"next_step": "finish", "reason": "Round limit reached."}
        return {"next_step": "finish", "chair_notes": notes + [note]}
    decision = chair_decide(state["scores"], state["debate"])
    return {"next_step": decision.next_step, "chair_notes": notes + [decision.model_dump()]}


def moderator_node(state: State):
    return {"verdict": decide(state["scores"], state.get("debate", []),
                              state["resume"], state["jd"])}


# --- routers: tiny functions that read the state and pick the next step ---

def after_disagreement(state: State):
    """Fork: debate if they disagree, else skip straight to the moderator."""
    return "debate" if state["disagreement"]["is_disagreement"] else "skip"


def after_chair(state: State):
    """Follow the chair agent's decision (already capped by the round limit)."""
    return "again" if state["next_step"] == "debate_again" else "stop"


def build_graph():
    g = StateGraph(State)
    g.add_node("panel", panel_node)
    g.add_node("disagreement", disagreement_node)
    g.add_node("debate", debate_node)
    g.add_node("chair", chair_node)
    g.add_node("moderator", moderator_node)

    g.add_edge(START, "panel")
    g.add_edge("panel", "disagreement")
    g.add_conditional_edges("disagreement", after_disagreement,
                            {"debate": "debate", "skip": "moderator"})
    g.add_edge("debate", "chair")
    g.add_conditional_edges("chair", after_chair,
                            {"again": "debate", "stop": "moderator"})  # "again" loops back
    g.add_edge("moderator", END)
    return g.compile()


# Build once, reuse for every run.
GRAPH = build_graph()


def run_panel(resume: str, jd: str, sensitivity: str = "high", max_rounds: int = 2) -> dict:
    """Run the whole engine. Returns a plain dict ready to save/show."""
    final = GRAPH.invoke({
        "resume": resume, "jd": jd,
        "sensitivity": sensitivity, "max_rounds": max_rounds,
    })
    return {
        "scores": {n: s.model_dump() for n, s in final["scores"].items()},
        "disagreement": final["disagreement"],
        "debate": [
            {n: r.model_dump() for n, r in rnd.items()}
            for rnd in final.get("debate", [])
        ],
        "chair_notes": final.get("chair_notes", []),
        "verdict": final["verdict"].model_dump(),
    }