"""CashPilot dashboard (Streamlit). Owner: Irvin. Talks only to the FastAPI backend.

Run locally:  API_BASE=http://localhost:8000 streamlit run frontend/app.py
"""
import os
import time

import plotly.graph_objects as go
import requests
import streamlit as st

API = os.getenv("API_BASE", "http://localhost:8000")
st.set_page_config(page_title="CashPilot", page_icon="🍦", layout="wide")


def get(path, **params):
    r = requests.get(f"{API}{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def post(path, body=None):
    r = requests.post(f"{API}{path}", json=body or {}, timeout=90)
    r.raise_for_status()
    return r.json()


def money(x):
    return "—" if x is None else (f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}")


try:
    health = get("/api/health")
except Exception as exc:
    st.error(f"Backend not reachable at {API}: {exc}")
    st.stop()

# ---------- sidebar: scenario, demo controls ----------
with st.sidebar:
    st.header("CashPilot")
    scenarios = get("/api/scenarios")
    labels = {s["id"]: s["label"] for s in scenarios}
    scenario = st.radio("Scenario", list(labels), index=list(labels).index("live"), format_func=labels.get)
    st.caption(f"Model: {health['model_provider']}")
    st.divider()
    st.subheader("Demo controls")
    if st.button("Ridgeline pays 6 days late", width="stretch"):
        post("/api/events", {"type": "payment_delayed", "txn": "T08", "days": 6})
        st.toast("Event sent. The monitor is investigating.")
    if st.button("Reset demo", width="stretch"):
        post("/api/demo/reset")
        st.rerun()

ov = get("/api/overview", scenario=scenario)
s, f = ov["settings"], ov["forecast"]
st.title(f"🍦 {s['business']}")
st.caption(f"Cash forecast {f['days'][0]['date']} to {f['days'][-1]['date']} · reserve {money(s['min_reserve'])}")

# ---------- alerts ----------
for a in get("/api/alerts")[:1]:
    if a["status"] == "investigating":
        st.warning(f"⚠️ Alert {a['id']}: cash drops to {money(a['min_balance'])} on {a['min_date']}. Investigating…")
        time.sleep(2)
        st.rerun()
    else:
        st.error(f"⚠️ Alert {a['id']} ({a['trigger']}): cash drops to {money(a['min_balance'])} on {a['min_date']}, "
                 f"{money(a['shortfall_vs_reserve'])} below the reserve.")

# ---------- KPIs ----------
k = st.columns(4)
k[0].metric("Cash today", money(s["opening_cash"]))
k[1].metric("Lowest balance", money(f["min_balance"]), f"on {f['min_date']}", delta_color="off")
k[2].metric("Ending cash", money(f["ending_cash"]))
k[3].metric("Below reserve by", money(f["shortfall_vs_reserve"]),
            delta=("safe" if f["shortfall_vs_reserve"] == 0 else "at risk"),
            delta_color=("normal" if f["shortfall_vs_reserve"] == 0 else "inverse"))

# ---------- lever toggles + chart ----------
levers = get("/api/levers")
picked = st.multiselect("Try levers (what-if)", [lv["id"] for lv in levers],
                        format_func=lambda i: next(f"{lv['name']} (${lv['cost_usd']:,.2f})" for lv in levers if lv["id"] == i))
sim = post("/api/simulate", {"scenario": scenario, "lever_ids": picked}) if picked else None

x = [d["date"][5:] for d in f["days"]]
fig = go.Figure()
fig.add_scatter(x=x, y=[d["closing"] for d in f["days"]], name="Current plan", mode="lines+markers")
if sim:
    fig.add_scatter(x=x, y=[d["closing"] for d in sim["days"]], name="With selected levers", mode="lines+markers")
fig.add_hline(y=s["min_reserve"], line_dash="dash", annotation_text="Reserve")
fig.add_hline(y=0, line_color="gray")
fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Closing cash ($)", legend_orientation="h")
st.plotly_chart(fig, width="stretch")
if sim:
    st.info(f"With those levers: lowest balance {money(sim['min_balance'])} on {sim['min_date']}, "
            f"ending {money(sim['ending_cash'])}.")

# ---------- plan + cost of waiting ----------
left, right = st.columns(2)
with left:
    st.subheader("Cheapest safe plan")
    p = post("/api/optimize", {"scenario": scenario})
    if p["feasible"] and not p["levers"]:
        st.success("No action needed: cash stays above the reserve every day.")
    elif p["feasible"]:
        names = {lv["id"]: lv["name"] for lv in levers}
        for lid in p["levers"]:
            st.write(f"• {names[lid]}")
        st.metric("Total cost", f"${p['total_cost']:,.2f}")
        for r in p["repayments"]:
            st.caption(f"Repay {money(r['amount'])} on {r['date']} ({r['lever']})")
    else:
        st.error(p["note"])
with right:
    st.subheader("Cost of waiting")
    pts = get("/api/cost-of-waiting", scenario=scenario)
    bar = go.Figure(go.Bar(x=[pt["decision_date"][5:] for pt in pts],
                           y=[pt["total_cost"] or 0 for pt in pts],
                           text=[f"${pt['total_cost']:,.2f}" if pt["feasible"] else "No safe plan" for pt in pts],
                           textposition="outside"))
    bar.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Decide on", yaxis_title="Cost ($)")
    st.plotly_chart(bar, width="stretch")

# ---------- investigation ----------
st.subheader("AI investigation")
inv = next((a["investigation"] for a in get("/api/alerts") if a.get("investigation")), None)
if st.button("Investigate now"):
    with st.spinner("Agent is calling tools…"):
        inv = post("/api/investigate", {"scenario": scenario})
if inv:
    badge = "✅ every number verified against the engine" if inv["verified"] else f"⚠️ unverified: {inv['unverified_amounts']}"
    st.caption(f"{badge} · mode: {inv['mode']}")
    st.markdown(inv["memo"].replace("\n", "  \n"))
    with st.expander(f"Tool trace ({len(inv['trace'])} calls)"):
        for t in inv["trace"]:
            st.write(f"**{t['tool']}** · {t['ms']} ms · {t['output_summary']}")

# ---------- approval queue ----------
st.subheader("Approval queue")
acts = get("/api/actions")
if not acts:
    st.caption("No drafted actions yet.")
for a in acts:
    with st.container(border=True):
        st.write(f"**{a['id']} · {a['subject']}** → {a['recipient']} · status: `{a['status']}`")
        st.caption(a["body"])
        if a["status"] == "pending":
            b1, b2, _ = st.columns([1, 1, 6])
            if b1.button("Approve", key=f"ap-{a['id']}"):
                post(f"/api/actions/{a['id']}/approve"); st.rerun()
            if b2.button("Reject", key=f"rj-{a['id']}"):
                post(f"/api/actions/{a['id']}/reject"); st.rerun()
