"""Simplest possible database: SQLite, two tables (users, runs). SQLAlchemy ORM.

SQLite is just a file (panel.db). No server to install. Good enough for this.
"""
import os
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

engine = create_engine("sqlite:///panel.db", connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/running/done/failed
    error: Mapped[str] = mapped_column(Text, default="")
    result_json: Mapped[str] = mapped_column(Text, default="")          # the whole result as JSON
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    role: Mapped[str] = mapped_column(String(20))      # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(engine)


# ---- users ----

def create_user(email, password_hash):
    with Session(engine) as s:
        u = User(email=email, password_hash=password_hash)
        s.add(u); s.commit(); s.refresh(u)
        return {"id": u.id, "email": u.email}


def get_user_by_email(email):
    with Session(engine) as s:
        u = s.query(User).filter(User.email == email).first()
        return None if not u else {"id": u.id, "email": u.email, "password_hash": u.password_hash}


def get_user_by_id(uid):
    with Session(engine) as s:
        u = s.get(User, uid)
        return None if not u else {"id": u.id, "email": u.email}


# ---- runs ----

def create_run(user_id):
    with Session(engine) as s:
        r = Run(user_id=user_id, status="pending")
        s.add(r); s.commit(); s.refresh(r)
        return r.id


def set_status(run_id, status, error=""):
    with Session(engine) as s:
        r = s.get(Run, run_id)
        if r:
            r.status = status
            r.error = error
            s.commit()


def save_result(run_id, result: dict):
    with Session(engine) as s:
        r = s.get(Run, run_id)
        if r:
            r.status = "done"
            r.result_json = json.dumps(result)
            s.commit()


def get_run(run_id, user_id):
    with Session(engine) as s:
        r = s.get(Run, run_id)
        if not r or r.user_id != user_id:
            return None
        return {
            "id": r.id, "status": r.status, "error": r.error,
            "result": json.loads(r.result_json) if r.result_json else None,
        }


def list_runs(user_id):
    with Session(engine) as s:
        rows = s.query(Run).filter(Run.user_id == user_id).order_by(Run.created_at.desc()).all()
        return [{"id": r.id, "status": r.status, "created_at": r.created_at.isoformat()} for r in rows]


# ---- chat messages ----

def add_message(run_id, user_id, role, content):
    with Session(engine) as s:
        s.add(Message(run_id=run_id, user_id=user_id, role=role, content=content))
        s.commit()


def get_messages(run_id, user_id):
    with Session(engine) as s:
        rows = (s.query(Message)
                 .filter(Message.run_id == run_id, Message.user_id == user_id)
                 .order_by(Message.created_at.asc()).all())
        return [{"role": m.role, "content": m.content} for m in rows]
