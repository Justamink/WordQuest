"""Teacher grades free-response answers (Update)."""
import streamlit as st

from db import query, execute, friendly_error

st.set_page_config(page_title="Grade Answers", page_icon="✅")
st.title("✅ Grade Answers")

# ---------------- SQL ----------------
UNGRADED_SQL = """
SELECT sp.progress_id, s.name, e.question_text, sp.submitted_answer, sp.answered_at
FROM studentprogress sp
JOIN student s ON s.student_id = sp.student_id
JOIN exercise e ON e.exercise_id = sp.exercise_id
WHERE sp.choice_id IS NULL AND sp.is_correct IS NULL
ORDER BY sp.answered_at;
"""

GRADE_SQL = "UPDATE studentprogress SET is_correct = %s WHERE progress_id = %s;"

GRADED_SQL = """
SELECT sp.progress_id, s.name, e.question_text, sp.submitted_answer, sp.is_correct
FROM studentprogress sp
JOIN student s ON s.student_id = sp.student_id
JOIN exercise e ON e.exercise_id = sp.exercise_id
WHERE sp.choice_id IS NULL AND sp.is_correct IS NOT NULL
ORDER BY sp.answered_at DESC
LIMIT 10;
"""

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

try:
    pending = query(UNGRADED_SQL)
    graded = query(GRADED_SQL)
except Exception as e:  # noqa: BLE001
    st.error(friendly_error(e))
    st.stop()

st.subheader(f"Awaiting review ({len(pending)})")
if not pending:
    st.info("Nothing to grade right now.")

for row in pending:
    with st.container(border=True):
        st.markdown(f"**{row['name']}** answered: _{row['question_text']}_")
        st.write(row["submitted_answer"])
        c1, c2, _ = st.columns([1, 1, 4])
        for col, label, value in ((c1, "Correct", True), (c2, "Incorrect", False)):
            if col.button(label, key=f"{label}_{row['progress_id']}"):
                try:
                    execute(GRADE_SQL, (value, row["progress_id"]))
                    st.session_state["flash"] = (
                        f"Attempt #{row['progress_id']} marked {label.lower()}."
                    )
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(friendly_error(e))

st.subheader("Recently graded")
st.dataframe(graded, hide_index=True, use_container_width=True)