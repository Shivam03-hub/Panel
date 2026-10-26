"""The ONE place that calls Groq. Strict JSON output + LangSmith tracing + retry.

Every AI call in the whole project goes through here. That's why tracing covers
everything, and why one retry fix protects every call at once.
"""
import os
import time
from dotenv import load_dotenv
from groq import Groq
from langsmith import traceable

load_dotenv()

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-20b"   # fast, has a free tier, supports strict JSON


def _is_rate_limit(e) -> bool:
    """Is this error Groq saying 'slow down'? (HTTP 429)"""
    status = getattr(e, "status_code", None)
    msg = str(e).lower()
    return status == 429 or "rate" in msg and "limit" in msg


def _call_with_retry(**kwargs):
    """Call Groq. If it's rate-limited, wait and try again, waiting longer each time."""
    delay = 3.0
    for attempt in range(7):               # up to 7 tries
        try:
            return _client.chat.completions.create(**kwargs)
        except Exception as e:
            if _is_rate_limit(e) and attempt < 6:
                time.sleep(delay)
                delay = min(delay * 1.7, 30.0)   # grow the wait, cap at 30s
                continue
            raise                          # any other error: fail immediately


@traceable(run_type="llm", name="groq_structured_call")
def run_structured(system_prompt: str, user_text: str, schema):
    """Send text to Groq and FORCE the reply to match `schema` exactly.

    Returns a validated instance of `schema` (a Pydantic object).
    """
    response = _call_with_retry(
        model=MODEL,
        temperature=0,  # no randomness — scores must be stable and comparable
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__.lower(),
                "strict": True,                 # <- the key line: reply cannot break the shape
                "schema": schema.model_json_schema(),
            },
        },
    )
    raw = response.choices[0].message.content
    return schema.model_validate_json(raw)      # second check, turns it into a Python object


@traceable(run_type="llm", name="groq_chat")
def chat_reply(messages: list, temperature: float = 0.4) -> str:
    """Plain text reply (no fixed shape). Used by the 'ask the panel' chat."""
    response = _call_with_retry(model=MODEL, temperature=temperature, messages=messages)
    return response.choices[0].message.content or "Sorry, please try again."
