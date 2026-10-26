# SimplePanel — Multi-Agent AI Interview System

Most AI resume screeners give one opaque score. SimplePanel is an AI hiring panel that
argues with itself.

Three **tool-using LLM interviewer agents** with deliberately conflicting priorities
(technical depth, communication, hiring risk) score a candidate independently. Before
scoring, each one can call tools to **check that a claim really appears in the resume**
and to **compute exact job tenures**. A plain-code check decides if they genuinely
disagree. **Only then** do they debate, and each interviewer **remembers the whole
debate**. After every round an **LLM chair agent** decides whether another round is worth
it, with a hard round limit. A moderator gives one final verdict with a confidence level.
You can then chat with the panel to ask why.

Built with **LangGraph** (conditional routing + an AI-steered loop), **Groq** (tool
calling + strict JSON output), **Pydantic**, **LangSmith** (tracing), **MCP** (tool
layer), **FastAPI** + **Streamlit**, with simple **SQLite** login.

## How a run flows

```
resume + job
   -> 3 interviewer agents score (alone, may use tools)
   -> disagreement check (plain maths, no AI)
        if they agree    -> skip to the moderator
        if they disagree -> debate round
                         -> chair agent: debate again or finish?
                            (hard round limit)
   -> moderator verdict
```

## What each file does

```
backend/
  schemas.py        the fixed shapes every AI answer must fit (Pydantic)
  llm.py            the ONE place that calls Groq (strict JSON, tool loop, tracing)
  tools.py          the interviewers' tools: find_in_resume, months_between
  agents.py         the 3 interviewer agents + the debate rounds (with memory)
  disagreement.py   "do they disagree?" — plain maths, NO AI
  moderator.py      the chair agent (continue or finish?) + the final judge
  graph.py          LangGraph: wires it all, with the fork and the debate loop
  chat.py           "ask the panel why" — chat grounded in the saved result
  db.py             SQLite: users + runs (SQLAlchemy)
  auth.py           login: bcrypt passwords + JWT tokens
  api.py            FastAPI server: register, login, start run, check status, chat
  mcp_server.py     the engine as an MCP tool

frontend/
  app.py            Streamlit: login, run a panel, see the verdict, chat
```