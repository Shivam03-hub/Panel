"""The moderator: reads everything, gives ONE final verdict. LLM-as-judge.

Same instructions as the full project: do NOT average, weigh what the role needs,
and lower confidence if the panel stayed split.
"""
from schemas import Scorecard, Rebuttal, Verdict, ChairDecision
from llm import run_structured


SYSTEM = (
    "You are the neutral moderator of a hiring panel. Three interviewers with different "
    "priorities (technical depth, communication, hiring risk) have independently scored a "
    "candidate and, where they disagreed, debated. "
    "Your job is to weigh all of their input fairly and deliver ONE final verdict for this "
    "specific role. Do NOT simply average the scores; judge what matters most for THIS job "
    "based on its responsibilities and requirements. "
    "Consider how strongly the interviewers disagreed and whether the debate resolved it: if "
    "they stayed sharply split on important points, lower your confidence accordingly. "
    "Be balanced, decisive, and specific."
)


def _format_scores(scores: dict[str, Scorecard]) -> str:
    out = ""
    for name, s in scores.items():
        strengths = ", ".join(s.strengths) if s.strengths else "none listed"
        concerns = ", ".join(s.concerns) if s.concerns else "none listed"
        out += (f"\n[{name}] score {s.score}/10, recommendation: {s.recommendation}\n"
                f"  Reasoning: {s.reasoning}\n  Strengths: {strengths}\n  Concerns: {concerns}\n")
    return out


def _format_debate(debate: list[dict[str, Rebuttal]]) -> str:
    if not debate:
        return "No debate took place (the panel broadly agreed).\n"
    out = ""
    for i, rnd in enumerate(debate, 1):
        out += f"\n-- Round {i} --\n"
        for name, reb in rnd.items():
            stance = "holds position" if reb.holds_position else "reconsidering"
            out += f"  {name} ({stance}): {reb.argument}\n"
    return out


CHAIR_SYSTEM = (
    "You are the chair of a hiring panel debate. After each debate round you decide what "
    "happens next. Choose 'debate_again' only if another round is likely to bring NEW arguments "
    "or change someone's position. Choose 'finish' if the interviewers are repeating themselves, "
    "have converged, or the key disagreement is already clear enough for a final verdict. "
    "Each round costs time and money, so do not continue without a good reason."
)


def chair_decide(scores: dict[str, Scorecard], debate: list[dict[str, Rebuttal]]) -> ChairDecision:
    """The chair agent: reads the scores and the debate so far, decides continue or finish."""
    user = (
        f"Interviewer scorecards:{_format_scores(scores)}\n"
        f"Debate so far:{_format_debate(debate)}\n\n"
        "Decide the next step: another debate round, or finish and hand over to the moderator."
    )
    return run_structured(CHAIR_SYSTEM, user, ChairDecision)


def decide(scores: dict[str, Scorecard], debate: list[dict[str, Rebuttal]],
           resume: str, jd: str) -> Verdict:
    """Produce the final Verdict from everything the panel did."""
    user = (
        f"Candidate resume:\n{resume}\n\nJob description:\n{jd}\n\n"
        f"Interviewer scorecards:{_format_scores(scores)}\n"
        f"Debate transcript:{_format_debate(debate)}\n\n"
        "Now deliver the final verdict for this role. Fill in the verdict: a final "
        "recommendation, an overall score (1-10), your confidence, a short rationale, the key "
        "strengths, and the key risks."
    )
    return run_structured(SYSTEM, user, Verdict)