"""ForeCash dashboard (Streamlit), design 05 + dropdown menu. Owner: Irvin.
Talks only to the FastAPI backend. Every dollar figure comes from the engine;
this file only formats numbers, it never calculates them.

Run (from frontend/, venv active):  streamlit run app.py
"""
import os
import time
from datetime import date

import plotly.graph_objects as go
import requests
import streamlit as st

API = os.getenv("API_BASE", "http://localhost:8000")
SCENARIO = "live"                      # the demo always runs on the live scenario
BUSINESS = "Paletería Arkansas"        # display name (overrides the backend's name)
OLD_NAMES = ["Paletería El Sol (demo)", "Paletería El Sol", "PaleterÃ\u00ada El Sol (demo)",
             "PaleterÃa El Sol (demo)", "PaleterÃ\u00ada El Sol", "PaleterÃa El Sol"]
PAYROLL_DATE = "2026-10-16"            # lowest point gets "(payroll day)" when it lands here
EVENT_LINE = "Ridgeline’s $4,000 payment is 6 days late."   # TODO: take the amount from the engine
PROVIDERS = {"akamai": "Akamai", "bedrock": "AWS Bedrock", "openai": "OpenAI"}
MEMO_LEFT = ("problem", "cause", "what happened", "why")   # memo sections kept on the left
CHART_HEIGHT = 400                     # both top charts use this, so their bottoms line up

# Dataset preview (front end only: saved in this browser session, does not change the forecast)
PREVIEW_NOTE = "Preview only: saved for this session. It doesn’t change the forecast yet."
SAMPLE_EXPENSES = [
    {"name": "Display freezer upgrade", "cost": 2500.00, "date": date(2026, 10, 15)},
    {"name": "Biweekly payroll", "cost": 8400.00, "date": date(2026, 10, 16)},
    {"name": "Dairy supply order", "cost": 2100.00, "date": date(2026, 10, 16)},
    {"name": "Sales tax", "cost": 900.00, "date": date(2026, 10, 16)},
]

# ---------- design 05 colors ----------
TEAL, LIME, INK, MUTED = "#0B5D57", "#C8EF5A", "#10201E", "#3D5753"
RED, AMBER, GREEN, BG, LINE = "#A3231A", "#C27C00", "#0B5D57", "#F2F6F5", "#98ADA9"
FONT = "Manrope, sans-serif"

st.set_page_config(page_title="ForeCash", page_icon="🍦", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap');
.stApp, .stApp button, .stApp input, .stApp p, .stApp li {{ font-family: 'Manrope', sans-serif; }}
.stApp {{ background: {BG}; color: {INK}; }}

/* hide Streamlit's black header bar, toolbar, sidebar and footer */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stSidebar"], [data-testid="collapsedControl"],
#MainMenu, footer {{ display: none !important; }}

/* hide the link icons next to headings */
[data-testid="stHeaderActionElements"], .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a {{
  display: none !important; }}

/* no white fade while Streamlit refreshes */
.stale-element, [data-stale="true"], [data-stale="true"] * {{
  opacity: 1 !important; transition: none !important; filter: none !important; }}

/* use the full screen: thin edges only */
.block-container, [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"] {{
  padding: 0.75rem 0.75rem 1rem !important; max-width: 100% !important; }}
section[data-testid="stMain"] {{ padding: 0 !important; }}
h1, h2, h3 {{ font-family: 'Manrope', sans-serif !important; font-weight: 800 !important; color: {INK}; }}

/* top bar */
.st-key-topbar {{ background: {TEAL}; border-radius: 6px; padding: 8px 16px;
  position: relative; overflow: visible !important; z-index: 1000; }}
.st-key-topbar p {{ color: #fff; font-weight: 800; font-size: 18px; margin: 0; }}
.st-key-topbar button[kind="primary"], .st-key-topbar [data-testid="stBaseButton-primary"] {{
  background: {LIME}; color: {INK}; border: 0; font-weight: 600; }}
.st-key-topbar button[kind="secondary"], .st-key-topbar [data-testid="stBaseButton-secondary"] {{
  background: transparent; color: #fff; border: 1px solid #7FB3AD; }}
.st-key-menubtn button {{ font-size: 20px; padding: 0 12px; min-height: 44px; }}
.st-key-topbar button {{ min-height: 44px; }}
.st-key-topbar button p {{ font-size: 16px !important; font-weight: 600; }}
.st-key-topbar button, .st-key-topbar button * {{ white-space: nowrap !important; overflow: visible !important; text-overflow: clip !important; }}
.st-key-topbar [data-testid="stBaseButton-primary"] p, .st-key-topbar button[kind="primary"] p {{ color: {INK} !important; }}
/* remove Streamlit's hidden spacing under text in the top bar, so the name centers with the buttons */
.st-key-topbar [data-testid="stMarkdownContainer"], .st-key-topbar [data-testid="stMarkdown"],
.st-key-topbar .stMarkdown {{ margin: 0 !important; padding: 0 !important; }}

/* brand name in the top bar (change "top" a pixel or two to nudge it up/down) */
.cp-brand {{ font-family: 'Bricolage Grotesque', 'Manrope', sans-serif; font-size: 30px; font-weight: 800;
  color: #fff; letter-spacing: -0.02em; white-space: nowrap;
  height: 44px; line-height: 44px; position: relative; top: -2px; }}

/* dropdown menu: hangs under the top bar, floats over the page, scrolls with it */
.st-key-menu {{ position: absolute; top: calc(100% + 8px); left: 0; width: 290px; z-index: 1001;
  background: #fff; border-radius: 8px; padding: 16px 12px;
  box-shadow: 0 12px 32px rgba(16, 32, 30, 0.25); }}
.st-key-menu p {{ font-weight: 700; color: {INK} !important; font-size: 15px !important; margin: 0; }}
.st-key-menu button, .st-key-menu [data-testid="stBaseButton-secondary"] {{
  justify-content: flex-start; background: #fff !important; color: {INK} !important;
  border: 1px solid #D5E2DF !important; }}
.st-key-menu button:hover {{ border-color: {TEAL} !important; color: {TEAL} !important; }}
.st-key-sub-new, .st-key-sub-view {{ margin-left: 10px; padding-left: 10px; border-left: 2px solid #D5E2DF; }}
.st-key-sub-new p, .st-key-sub-view p {{ font-weight: 600; font-size: 14px !important; }}

/* pencil + trash icons in the expense list: plain, shaded on hover */
[class*="st-key-pen-"] button, [class*="st-key-bin-"] button {{
  background: transparent !important; border: 0 !important; border-radius: 8px !important;
  min-height: 40px; padding: 4px 10px !important; color: {MUTED} !important; }}
[class*="st-key-pen-"] button:hover {{ background: #DDF2EC !important; color: {TEAL} !important; }}
[class*="st-key-bin-"] button:hover {{ background: #FCE4E2 !important; color: {RED} !important; }}
[class*="st-key-pen-"] button *, [class*="st-key-bin-"] button * {{ color: inherit !important; font-size: 22px !important; }}

/* red "Yes, delete" button in the warning */
[class*="st-key-yesdel"] button {{ color: #fff !important; background: {RED} !important; border: 0 !important; }}
[class*="st-key-yesdel"] button p {{ color: #fff !important; }}

/* "Try a fix" dropdown button looks like an input box */
.st-key-fixbox button, .st-key-fixbox [data-testid="stPopover"] > div > button, .st-key-fixbox [data-testid="stPopoverButton"] {{
  background: #fff !important; border: 1px solid {LINE} !important;
  color: {INK} !important; justify-content: space-between; min-height: 44px; }}

/* memo cards */
.cp-memo-title {{ font-weight: 800; font-size: 16px; margin-bottom: 4px; color: {INK}; }}

/* page pieces */
.cp-alert {{ border-radius: 6px; padding: 18px 22px; margin: 10px 0 14px; }}
.cp-alert .big {{ font-size: 21px; font-weight: 800; }}
.cp-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); background: #fff;
  border-radius: 6px; box-shadow: 0 1px 0 #D5E2DF; margin-bottom: 14px; }}
.cp-kpis > div {{ padding: 16px 22px; border-right: 1px solid #E3ECEA; }}
.cp-kpis > div:last-child {{ border-right: 0; }}
.cp-label {{ font-size: 13px; color: {MUTED}; }}
.cp-value {{ font-size: 30px; font-weight: 800; }}
.cp-note {{ font-size: 12px; color: {MUTED}; }}
.cp-callout {{ background: #FFE58F; border-radius: 6px; padding: 16px; font-size: 17px; line-height: 1.45; }}
.cp-pill {{ display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 13px; margin: 0 6px 8px 0; }}
.cp-footer {{ background: {TEAL}; color: #E6F2F0; text-align: center; font-size: 13px; padding: 14px; border-radius: 6px; margin-top: 18px; }}
.cp-colhead {{ font-size: 12px; color: {MUTED}; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)


# ---------- helpers: talk to the backend ----------
def get(path, **params):
    r = requests.get(f"{API}{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def post(path, body=None):
    r = requests.post(f"{API}{path}", json=body or {}, timeout=90)
    r.raise_for_status()
    return r.json()


# Cached versions for the slow, read-only calls (forecast, optimizer, cost of waiting).
# `ver` changes after Simulate, Reset, or any alert change, so results are never stale.
@st.cache_data(ttl=600, show_spinner=False)
def cget(path, ver, **params):
    return get(path, **params)


@st.cache_data(ttl=600, show_spinner=False)
def cpost(path, ver, body):
    return post(path, body)


# ---------- helpers: format numbers, dates and text ----------
def money(x):        # whole dollars: -2200 -> "-$2,200"
    return "—" if x is None else (f"-${-x:,.0f}" if x < 0 else f"${x:,.0f}")


def cents(x):        # two decimals: 9.21 -> "$9.21"
    return "—" if x is None else f"${x:,.2f}"


def signed(x):       # 500 -> "+$500"
    return ("+" if x and x > 0 else "") + money(x)


def as_date(s):
    return date.fromisoformat(s[:10])


def day_short(s):    # "Mon 12"  (no %-d: it breaks on Windows)
    d = as_date(s)
    return f"{d:%a} {d.day}"


def day_long(s):     # "Fri Oct 16"
    d = as_date(s)
    return f"{d:%a %b} {d.day}"


def full_date(d):    # date object -> "Fri Oct 16, 2026"
    return f"{d:%a %b} {d.day}, {d.year}"


def payroll_tag(s):
    return " (payroll day)" if s[:10] == PAYROLL_DATE else ""


def clean(s):        # repair "PaleterÃa"-style garbled text and swap in the display name
    s = str(s)
    try:
        s = s.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    for old in OLD_NAMES:
        s = s.replace(old, BUSINESS)
    s = s.replace("Card settlement", "Revenue")
    return s


def md(s):           # clean text + escape $, so "$9 ... $125" isn't read as a math formula
    return clean(s).replace("$", "\\$")


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def chart(fig):      # theme=None keeps our colors instead of Streamlit's
    st.plotly_chart(fig, width="stretch", theme=None)


def split_memo(text):
    """Split the AI memo into (title, body) pairs at lines like '## Problem' or '**Cause**'."""
    sections, title, buf = [], None, []
    for line in clean(text).splitlines():
        t = line.strip()
        is_heading = t.startswith("#") or (t.startswith("**") and t.endswith("**") and len(t) > 4)
        if is_heading:
            if title or "".join(buf).strip():
                sections.append((title, "\n".join(buf).strip()))
            title, buf = t.strip("#* ").rstrip(":"), []
        else:
            buf.append(line)
    if title or "".join(buf).strip():
        sections.append((title, "\n".join(buf).strip()))
    return sections


def memo_card(title, body):
    with st.container(border=True):
        if title:
            html(f"<div class='cp-memo-title'>{title}</div>")
        if body:
            st.markdown(md(body).replace("\n", "  \n"))


# ---------- callbacks (run before the refresh, so one click = one change) ----------
def toggle_menu():
    st.session_state.menu_open = not st.session_state.menu_open
    st.session_state.submenu = None


def toggle_submenu(name):
    st.session_state.submenu = None if st.session_state.submenu == name else name


def open_dialog(name):
    """Close the menu and open a pop-up window (needs a full refresh, so it ends with st.rerun)."""
    st.session_state.dialog = name
    st.session_state.menu_open = False
    st.session_state.submenu = None
    st.rerun()


def apply_fixes(ids):
    st.session_state.applied_fixes = [lid for lid in ids if st.session_state.get(f"lv-{lid}")]


def clear_fixes():
    for k in list(st.session_state.keys()):
        if str(k).startswith("lv-"):
            st.session_state[k] = False
    st.session_state.applied_fixes = []


def forget(prefix):  # wipe a ticket's typed values so it opens fresh next time
    for k in list(st.session_state.keys()):
        if str(k).startswith(prefix + "-"):
            del st.session_state[k]


try:
    health = get("/api/health")
except Exception as exc:
    st.error(f"Backend not reachable at {API}: {exc}")
    st.stop()

for key, default in [("menu_open", False), ("submenu", None), ("data_ver", 0),
                     ("applied_fixes", []), ("expenses", [dict(e) for e in SAMPLE_EXPENSES])]:
    if key not in st.session_state:
        st.session_state[key] = default


# ---------- expense ticket + list (pop-up windows) ----------
def expense_fields(prefix, existing=None):
    e = existing or {}
    name = st.text_input("Name", value=e.get("name", ""), key=f"{prefix}-name",
                         placeholder="Who you’re paying, e.g. Dairy supplier")
    cost = st.number_input("Cost ($)", min_value=0.0, step=10.0, format="%.2f",
                           value=float(e.get("cost", 0.0)), key=f"{prefix}-cost")
    when = st.date_input("Date", value=e.get("date", date.today()), format="MM/DD/YYYY",
                         key=f"{prefix}-date")
    if PREVIEW_NOTE:
        st.caption(PREVIEW_NOTE)
    return name.strip(), cost, when


@st.dialog("New expense")
def new_expense_dialog():
    name, cost, when = expense_fields("new")
    left, _, right = st.columns([1, 1.2, 1])
    cancel = left.button("Cancel", key="new-cancel", width="stretch")
    save = right.button("Save changes", key="new-save", type="primary", width="stretch")
    if cancel:
        forget("new")
        st.rerun()
    if save:
        if not name or cost <= 0:
            st.error("Add a name and a cost above $0.")
        else:
            st.session_state.expenses.append({"name": name, "cost": cost, "date": when})
            forget("new")
            st.session_state.toast_msg = "Expense saved."
            st.rerun()


@st.dialog("Edit expense")
def edit_expense_dialog(idx):
    exps = st.session_state.expenses
    if idx is None or idx >= len(exps):
        st.caption("That expense no longer exists.")
        return
    prefix = f"edit{idx}"
    name, cost, when = expense_fields(prefix, exps[idx])
    left, _, right = st.columns([1, 1.2, 1])
    cancel = left.button("Cancel", key=f"{prefix}-cancel", width="stretch")
    save = right.button("Save changes", key=f"{prefix}-save", type="primary", width="stretch")
    if cancel:
        forget(prefix)
        st.session_state.dialog = "view_expenses"     # back to the list
        st.rerun()
    if save:
        if not name or cost <= 0:
            st.error("Add a name and a cost above $0.")
        else:
            exps[idx] = {"name": name, "cost": cost, "date": when}
            forget(prefix)
            st.session_state.toast_msg = "Changes saved."
            st.session_state.dialog = "view_expenses"
            st.rerun()


@st.dialog("Delete expense?")
def delete_expense_dialog(idx):
    exps = st.session_state.expenses
    if idx is None or idx >= len(exps):
        st.caption("That expense no longer exists.")
        return
    e = exps[idx]
    st.markdown(f"Are you sure you want to delete **{md(e['name'])}** "
                f"({md(cents(e['cost']))}, {full_date(e['date'])})?")
    st.caption("This removes the expense from the list.")
    left, _, right = st.columns([1, 1.2, 1])
    if left.button("Cancel", key="del-cancel", width="stretch"):
        st.session_state.dialog = "view_expenses"     # back to the list
        st.rerun()
    if right.button("Yes, delete", key="yesdel-confirm", width="stretch"):
        exps.pop(idx)
        st.session_state.toast_msg = "Expense deleted."
        st.session_state.dialog = "view_expenses"
        st.rerun()


@st.dialog("Existing expenses", width="large")
def view_expenses_dialog():
    exps = st.session_state.expenses
    cols = [3, 1.5, 2, 0.45, 0.45]
    if not exps:
        st.caption("No expenses yet. Add one from ☰ → New → Expense.")
    else:
        h1, h2, h3, _, _ = st.columns(cols)
        h1.markdown("<div class='cp-colhead'>Name</div>", unsafe_allow_html=True)
        h2.markdown("<div class='cp-colhead'>Cost</div>", unsafe_allow_html=True)
        h3.markdown("<div class='cp-colhead'>Date</div>", unsafe_allow_html=True)
        for i, e in enumerate(exps):
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns(cols, vertical_alignment="center")
                c1.markdown(f"**{md(e['name'])}**")
                c2.markdown(md(cents(e["cost"])))
                c3.markdown(full_date(e["date"]))
                if c4.button(":material/edit:", key=f"pen-{i}", type="tertiary", help="Edit"):
                    st.session_state.edit_idx = i
                    st.session_state.dialog = "edit_expense"
                    st.rerun()
                if c5.button(":material/delete:", key=f"bin-{i}", type="tertiary", help="Delete"):
                    st.session_state.del_idx = i
                    st.session_state.dialog = "delete_expense"
                    st.rerun()
    if PREVIEW_NOTE:
        st.caption(PREVIEW_NOTE)
    _, right = st.columns([3, 1])
    if right.button("Done", type="primary", key="view-done", width="stretch"):
        st.rerun()


# ---------- DevRev pop-ups: record a customer's late-payment promise, see what DevRev tracks ----------
CHANNELS = ["in person", "phone", "email", "text message", "other"]


def _api_error(e):
    resp = getattr(e, "response", None)
    try:
        return resp.json().get("detail", str(e)) if resp is not None else str(e)
    except Exception:
        return str(e)


@st.dialog("Delayed Receivable", width="large")
def new_promise_dialog():
    """The owner heard it in person or on the phone: preview the impact, approve, and the forecast,
    alert and DevRev follow-up update together. All math happens in the backend."""
    incoming = [t for t in get("/api/transactions") if t["direction"] == "in"]
    if not incoming:
        st.caption("No incoming payments in this week's forecast.")
        return
    labels = {f"{t['id']} · {clean(t['description'])} · {money(t['amount'])} · expected {day_long(t['date'])}": t
              for t in incoming}
    t = labels[st.selectbox("Which payment?", list(labels), key="pr-txn")]
    customer = st.text_input("Customer", t["description"].split(" paleta")[0].split(",")[0], key=f"pr-cust-{t['id']}")
    cur = as_date(t["date"])
    new_date = st.date_input("New date they gave you", value=date.fromordinal(cur.toordinal() + 1),
                             min_value=date.fromordinal(cur.toordinal() + 1), format="MM/DD/YYYY", key="pr-date")
    c1, c2 = st.columns(2)
    said_by = c1.text_input("Who told you?", placeholder="e.g. Luis Pardo, accounts payable", key="pr-who")
    channel = c2.selectbox("How?", CHANNELS, key="pr-how")
    quote = st.text_area("What did they say? (optional, their words)", max_chars=300, key="pr-quote",
                         placeholder="We'll pay the full amount on the 21st.")
    body = {"txn": t["id"], "new_date": new_date.isoformat(), "said_by": said_by, "channel": channel,
            "quote": quote, "customer": customer}
    if st.button("Preview the impact", width="stretch", key="pr-preview"):
        try:
            st.session_state.pr_preview = (body, post("/api/devrev/payment-update/preview", body))
        except Exception as e:
            st.session_state.pop("pr_preview", None)
            st.error(_api_error(e))
    saved = st.session_state.get("pr_preview")
    if not saved or saved[0] != body:
        st.caption("Preview first. Nothing changes until you approve.")
        return
    p = saved[1]
    st.markdown(md(f"**{p['txn']}** moves from {day_long(p['old_date'])} to **{day_long(p['new_date'])}** "
                   f"({p['days_later']} days later)."))
    m1, m2 = st.columns(2)
    m1.metric("Lowest balance now", money(p["before"]["lowest"]), day_long(p["before"]["lowest_date"]), delta_color="off")
    m2.metric("Lowest balance after", money(p["after"]["lowest"]), day_long(p["after"]["lowest_date"]), delta_color="off")
    if p["after"]["lowest"] < p["reserve"]:
        st.warning(md(f"This drops cash below your {money(p['reserve'])} reserve. "
                      "ForeCash will alert you and find the cheapest fix."))
    if p["already_recorded"]:
        st.info(f"DevRev already tracks this promise as {p['already_recorded']}. "
                "Approving updates the forecast without a duplicate follow-up.")
    else:
        st.caption(md(f"Follow-up to create on the DevRev board: **{p['follow_up']['title']}**"))
    left, _, right = st.columns([1, 1.2, 1])
    if left.button("Cancel", width="stretch", key="pr-cancel"):
        st.session_state.pop("pr_preview", None)
        st.rerun()
    if right.button("Approve and update", type="primary", width="stretch", key="pr-approve"):
        try:
            r = post("/api/devrev/payment-update/apply", body)
            st.session_state.pop("pr_preview", None)
            st.session_state.data_ver += 1
            st.session_state.toast_msg = r["note"]
            st.rerun()
        except Exception as e:
            st.error(_api_error(e))


@st.dialog("Existing Receivables", width="large")
def view_promises_dialog():
    try:
        items = get("/api/devrev/follow-ups")["follow_ups"]
    except Exception as e:
        st.error(_api_error(e))
        return
    if not items:
        st.caption("Nothing tracked yet. Record one from ☰ → New → Delayed Receivable.")
    for f_ in items:
        with st.container(border=True):
            badge = "🟢 open" if f_["status"] == "open" else "✅ done"
            st.markdown(md(f"**{f_['id']} · {f_['title']}** · {f_['account']} · {badge}"))
            st.caption(md(f"Owner: {f_['owner']} · Due: {f_['due_date']}"))
            for s_ in f_["sources"]:
                st.caption(md(f"📎 {s_['ref']}" + (f" lines {s_['lines']}" if s_["lines"] else "")
                              + (f" — “{s_['quote']}”" if s_["quote"] else "")))
    st.caption("Full details, Mark done and Reopen: the “Enterprise follow-ups (DevRev)” view.")
    _, right = st.columns([3, 1])
    if right.button("Done", type="primary", key="pr-view-done", width="stretch"):
        st.rerun()


# ---------- top bar: menu, name, demo controls (a fragment: the menu only refreshes this bar) ----------
@st.fragment
def top_bar():
    with st.container(key="topbar"):
        c0, c1, c2, c3 = st.columns([0.5, 4.5, 3.8, 1.4], vertical_alignment="center")
        c0.button("☰", key="menubtn", help="Menu", on_click=toggle_menu)
        c1.markdown("<div class='cp-brand'>ForeCash</div>", unsafe_allow_html=True)
        moved = any(t["id"] == "T08" and t["date"][:10] != "2026-10-15" for t in get("/api/transactions"))
        if c2.button("Simulate: Ridgeline pays 6 days late", type="primary", width="stretch", disabled=moved,
                     help="Already applied. Press Reset demo to run it again." if moved else None):
            post("/api/events", {"type": "payment_delayed", "txn": "T08", "days": 6})
            st.session_state.data_ver += 1
            st.session_state.menu_open = False
            st.session_state.ridgeline_text = True     # show the customer's text message
            st.rerun()                               # numbers changed: refresh the whole page
        if c3.button("Reset demo", width="stretch"):
            post("/api/demo/reset")
            st.session_state.data_ver += 1
            st.session_state.menu_open = False
            clear_fixes()
            st.rerun()
        if st.session_state.menu_open:
            sub = st.session_state.submenu
            with st.container(key="menu"):
                # New
                st.button(("▾ " if sub == "new" else "▸ ") + "New", key="m-new",
                          width="stretch", on_click=toggle_submenu, args=("new",))
                if sub == "new":
                    with st.container(key="sub-new"):
                        if st.button("Expense", key="m-new-exp", width="stretch"):
                            open_dialog("new_expense")
                        if st.button("Delayed Receivable", key="m-new-promise", width="stretch"):
                            open_dialog("new_promise")
                # View
                st.button(("▾ " if sub == "view" else "▸ ") + "View", key="m-view",
                          width="stretch", on_click=toggle_submenu, args=("view",))
                if sub == "view":
                    with st.container(key="sub-view"):
                        if st.button("Existing expense", key="m-view-exp", width="stretch"):
                            open_dialog("view_expenses")
                        if st.button("Existing Receivables", key="m-view-promise", width="stretch"):
                            open_dialog("view_promises")


top_bar()

# ---------- "Try a fix" pop-up: tick options, Apply closes the window ----------
@st.dialog("Try a fix", width="large")
def fix_dialog():
    levers = get("/api/levers")
    st.caption("Tick the options to test, then press Apply. Nothing is paid or sent; this only tests the plan.")
    chosen = [lv["id"] for lv in levers
              if st.checkbox(clean(lv["name"]), value=lv["id"] in st.session_state.applied_fixes, key=f"fx-{lv['id']}")]
    b1, b2 = st.columns(2)
    if b1.button("Apply changes", type="primary", width="stretch", key="fx-apply"):
        st.session_state.applied_fixes = chosen
        st.session_state.data_ver += 1
        st.rerun()
    if b2.button("Clear", width="stretch", key="fx-clear"):
        st.session_state.applied_fixes = []
        st.session_state.data_ver += 1
        st.rerun()


# open whichever pop-up the menu asked for (pop = it only opens once)
dlg = st.session_state.pop("dialog", None)
if dlg == "new_expense":
    new_expense_dialog()
elif dlg == "view_expenses":
    view_expenses_dialog()
elif dlg == "edit_expense":
    edit_expense_dialog(st.session_state.get("edit_idx"))
elif dlg == "fix":
    fix_dialog()
elif dlg == "delete_expense":
    delete_expense_dialog(st.session_state.get("del_idx"))
elif dlg == "new_promise":
    new_promise_dialog()
elif dlg == "view_promises":
    view_promises_dialog()

msg = st.session_state.pop("toast_msg", None)
if msg:
    st.toast(msg)

# ---------- the late-payment "text message" from Ridgeline (slides in top right, fades out) ----------
RIDGELINE_TEXT = """
<style>
@keyframes cp-sms { 0% {transform: translateX(120%); opacity: 0}
                    6% {transform: translateX(0); opacity: 1}
                    88% {transform: translateX(0); opacity: 1}
                    100% {transform: translateX(120%); opacity: 0; visibility: hidden} }
.cp-sms { position: fixed; top: 70px; right: 18px; z-index: 999999; width: 340px; max-width: calc(100vw - 36px);
          background: rgba(250,250,252,.97); border-radius: 18px; padding: 12px 14px 14px;
          box-shadow: 0 12px 32px rgba(0,0,0,.22); font-family: -apple-system, "SF Pro Text", Manrope, sans-serif;
          animation: cp-sms 12s ease-in-out forwards; pointer-events: none; }
.cp-sms-top { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #6B7280; margin-bottom: 8px; }
.cp-sms-app { width: 20px; height: 20px; border-radius: 5px; background: #34C759; color: #fff;
              display: flex; align-items: center; justify-content: center; font-size: 12px; }
.cp-sms-from { font-weight: 700; font-size: 14px; color: #111; margin: 0 0 6px; }
.cp-sms-bubble { background: #E9E9EB; color: #111; border-radius: 18px 18px 18px 4px; padding: 9px 12px;
                 font-size: 14px; line-height: 1.35; }
</style>
<div class="cp-sms">
  <div class="cp-sms-top"><span class="cp-sms-app">💬</span><span>MESSAGES</span><span style="margin-left:auto">now</span></div>
  <div class="cp-sms-from">Luis Pardo · Ridgeline Corp</div>
  <div class="cp-sms-bubble">Hi Julian, I’m really sorry. Our payment run moved because of the quarter close,
  so invoice INV-2041 for &#36;4,000 will go out on Oct 21 instead of Oct 15. That’s 6 days late.
  Apologies for the trouble, and thank you for understanding. – Luis</div>
</div>
"""
if st.session_state.pop("ridgeline_text", False):
    st.session_state.ridgeline_until = time.time() + 12
sms_slot = st.empty()        # always on the page (even when empty), so nothing below it shifts
if time.time() < st.session_state.get("ridgeline_until", 0):
    sms_slot.markdown(RIDGELINE_TEXT, unsafe_allow_html=True)

# alerts are fetched fresh every time; they decide when cached data must refresh
alerts = get("/api/alerts")
alert = alerts[0] if alerts else None
ver = f"{st.session_state.data_ver}-{alert['id'] if alert else 'none'}-{alert['status'] if alert else ''}"

ov = cget("/api/overview", ver, scenario=SCENARIO)
s, f = ov["settings"], ov["forecast"]
days = f["days"]
reserve = s["min_reserve"]
trouble = f["shortfall_vs_reserve"] > 0     # red week: show "Try a fix" and the AI analysis

# ---------- view switch: ForeCash vs. DevRev follow-up board ----------
view = st.radio("View", ["ForeCash", "Enterprise follow-ups (DevRev)"], horizontal=True, label_visibility="collapsed")

if view != "ForeCash":
    st.title("Enterprise follow-ups (DevRev)")
    st.caption("Created by DevRev Computer through our MCP connector, after the user approved each preview. "
               "Evidence: synthetic call transcripts written for this demo (DevRev confirmed teams may load their own data). "
               "Open follow-ups about incoming payments also appear on the ForeCash page.")
    if st.button("Refresh"):
        st.rerun()
    acct = st.text_input("Filter by account", "")
    data = get("/api/devrev/follow-ups", account=acct)
    items = data["follow_ups"]
    m = st.columns(3)
    m[0].metric("Follow-ups", data["total"])
    m[1].metric("Open", sum(1 for f in items if f["status"] == "open"))
    m[2].metric("Duplicates blocked", sum(f["repeat_attempts"] for f in items))
    if not items:
        st.info("No follow-ups yet. In DevRev Computer, ask the commitment-to-action skill to review an account.")
    for f in items:
        with st.container(border=True):
            badge = "🟢 open" if f["status"] == "open" else "✅ done"
            st.write(f"**{f['id']} · " + f['title'].replace('$', r'\$') + f"** · {f['account']} · {badge}")
            st.caption(f"Owner: {f['owner']} · Due: {f['due_date']} · Requested via DevRev Computer "
                       f"· created {f['created_at'][:16].replace('T', ' ')} UTC"
                       + (f" · repeat runs blocked: {f['repeat_attempts']}" if f["repeat_attempts"] else ""))
            if f["details"]:
                st.write(f["details"].replace("$", r"\$"))
            for s_ in f["sources"]:
                loc = " · ".join(x for x in [s_["lines"] and f"lines {s_['lines']}",
                                             s_["sha256"] and f"sha256 {s_['sha256'][:12]}…"] if x)
                st.caption(f"📎 Source: `{s_['ref']}`" + (f" ({loc})" if loc else "")
                           + (f" — “{s_['quote']}”" if s_["quote"] else ""))
            if f["status"] == "open" and st.button("Mark done", key=f"done-{f['id']}"):
                post(f"/api/devrev/follow-ups/{f['id']}/status?status=done")
                st.rerun()
            if f["status"] == "done" and st.button("Reopen", key=f"reopen-{f['id']}"):
                post(f"/api/devrev/follow-ups/{f['id']}/status?status=open")
                st.rerun()
    st.stop()

# ---------- header ----------
h1, h2 = st.columns([3, 2], vertical_alignment="bottom")
h1.markdown(f"<h1 style='margin:0;font-size:38px'>{BUSINESS} · ForeCash</h1>"
            f"<div style='color:{MUTED}'>Find the cheapest way through a cash crunch, and what it costs to wait.</div>",
            unsafe_allow_html=True)
h2.markdown(f"<div style='text-align:right;font-weight:600'>Cash forecast {day_long(days[0]['date'])} – "
            f"{day_long(days[-1]['date'])} · Reserve: {money(reserve)}</div>", unsafe_allow_html=True)

# ---------- status banner ----------
if alert and alert["status"] == "investigating":
    html("<div class='cp-alert' style='background:#FFF4CC;border:1px solid #E0C060'>"
         "<div class='big'>ForeCash is investigating a change in your cash…</div></div>")
    time.sleep(2)
    st.rerun()
elif f["shortfall_vs_reserve"] == 0:
    html(f"<div class='cp-alert' style='background:#DDF2EC;border:1px solid #8CC9B8'>"
         f"<div class='big' style='color:{GREEN}'>You’re safe this week. Lowest balance: {money(f['min_balance'])} "
         f"on {day_long(f['min_date'])}{payroll_tag(f['min_date'])}.</div></div>")
else:
    proof = ("<div style='font-size:14px;margin-top:4px'>ForeCash spotted this on its own and investigated. "
             "Nobody had to ask.</div>") if alert else ""
    html(f"<div class='cp-alert' style='background:#FCE4E2;border:1px solid #E5A19A'>"
         f"<div class='big' style='color:#7E1A12'>Cash runs short: {money(f['min_balance'])} on "
         f"{day_long(f['min_date'])}{payroll_tag(f['min_date'])}. {EVENT_LINE if alert else ''}</div>{proof}</div>")

# ---------- four numbers in a row ----------
bad = f["shortfall_vs_reserve"] > 0
low_color = RED if f["min_balance"] < reserve else INK
html(f"""<div class='cp-kpis'>
<div><div class='cp-label'>Cash today</div><div class='cp-value' style='color:{RED if s['opening_cash'] < 0 else INK}'>{money(s['opening_cash'])}</div></div>
<div><div class='cp-label'>Lowest balance</div>
 <div class='cp-value' style='color:{low_color}'>{money(f['min_balance'])}
 <span style='font-size:15px;font-weight:600'>{day_long(f['min_date'])}</span></div>
 <div class='cp-note'>We judge safety by your worst day, not your last day.</div></div>
<div><div class='cp-label'>Ending cash</div><div class='cp-value' style='color:{RED if f['ending_cash'] < 0 else INK}'>{money(f['ending_cash'])}</div></div>
<div><div class='cp-label'>Below reserve by</div>
 <div class='cp-value' style='color:{RED if bad else GREEN}'>{money(f['shortfall_vs_reserve'])}</div></div>
</div>""")


# ---------- chart + try a fix + plan + waiting (a fragment: picking an option only refreshes this part) ----------
@st.fragment
def forecast_section(ver, f, reserve):
    days = f["days"]
    bad = f["shortfall_vs_reserve"] > 0

    st.markdown("### Daily cash balance")
    chart_box = st.container()

    levers = cget("/api/levers", ver)
    names = {lv["id"]: clean(lv["name"]) for lv in levers}
    costs = {lv["id"]: lv["cost_usd"] for lv in levers}

    # red week: three columns with "Try a fix"; green week: two boxed cards, no "Try a fix"
    if bad:
        c_fix, c_plan, c_wait = st.columns(3, gap="medium")
    else:
        c_fix = None
        c_plan, c_wait = st.columns(2, gap="medium")
    sim = None

    # ----- try a fix: tick options, then press "Apply changes" (only when there's a problem) -----
    if c_fix is not None:
        with c_fix:
            st.markdown("### Try a fix")
            picked = [lid for lid in st.session_state.applied_fixes if lid in names]
            label = (f"{len(picked)} option{'s' if len(picked) != 1 else ''} applied" if picked
                     else "Pick one or more options")
            with st.container(key="fixbox"):
                if st.button(label + "  ▾", width="stretch", key="fix-open"):
                    open_dialog("fix")
            if picked:
                st.caption("Testing: " + md(", ".join(names[lid] for lid in picked)))
            sim = cpost("/api/simulate", ver, {"scenario": SCENARIO, "lever_ids": sorted(picked)}) if picked else None
            if sim:
                if sim["shortfall_vs_reserve"] == 0:
                    html(f"<div class='cp-callout' style='background:#DDF2EC'><strong>This keeps you safe every day.</strong> "
                         f"Lowest balance {money(sim['min_balance'])} on {day_long(sim['min_date'])}.</div>")
                elif sim["ending_cash"] >= reserve:
                    # the "aha": ending looks fine, worst day doesn't
                    html(f"<div class='cp-callout'>Ending cash looks fine ({signed(sim['ending_cash'])}), but "
                         f"{as_date(sim['min_date']):%A} payroll still drops you to {money(sim['min_balance'])}, which is "
                         f"{money(sim['shortfall_vs_reserve'])} below your reserve. <strong>This fix isn’t enough.</strong></div>")
                else:
                    html(f"<div class='cp-callout' style='background:#FCE4E2'>Still short: lowest balance "
                         f"{money(sim['min_balance'])} on {day_long(sim['min_date'])}. <strong>This fix isn’t enough.</strong></div>")

    # ----- the two charts, same height so their tops and bottoms line up -----
    with chart_box:
        c_bal, c_flow = st.columns([3, 2], gap="medium")
        x = [day_short(d["date"]) for d in days]
        fig = go.Figure()
        fig.add_scatter(x=x, y=[d["closing"] for d in days], name="Current plan", mode="lines+markers",
                        line=dict(color=RED if bad else TEAL, width=3), marker=dict(size=7))
        if sim:
            fig.add_scatter(x=x, y=[d["closing"] for d in sim["days"]], name="With the options you picked",
                            mode="lines+markers", line=dict(color=AMBER, width=3, dash="dot"), marker=dict(size=7))
        fig.add_hline(y=reserve, line_dash="dash", line_color=TEAL, annotation_text=f"Reserve {money(reserve)}",
                      annotation_position="top left", annotation_font_color=TEAL)
        fig.add_hline(y=0, line_color=LINE)
        low_label = ("Payroll day · " if f["min_date"][:10] == PAYROLL_DATE else "Lowest · ") + money(f["min_balance"])
        fig.add_annotation(x=day_short(f["min_date"]), y=f["min_balance"], text=low_label, showarrow=True,
                           arrowhead=0, ay=-34, font=dict(color=RED if bad else INK, size=13), bgcolor="#fff")
        fig.update_layout(height=CHART_HEIGHT, margin=dict(l=20, r=30, t=20, b=20), plot_bgcolor="#fff",
                          paper_bgcolor="#fff", font=dict(family=FONT, size=13, color=INK),
                          hoverlabel=dict(font_family=FONT),
                          legend_orientation="h", legend_y=1.1,
                          yaxis=dict(tickprefix="$", tickformat=",", gridcolor="#EEF2F1", automargin=True),
                          xaxis=dict(gridcolor="#EEF2F1", automargin=True, tickfont=dict(size=13)))
        with c_bal:
            chart(fig)
        with c_flow:      # revenue vs. expenses, day by day (engine numbers, no math here)
            txns = cget("/api/transactions", ver, scenario=SCENARIO)
            by_day = {}
            for t in sorted(txns, key=lambda t: -t["amount"]):
                by_day.setdefault((t["date"][:10], t["direction"]), []).append(
                    f"{clean(t['description'])}: {money(t['amount'])}")
            dates = [d["date"][:10] for d in days]
            flow = go.Figure()
            for direction, label, key, color in (("in", "Revenue", "inflows", GREEN),
                                                 ("out", "Expenses", "outflows", RED)):
                tips = []
                for d in days:
                    items = by_day.get((d["date"][:10], direction), [])
                    tip = "<br>".join(items) if items else "nothing scheduled"
                    if len(items) > 1:          # the day's total comes from the engine, not added up here
                        tip += f"<br><b>Total: {money(d[key])}</b>"
                    tips.append(tip)
                flow.add_bar(x=x, y=[d[key] for d in days], name=label, marker_color=color, customdata=tips,
                             hovertemplate=f"<b>{label}, %{{x}}</b><br>%{{customdata}}<extra></extra>")
            flow.update_layout(barmode="group", height=CHART_HEIGHT, margin=dict(l=20, r=20, t=64, b=20),
                               title=dict(text="<b>Revenue vs. expenses</b>", x=0.02, y=0.97,
                                          font=dict(family=FONT, size=16, color=INK)),
                               plot_bgcolor="#fff", paper_bgcolor="#fff",
                               font=dict(family=FONT, size=13, color=INK), hoverlabel=dict(font_family=FONT),
                               legend=dict(orientation="h", x=0, y=1.07, font=dict(family=FONT, size=13),
                                           itemclick="toggleothers", itemdoubleclick="toggle"),
                               bargap=0.25,
                               yaxis=dict(tickprefix="$", tickformat=",", gridcolor="#EEF2F1", automargin=True),
                               xaxis=dict(automargin=True, tickfont=dict(size=13)))
            chart(flow)

    # ----- cheapest plan (boxed card on a green week) -----
    with c_plan:
        with st.container(border=not bad):
            p = cpost("/api/optimize", ver, {"scenario": SCENARIO})
            if p["feasible"] and not p["levers"]:
                st.markdown("### No action needed")
                st.success("Cash stays above the reserve every day.")
            elif p["feasible"]:
                st.markdown(f"### Cheapest plan that keeps you safe every day: {md(cents(p['total_cost']))}")
                repay = {r["lever"]: r for r in p["repayments"]}
                lines = []
                for lid in p["levers"]:
                    detail = cents(costs.get(lid))
                    if lid in repay:
                        detail += f" interest; repay {cents(repay[lid]['amount'])} on {day_long(repay[lid]['date'])}"
                    lines.append(f"<li>{names.get(lid, lid)} ({detail})</li>")
                html(f"<ol style='padding-left:20px;line-height:1.6;font-size:17px'>{''.join(lines)}</ol>"
                     f"<div class='cp-note'>ForeCash tested every combination of {len(levers)} options.</div>")
            else:
                st.markdown("### No safe plan")
                st.error(md(p["note"]))
            if p["levers"] or not p["feasible"]:
                with st.expander("How ForeCash priced every option"):
                    for lv in sorted(levers, key=lambda l: l["cost_usd"]):
                        tag = " · ✅ in the plan" if lv["id"] in p["levers"] else (" · last resort" if lv.get("last_resort") else "")
                        st.markdown(md(f"**{cents(lv['cost_usd'])}** · {lv['name']}{tag}"))
                        st.caption(md(lv["cost_basis"] + (f" · decide by {day_long(lv['deadline'])}" if lv.get("deadline") else "")))

    # ----- cost of waiting (boxed card on a green week) -----
    with c_wait:
        with st.container(border=not bad):
            st.markdown("### What waiting costs you")
            pts = cget("/api/cost-of-waiting", ver, scenario=SCENARIO)
            nothing_to_decide = all(pt["feasible"] and not pt["total_cost"] for pt in pts)
            if nothing_to_decide:
                st.success("Nothing to decide this week: you’re safe whichever day you look at it.")
            else:
                top = max([pt["total_cost"] for pt in pts if pt["feasible"]] or [1])
                colors, heights, texts, labels = [], [], [], []
                for i, pt in enumerate(pts):
                    labels.append(f"{as_date(pt['decision_date']):%a}")
                    if pt["feasible"]:
                        heights.append(pt["total_cost"])
                        texts.append(cents(pt["total_cost"]))
                        colors.append(GREEN if i == 0 else AMBER)
                    else:
                        heights.append(top)                     # full-height red bar, not a cost
                        texts.append("No safe plan:<br>payroll missed")
                        colors.append(RED)
                bar = go.Figure(go.Bar(x=labels, y=heights, text=texts, textposition="outside",
                                       marker_color=colors, cliponaxis=False, constraintext="none",
                                       textfont=dict(size=14, color=INK)))
                bar.update_layout(height=290, margin=dict(l=10, r=10, t=50, b=20), plot_bgcolor="#fff",
                                  paper_bgcolor="#fff", font=dict(family=FONT, size=14, color=INK),
                                  yaxis=dict(visible=False),
                                  xaxis=dict(automargin=True, tickfont=dict(size=14)))
                chart(bar)
                parts = []
                for i, pt in enumerate(pts):
                    when = "today" if i == 0 else f"{as_date(pt['decision_date']):%A}"
                    if pt["feasible"]:
                        parts.append(f"Decide {when}: {money(pt['total_cost'])}.")
                    else:
                        parts.append(f"Wait until {when}: you can’t make payroll.")
                st.markdown(f"**{md(' '.join(parts))}**")


forecast_section(ver, f, reserve)

# ---------- DevRev: what customers said about money you're expecting ----------
def devrev_commitments_panel():
    """Open DevRev follow-ups whose account appears in an incoming payment. Read-only."""
    import os
    try:
        items = get("/api/devrev/follow-ups", status="open")["follow_ups"]
        incoming = [t for t in get("/api/transactions") if t["direction"] == "in"]
    except Exception:
        return
    hits = [(t, f) for t in incoming for f in items
            if f["account"].lower() in t["description"].lower() and t["date"][:10] == f["due_date"][:10]]
    if not hits:
        return
    esc = lambda x: str(x).replace("$", r"\$")
    with st.container(border=True):
        st.markdown("**🔎 Why this payment moved: what the customer told you (from DevRev)**")
        for t, f in hits:
            st.markdown(f"**{t['id']}** {esc(t['description'])}  \n"
                        f"→ **{f['id']} · {esc(f['title'])}** · due {f['due_date']} · owner {f['owner']}")
            for s_ in f["sources"]:
                st.caption(f"📎 `{s_['ref']}`" + (f" lines {s_['lines']}" if s_["lines"] else "")
                           + (f" — “{esc(s_['quote'])}”" if s_["quote"] else ""))
        st.caption("From DevRev: found in call transcripts or recorded by you, and approved by you. Read-only here.")
        st.link_button("Open DevRev Computer", os.getenv("DEVREV_URL", "https://app.devrev.ai"))


devrev_commitments_panel()

# ---------- AI analyst (left, red week only) + approvals and plan details (right) ----------
right_sections = []
if trouble:
    c_ai, c_ok = st.columns(2, gap="medium")
    with c_ai:
        st.markdown("### What happened and why")
        inv = next((a["investigation"] for a in alerts if a.get("investigation")), None)
        if st.button("Investigate now"):
            with st.spinner("ForeCash is checking the numbers…"):
                try:
                    inv = post("/api/investigate", {"scenario": SCENARIO})
                except Exception:
                    st.warning("The analysis is taking longer than expected. Try again in a moment.")
        if inv:
            offline = health["model_provider"] == "stub" or inv.get("mode") in ("template", "stub", "fallback")
            if offline:
                html("<span class='cp-pill' style='background:#FFF4CC'>AI offline: using built-in analysis.</span>")
            else:
                check = ("<span class='cp-pill' style='background:#DDF2EC;color:#0B5D57;font-weight:600'>"
                         "✓ Every number checked against the engine</span>") if inv["verified"] else (
                         f"<span class='cp-pill' style='background:#FCE4E2'>⚠ Unverified: {inv['unverified_amounts']}</span>")
                tools = len({t["tool"] for t in inv["trace"]})
                where = PROVIDERS.get(health["model_provider"], health["model_provider"])
                html(f"{check}<span class='cp-pill' style='background:#EEF2F1'>Strands agent · AI on {where} · {tools} tools used</span>")
            sections = split_memo(inv["memo"])
            for title, body in sections:
                if not title or title.lower().startswith(MEMO_LEFT):
                    memo_card(title, body)
                else:
                    right_sections.append((title, body))
            with st.expander(f"How the Strands agent worked: tool trace ({len(inv['trace'])} calls)"):
                for t in inv["trace"]:
                    st.markdown(md(f"**{t['tool']}** · {t['ms']} ms · {t['output_summary']}"))
        else:
            st.caption("ForeCash writes its analysis here when it spots a problem.")
else:
    c_ok = st.container()     # green week: approvals use the full width

with c_ok:
    st.markdown("### Ready for your approval")
    acts = get("/api/actions") if bad else []    # drafts only matter while there's a cash problem
    if not acts:
        st.caption("Nothing to approve yet.")
    for a in acts:
        with st.container(border=True):
            st.markdown(f"**To {md(a['recipient'])}:** {md(a['subject'])}")
            st.caption(md(a["body"]))
            if a["status"] == "pending":
                b1, b2, _ = st.columns([1, 1, 4])
                if b1.button("Approve", key=f"ap-{a['id']}", type="primary"):
                    post(f"/api/actions/{a['id']}/approve")
                    st.rerun()
                if b2.button("Reject", key=f"rj-{a['id']}"):
                    post(f"/api/actions/{a['id']}/reject")
                    st.rerun()
            else:
                st.markdown(f"Status: `{a['status']}`")
    st.caption("Nothing is sent without your approval. Approving twice never sends twice.")
    for title, body in right_sections:     # the rest of the AI memo (cheapest plan, cost of waiting, ...)
        memo_card(title, body)

# ---------- footer ----------
html("<div class='cp-footer'>Demo data (synthetic) · Runs on Akamai Cloud · Agent built with Strands</div>")