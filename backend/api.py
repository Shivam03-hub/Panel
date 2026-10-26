"""FastAPI web server. Login + start a run (in the background) + check status.

A run takes ~1 minute, which is too long for one web request. So we reply
instantly with a run id and do the work in the background; the frontend polls.
"""
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
import auth
import chat as chat_agent
from graph import run_panel

app = FastAPI(title="Panel API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

db.init_db()


# ---- request shapes ----

class AuthReq(BaseModel):
    email: str
    password: str


class RunReq(BaseModel):
    resume: str
    jd: str
    sensitivity: str = "high"
    max_rounds: int = 2


class ChatReq(BaseModel):
    message: str


# ---- the background job ----

def execute(run_id, resume, jd, sensitivity, max_rounds):
    try:
        db.set_status(run_id, "running")
        result = run_panel(resume, jd, sensitivity, max_rounds)
        db.save_result(run_id, result)
    except Exception as e:
        db.set_status(run_id, "failed", str(e))


# ---- auth ----

@app.post("/register")
def register(req: AuthReq):
    email = req.email.strip().lower()
    if "@" not in email or len(req.password) < 6:
        raise HTTPException(400, "Valid email and a 6+ char password required.")
    if db.get_user_by_email(email):
        raise HTTPException(400, "Email already registered.")
    user = db.create_user(email, auth.hash_password(req.password))
    return {"token": auth.make_token(user["id"], user["email"]), "user": user}


@app.post("/login")
def login(req: AuthReq):
    email = req.email.strip().lower()
    user = db.get_user_by_email(email)
    if not user or not auth.check_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Wrong email or password.")
    return {"token": auth.make_token(user["id"], user["email"]),
            "user": {"id": user["id"], "email": user["email"]}}


# ---- runs (login required) ----

@app.post("/runs")
def start_run(req: RunReq, tasks: BackgroundTasks, user=Depends(auth.current_user)):
    run_id = db.create_run(user["id"])
    tasks.add_task(execute, run_id, req.resume, req.jd, req.sensitivity, req.max_rounds)
    return {"id": run_id, "status": "pending"}


@app.get("/runs")
def my_runs(user=Depends(auth.current_user)):
    return db.list_runs(user["id"])


@app.get("/runs/{run_id}")
def get_run(run_id: int, user=Depends(auth.current_user)):
    run = db.get_run(run_id, user["id"])
    if not run:
        raise HTTPException(404, "Run not found")
    return run


# ---- chat about a finished run ----

@app.get("/runs/{run_id}/chat")
def read_chat(run_id: int, user=Depends(auth.current_user)):
    if not db.get_run(run_id, user["id"]):
        raise HTTPException(404, "Run not found")
    return {"messages": db.get_messages(run_id, user["id"])}


@app.post("/runs/{run_id}/chat")
def send_chat(run_id: int, req: ChatReq, user=Depends(auth.current_user)):
    run = db.get_run(run_id, user["id"])
    if not run or not run["result"]:
        raise HTTPException(404, "Run not found or not finished")
    db.add_message(run_id, user["id"], "user", req.message)
    history = db.get_messages(run_id, user["id"])
    reply = chat_agent.answer(run["result"], history)
    db.add_message(run_id, user["id"], "assistant", reply)
    return {"reply": reply}
