"""The three interviewers and the multi-round debate.

Each 'agent' is one AI call with a different personality (system prompt).
The personalities are deliberately in conflict, so they disagree on purpose.

The personas use the SAME convergence fix as the full project: a score band,
explicit permission to ignore other factors, and an ignore-list. Without these,
all three agents drift to the same verdict (the "convergence bug").
"""
from schemas import Scorecard, Rebuttal
from llm import run_structured


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
    """Run ONE interviewer. Returns its Scorecard."""
    user = (
        f"Here is the candidate's resume:\n{resume}\n\n"
        f"Here is the job description:\n{jd}\n\n"
        "Score this candidate ONLY on your own area of focus, following your scoring rule "
        "exactly. Ignore every factor outside your focus. Fill in the scorecard."
    )
    return run_structured(PERSONAS[name], user, Scorecard)


def score_all(resume: str, jd: str) -> dict[str, Scorecard]:
    """Run all three interviewers independently. None sees the others' answers."""
    return {name: score_one(name, resume, jd) for name in PERSONAS}


def debate_round(scores: dict[str, Scorecard], prior_rounds: list, resume: str, jd: str) -> dict[str, Rebuttal]:
    """One round of debate. Each interviewer sees the others' ORIGINAL positions plus what
    everyone argued in the PREVIOUS round, then writes a fresh rebuttal.
    They are NOT allowed to change their score - only to argue.
    """
    rebuttals = {}
    for name in PERSONAS:
        own = scores[name]

        # What the others said originally.
        others = "\n".join(
            f"- {other}: {sc.score}/10 ({sc.recommendation}). {sc.reasoning}"
            for other, sc in scores.items() if other != name
        )

        # What the others argued in the most recent round (if any).
        last_round_text = ""
        if prior_rounds:
            last = prior_rounds[-1]
            last_round_text = "In the previous round they argued:\n" + "\n".join(
                f"- {other} argued: {reb.argument}"
                for other, reb in last.items() if other != name
            ) + "\n"

        system = PERSONAS[name] + (
            " You are in a live, multi-round debate with the other two interviewers. "
            "Defend your score strictly from your area of focus and respond to their latest "
            "points. Do NOT change your score in this round; just argue your case."
        )
        user = (
            f"Candidate resume:\n{resume}\n\nJob description:\n{jd}\n\n"
            f"Your score: {own.score}/10 ({own.recommendation}). Your reasoning: {own.reasoning}\n\n"
            f"The other interviewers' original positions:\n{others}\n\n"
            f"{last_round_text}"
            "Write a short rebuttal (2-4 sentences) responding to their latest points, strictly "
            "from your area of focus, and state whether you still hold your position."
        )
        rebuttals[name] = run_structured(system, user, Rebuttal)
    return rebuttals
