"""S1: A student answers a question (Read + Insert)."""
import streamlit as st

from db import query, execute, friendly_error

st.set_page_config(page_title="Practice", page_icon="📝")
st.title("📝 Practice")

# ---------------- SQL ----------------
STUDENTS_SQL = "SELECT student_id, name FROM student ORDER BY name;"

TOPICS_SQL = """
SELECT t.topic_id, t.topic_name, c.course_code
FROM topic t
JOIN course c ON c.course_id = t.course_id
ORDER BY c.course_code, t.topic_name;
"""

EXERCISES_SQL = """
SELECT e.exercise_id, e.question_text, e.question_type, u.unit_name
FROM exercise e
JOIN practiceunit u ON u.unit_id = e.unit_id
WHERE u.topic_id = %s
ORDER BY u.unit_name, e.exercise_id;
"""

CHOICES_SQL = """
SELECT choice_id, choice_text
FROM answerchoice
WHERE exercise_id = %s
ORDER BY choice_id;
"""

# Multiple choice: the database looks up whether the chosen option is correct.
INSERT_MC_SQL = """
INSERT INTO studentprogress (student_id, exercise_id, choice_id, is_correct, answered_at)
SELECT %s, exercise_id, choice_id, is_correct, NOW()
FROM answerchoice
WHERE choice_id = %s AND exercise_id = %s
RETURNING progress_id, is_correct;
"""

# Free response: is_correct stays NULL until a teacher grades it.
INSERT_FR_SQL = """
INSERT INTO studentprogress (student_id, exercise_id, submitted_answer, answered_at)
VALUES (%s, %s, %s, NOW())
RETURNING progress_id;
"""

RECENT_SQL = """
SELECT sp.progress_id, e.question_text, sp.choice_id, sp.submitted_answer,
       sp.is_correct, sp.answered_at
FROM studentprogress sp
JOIN exercise e ON e.exercise_id = sp.exercise_id
WHERE sp.student_id = %s
ORDER BY sp.answered_at DESC
LIMIT 10;
"""


def load(sql, params=None):
    try:
        return query(sql, params)
    except Exception as e:  # noqa: BLE001
        st.error(friendly_error(e))
        st.stop()


# ---------------- UI ----------------
students = load(STUDENTS_SQL)
if not students:
    st.info("No students in the database yet.")
    st.stop()

student = st.selectbox(
    "Who is answering?", students, format_func=lambda s: s["name"]
)

topics = load(TOPICS_SQL)
topic = st.selectbox(
    "Topic",
    topics,
    format_func=lambda t: f"{t['course_code']} - {t['topic_name']}",
)

exercises = load(EXERCISES_SQL, (topic["topic_id"],))
if not exercises:
    st.info("No exercises in this topic yet.")
    st.stop()

exercise = st.selectbox(
    "Exercise",
    exercises,
    format_func=lambda e: f"[{e['unit_name']}] {e['question_text'][:70]}",
)

st.markdown(f"### {exercise['question_text']}")

with st.form("answer_form"):
    choice_id = None
    free_text = ""
    if exercise["question_type"] == "multiple_choice":
        choices = load(CHOICES_SQL, (exercise["exercise_id"],))
        labels = {c["choice_id"]: c["choice_text"] for c in choices}
        choice_id = st.radio(
            "Pick one:", list(labels), format_func=lambda cid: labels[cid], index=None
        )
    else:
        free_text = st.text_area("Your answer")

    submitted = st.form_submit_button("Submit answer")

if submitted:
    try:
        if exercise["question_type"] == "multiple_choice":
            if choice_id is None:
                st.warning("Please select an answer first.")
            else:
                rows = execute(
                    INSERT_MC_SQL,
                    (student["student_id"], choice_id, exercise["exercise_id"]),
                )
                if rows and rows[0]["is_correct"]:
                    st.success("Correct! 🎉")
                else:
                    st.error("Not quite. Try another exercise!")
        else:
            if not free_text.strip():
                st.warning("Please type an answer first.")
            else:
                execute(
                    INSERT_FR_SQL,
                    (student["student_id"], exercise["exercise_id"], free_text.strip()),
                )
                st.success("Answer submitted! Your teacher will review it.")
    except Exception as e:  # noqa: BLE001
        st.error(friendly_error(e))

st.subheader("Your recent attempts")
st.dataframe(load(RECENT_SQL, (student["student_id"],)), hide_index=True, use_container_width=True)