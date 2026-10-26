"""Streamlit frontend. One file. Login screen, then run a panel and see the verdict."""
import time
import requests
import streamlit as st

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="Panel", page_icon="⚖️", layout="centered")

# session_state survives Streamlit's reruns. We keep the login token here.
st.session_state.setdefault("token", None)
st.session_state.setdefault("run_id", None)

REC_LABEL = {
    "strong_hire": "🌟 Strong Hire", "hire": "✅ Hire",
    "no_hire": "⚠️ No Hire", "strong_no_hire": "⛔ Strong No Hire",
}

SAMPLE_RESUME = """Ravi Kumar — Backend Engineer
Experience: Backend Engineer, FinPay (Mar 2023 - Jan 2024). Software Engineer,
QuickCart (Feb 2022 - Dec 2022). Junior Developer, DevHouse (Jun 2021 - Jan 2022).
Skills: Python, Go, PostgreSQL, Redis, Docker, Kubernetes, gRPC. B.Tech CS, VIT 2021."""

SAMPLE_JD = """Senior Backend Engineer. Lead our payments platform. Design large-scale
payment systems, mentor junior engineers, work with product, explain technical decisions
to non-technical stakeholders. Required: 5+ years backend, Python, distributed systems,
PostgreSQL. Preferred: Go, Kubernetes."""


def headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


# ---------------- LOGIN SCREEN ----------------

if not st.session_state.token:
    st.title("⚖️ Panel")
    st.caption("An AI hiring panel that argues with itself.")
    tab_login, tab_signup = st.tabs(["Log in", "Create account"])

    with tab_login:
        e = st.text_input("Email", key="le")
        p = st.text_input("Password", type="password", key="lp")
        if st.button("Log in"):
            r = requests.post(f"{API}/login", json={"email": e, "password": p})
            if r.status_code == 200:
                st.session_state.token = r.json()["token"]
                st.rerun()
            else:
                st.error(r.json().get("detail", "Login failed"))

    with tab_signup:
        e2 = st.text_input("Email", key="se")
        p2 = st.text_input("Password (6+ chars)", type="password", key="sp")
        if st.button("Create account"):
            r = requests.post(f"{API}/register", json={"email": e2, "password": p2})
            if r.status_code == 200:
                st.session_state.token = r.json()["token"]
                st.rerun()
            else:
                st.error(r.json().get("detail", "Sign up failed"))
    st.stop()


# ---------------- MAIN APP ----------------

with st.sidebar:
    st.header("⚖️ Panel")
    if st.button("Log out"):
        st.session_state.token = None
        st.session_state.run_id = None
        st.rerun()

st.title("Convene the panel")

col1, col2 = st.columns(2)
resume = col1.text_area("Candidate resume", SAMPLE_RESUME, height=220)
jd = col2.text_area("Job description", SAMPLE_JD, height=220)

c1, c2 = st.columns(2)
sensitivity = c1.selectbox("Strictness", ["high", "medium", "low"])
max_rounds = c2.selectbox("Debate rounds", [1, 2, 3], index=1)

if st.button("⚖️ Run the Panel", type="primary"):
    r = requests.post(f"{API}/runs", headers=headers(),
                      json={"resume": resume, "jd": jd,
                            "sensitivity": sensitivity, "max_rounds": max_rounds})
    if r.status_code == 200:
        st.session_state.run_id = r.json()["id"]
    else:
        st.error("Could not start the run. Is the backend running?")


# ---------------- WAIT + SHOW RESULT ----------------

if st.session_state.run_id:
    run_id = st.session_state.run_id
    placeholder = st.empty()

    # Poll until the run is done or failed.
    while True:
        r = requests.get(f"{API}/runs/{run_id}", headers=headers())
        run = r.json()
        if run["status"] in ("pending", "running"):
            placeholder.info("🧑‍⚖️ The panel is deliberating… (about a minute)")
            time.sleep(2)
            continue
        break

    placeholder.empty()

    if run["status"] == "failed":
        st.error(f"Run failed: {run['error']}")
    else:
        res = run["result"]
        v = res["verdict"]

        st.subheader("Final verdict")
        st.markdown(f"## {REC_LABEL.get(v['recommendation'], v['recommendation'])}")
        st.markdown(f"**{v['overall_score']}/10 · confidence: {v['confidence']}**")
        st.write(v["rationale"])
        colL, colR = st.columns(2)
        colL.markdown("**✅ Key strengths**")
        for s in v.get("key_strengths", []):
            colL.markdown(f"- {s}")
        colR.markdown("**⚠️ Key risks**")
        for r in v.get("key_risks", []):
            colR.markdown(f"- {r}")

        st.divider()
        st.subheader("The panel")
        cols = st.columns(3)
        for col, (name, sc) in zip(cols, res["scores"].items()):
            col.markdown(f"**{name}**")
            col.markdown(f"### {sc['score']}/10")
            col.caption(REC_LABEL.get(sc["recommendation"], sc["recommendation"]))
            col.write(sc["reasoning"])
            if sc.get("strengths"):
                col.caption("Strengths: " + "; ".join(sc["strengths"]))
            if sc.get("concerns"):
                col.caption("Concerns: " + "; ".join(sc["concerns"]))

        st.divider()
        d = res["disagreement"]
        st.info(("🔥 " if d["is_disagreement"] else "🤝 ") + d["summary"])

        if res["debate"]:
            st.subheader("The debate")
            notes = res.get("chair_notes", [])
            for i, rnd in enumerate(res["debate"], 1):
                st.markdown(f"**Round {i}**")
                for name, reb in rnd.items():
                    stance = "holds position" if reb["holds_position"] else "reconsidering"
                    st.markdown(f"- **{name}** ({stance}): {reb['argument']}")
                # What the chair agent decided after this round, and why.
                if i <= len(notes):
                    st.caption(f"🪑 Chair → {notes[i - 1]['next_step']}: {notes[i - 1]['reason']}")

        # ---- ask the panel (chat) ----
        st.divider()
        st.subheader("💬 Ask the panel about this verdict")
        hist = requests.get(f"{API}/runs/{run_id}/chat", headers=headers()).json()["messages"]
        for m in hist:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
        q = st.chat_input("e.g. Why did the risk interviewer score so low?")
        if q:
            with st.chat_message("user"):
                st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    rep = requests.post(f"{API}/runs/{run_id}/chat", headers=headers(),
                                        json={"message": q}).json()["reply"]
                st.markdown(rep)