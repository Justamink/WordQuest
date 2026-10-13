"""Search exercises (Read/Search) and delete one (Delete)."""
import streamlit as st

from db import query, execute, friendly_error

st.set_page_config(page_title="Manage Exercises", page_icon="🗂️")
st.title("🗂️ Manage Exercises")

# ---------------- SQL ----------------
SEARCH_SQL = """
SELECT e.exercise_id, e.question_text, e.question_type, u.unit_name,
       (SELECT COUNT(*) FROM answerchoice a WHERE a.exercise_id = e.exercise_id) AS num_choices,
       (SELECT COUNT(*) FROM studentprogress sp WHERE sp.exercise_id = e.exercise_id) AS num_attempts
FROM exercise e
JOIN practiceunit u ON u.unit_id = e.unit_id
WHERE e.question_text ILIKE %s
ORDER BY e.exercise_id;
"""

DELETE_SQL = "DELETE FROM exercise WHERE exercise_id = %s;"

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

keyword = st.text_input("Search question text")

try:
    rows = query(SEARCH_SQL, (f"%{keyword}%",))
except Exception as e:  # noqa: BLE001
    st.error(friendly_error(e))
    st.stop()

st.dataframe(rows, hide_index=True, use_container_width=True)

st.subheader("Delete an exercise")
if rows:
    target = st.selectbox(
        "Exercise to delete",
        rows,
        format_func=lambda r: f"#{r['exercise_id']} - {r['question_text'][:60]}",
    )
    st.warning(
        f"This exercise has {target['num_choices']} answer option(s) and "
        f"{target['num_attempts']} student attempt(s)."
    )
    confirm = st.checkbox("Yes, I'm sure I want to delete this exercise")
    if st.button("Delete exercise", disabled=not confirm):
        try:
            execute(DELETE_SQL, (target["exercise_id"],))
            st.session_state["flash"] = f"Exercise #{target['exercise_id']} deleted."
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(friendly_error(e))
else:
    st.info("No exercises match your search.")