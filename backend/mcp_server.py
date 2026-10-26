"""The three interviewer agents and the multi-round debate.

Each interviewer is a tool-using agent with its own personality (system prompt). While
scoring, it decides for itself whether to call tools (check a claim in the resume, compute
job lengths) before filling in its scorecard. The personalities deliberately conflict.

The personas use the SAME convergence fix as the full project: a score band,
explicit permission to ignore other factors, and an ignore-list. Without these,
all three agents drift to the same verdict (the "convergence bug").
"""
from schemas import Scorecard, Rebuttal
from llm import run_structured, run_agent
from tools import make_tools


PERSONAS = {
    "Technical": (
        "You are the Technical-Depth interviewer on a hiring panel. "
        "You judge the candidate ONLY on raw technical ability and how well their hard "
        "technical skills match the role's technical needs. "
        "CRITICAL SCORING RULE: your score must reflect technical skill ALONE. If the "
        "candidate is technically strong, give a HIGH score (8-10) EVEN IF they are short "
        "on years of experience, seniority, mentoring, or communication skills. Those are "
        "other interviewers' concerns, NOT yours. Only score low if the technical skills "
        "themselves are weak or a poor match for the role's technology. "
        "Completely ignore job tenure, career gaps, seniority level, and communication when scoring."
    ),
    "Communication": (
        "You are the Communication interviewer on a hiring panel. "
        "You judge the candidate ONLY on communication and collaboration: clarity of their "
        "writing, ability to explain technical work, and evidence of teamwork, mentoring, and "
        "communicating with non-technical people. "
        "CRITICAL SCORING RULE: your score must reflect communication ability ALONE. Completely "
        "ignore technical depth, years of experience, and hiring risk. Give a HIGH score if the "
        "resume shows clear, collaborative, well-explained experience; give a LOW score if it is "
        "vague, terse, or shows no sign of communication or teamwork - no matter how technically "
        "strong or how risky the candidate is."
    ),
    "Risk": (
        "You are the Risk-Aversion interviewer on a hiring panel. "
        "You judge the candidate ONLY on hiring risk and red flags: short job tenures, frequent "
        "job changes, career gaps, over-claiming, and whether the candidate's seniority and "
        "experience genuinely match what the role demands. "
        "CRITICAL SCORING RULE: your score must reflect hiring risk ALONE, where 10 means a very "
        "safe, low-risk hire and 1 means a very risky hire. Completely ignore how technically "
        "brilliant or how well-spoken the candidate is. Give a LOW score for instability, "
        "experience or seniority gaps, and mismatches; give a HIGH score only for a stable, "
        "proven, well-matched track record."
    ),
}


def score_one(name: str, resume: str, jd: str) -> Scorecard:
    """Run ONE interviewer agent. It may call tools first, then returns its Scorecard."""
    user = (
        f"Here is the candidate's resume:\n{resume}\n\n"
        f"Here is the job description:\n{jd}\n\n"
        "Score this candidate ONLY on your own area of focus, following your scoring rule "
        "exactly. Ignore every factor outside your focus. "
        "You have tools: use find_in_resume to check that a claim is really in the resume before "
        "you list it, and months_between to work out job lengths instead of guessing. "
        "Use them only if they help. Then fill in the scorecard."
    )
    tools, tool_fns = make_tools(resume)
    return run_agent(PERSONAS[name], user, Scorecard, tools, tool_fns)


def score_all(resume: str, jd: str) -> dict[str, Scorecard]:
    """Run all three interviewers independently. None sees the others' answers."""
    return {name: score_one(name, resume, jd) for name in PERSONAS}


def debate_round(scores: dict[str, Scorecard], prior_rounds: list, resume: str, jd: str) -> dict[str, Rebuttal]:
    """One round of debate. Each interviewer sees the others' ORIGINAL positions plus its
    MEMORY of the whole debate so far (every round, including its own earlier arguments),
    then writes a fresh rebuttal. They are NOT allowed to change their score - only to argue.
    """
    rebuttals = {}
    for name in PERSONAS:
        own = scores[name]

        # What the others said originally.
        others = "\n".join(
            f"- {other}: {sc.score}/10 ({sc.recommendation}). {sc.reasoning}"
            for other, sc in scores.items() if other != name
        )

        # Memory: the whole debate so far, including this interviewer's own earlier
        # arguments, so it can build on them instead of repeating itself.
        history_text = ""
        if prior_rounds:
            lines = []
            for i, rnd in enumerate(prior_rounds, 1):
                for who, reb in rnd.items():
                    speaker = "You" if who == name else who
                    lines.append(f"- Round {i}, {speaker}: {reb.argument}")
            history_text = "The debate so far:\n" + "\n".join(lines) + "\n"

        system = PERSONAS[name] + (
            " You are in a live, multi-round debate with the other two interviewers. "
            "Defend your score strictly from your area of focus and respond to their latest "
            "points. Do NOT change your score in this round; just argue your case."
        )
        user = (
            f"Candidate resume:\n{resume}\n\nJob description:\n{jd}\n\n"
            f"Your score: {own.score}/10 ({own.recommendation}). Your reasoning: {own.reasoning}\n\n"
            f"The other interviewers' original positions:\n{others}\n\n"
            f"{history_text}"
            "Write a short rebuttal (2-4 sentences) responding to their latest points, strictly "
            "from your area of focus. Do not repeat your earlier arguments; add something new or "
            "answer their strongest point. State whether you still hold your position."
        )
        rebuttals[name] = run_structured(system, user, Rebuttal)
    return rebuttals