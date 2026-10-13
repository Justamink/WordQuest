"""WordQuest home page: connection status + navigation.

Run with:  streamlit run app.py
"""
import streamlit as st

from db import query, friendly_error

st.set_page_config(page_title="WordQuest", page_icon="🧭")

st.title("🧭 WordQuest")
st.write(
    "Practice English with topic-based exercises, earn badges, and give "
    "teachers insight into where students need more practice."
)

# ---- Database connection card (Section 6.2 evidence) ----
st.subheader("Database Connection")
try:
    info = query("SELECT current_database() AS db, version() AS version;")[0]
    st.success(f"Connected to PostgreSQL database '{info['db']}'")
    st.caption(info["version"])
except Exception as e:  # noqa: BLE001
    st.error(friendly_error(e))
    st.stop()

# ---- Quick row counts ----
st.subheader("Table Row Counts")
TABLES = [
    "student", "course", "classsection", "topic", "practiceunit",
    "exercise", "answerchoice", "studentprogress", "badge", "student_badge",
]
counts = []
for t in TABLES:
    try:
        n = query(f"SELECT COUNT(*) AS n FROM {t};")[0]["n"]
        counts.append({"table": t, "rows": n})
    except Exception:  # table name may differ in your schema
        counts.append({"table": t, "rows": "n/a"})
st.dataframe(counts, hide_index=True, use_container_width=True)

# ---- Navigation guide ----
st.subheader("Screens")
st.markdown(
    """
| Screen | What you can do | Scenario |
|---|---|---|
| Practice | Answer a multiple-choice or free-response question | S1 |
| Add Exercise | Add a question and its answer options | S2 |
| Badges | Award a badge to a student and view earned badges | S3 |
| Grade Answers | Mark free-response answers correct or incorrect | (Update) |
| Manage Exercises | Search exercises and delete one | (Read / Delete) |

Use the sidebar to navigate.
"""
)