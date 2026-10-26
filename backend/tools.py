"""Tools the interviewer agents can choose to call. Plain Python, no internet, no AI.

Each agent decides for itself whether to use them (that's what makes it an agent):
  - find_in_resume: check a claim really appears in the resume (stops made-up strengths)
  - months_between: exact job-length maths instead of the model guessing
"""
from datetime import date, datetime
from langsmith import traceable


def _parse_month(text: str):
    """'Mar 2023' / 'March 2023' / '2023-03' / '03/2023' / 'Present' -> (year, month)."""
    s = text.strip()
    if s.lower() in ("present", "now", "current", "today"):
        today = date.today()
        return today.year, today.month
    parts = s.split()
    if len(parts) == 2 and parts[0][:3].isalpha():
        s = f"{parts[0][:3].title()} {parts[1]}"          # "September 2023" -> "Sep 2023"
    for fmt in ("%b %Y", "%Y-%m", "%m/%Y"):
        try:
            d = datetime.strptime(s, fmt)
            return d.year, d.month
        except ValueError:
            pass
    raise ValueError(f"Can't read the date '{text}'. Use a format like 'Mar 2023'.")


def make_tools(resume: str):
    """Build the tools for ONE run. Returns (tool descriptions for Groq, {name: function})."""

    @traceable(run_type="tool", name="find_in_resume")
    def find_in_resume(phrase: str) -> str:
        phrase = phrase.strip()
        if not phrase:
            return "Empty phrase - nothing to search."
        i = resume.lower().find(phrase.lower())
        if i == -1:
            return f'NOT FOUND: "{phrase}" does not appear in the resume.'
        start, end = max(0, i - 60), min(len(resume), i + len(phrase) + 60)
        return f'FOUND: "...{resume[start:end]}..."'

    @traceable(run_type="tool", name="months_between")
    def months_between(start: str, end: str) -> str:
        y1, m1 = _parse_month(start)
        y2, m2 = _parse_month(end)
        months = (y2 - y1) * 12 + (m2 - m1)
        return f"{months} months ({months / 12:.1f} years)"

    specs = [
        {"type": "function", "function": {
            "name": "find_in_resume",
            "description": "Check whether a word or phrase really appears in the candidate's "
                           "resume. Returns the surrounding text if found, or NOT FOUND.",
            "parameters": {"type": "object",
                           "properties": {"phrase": {"type": "string",
                                                     "description": "Exact words to look for"}},
                           "required": ["phrase"]}}},
        {"type": "function", "function": {
            "name": "months_between",
            "description": "Exact number of months between two dates, e.g. a job's start and "
                           "end. Dates like 'Mar 2023' or 'Present'.",
            "parameters": {"type": "object",
                           "properties": {"start": {"type": "string"},
                                          "end": {"type": "string"}},
                           "required": ["start", "end"]}}},
    ]
    return specs, {"find_in_resume": find_in_resume, "months_between": months_between}