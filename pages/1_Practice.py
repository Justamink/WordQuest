"""S1: A student views questions in a practice unit (Read/Search)."""
import streamlit as st

from db import query, execute, friendly_error

st.set_page_config(page_title="Practice", page_icon="📝")
st.title("📝 Practice")

# ---------------- SQL ----------------
STUDENTS_SQL = """
SELECT student_id, first_name || ' ' || last_name AS name
FROM "Student"
ORDER BY last_name, first_name;
"""

TOPICS_SQL = """
SELECT t.topic_id, t.name AS topic_name, c.course_code
FROM "Topic" t
JOIN "ClassSection" cs ON cs.class_id = t.class_id
JOIN "Course" c ON c.course_id = cs.course_id
ORDER BY c.course_code, t.name;
"""

# Get practice units belonging to the selected topic.
UNITS_SQL = """
SELECT unit_id, title AS unit_name
FROM "PracticeUnit"
WHERE topic_id = %s
ORDER BY title;
"""

# Get exercises belonging to the selected practice unit.
EXERCISES_SQL = """
SELECT e.exercise_id, e.question_text, e.question_type,
       u.title AS unit_name
FROM "Exercise" e
JOIN "PracticeUnit" u ON u.unit_id = e.unit_id
WHERE u.unit_id = %s
ORDER BY e.exercise_id;
"""

CHOICES_SQL = """
SELECT choice_id, choice_text
FROM "AnswerChoice"
WHERE exercise_id = %s
ORDER BY display_order NULLS LAST, choice_id;
"""

# Multiple choice: look up whether the chosen option is correct.
# StudentProgress does not have a choice_id column.
INSERT_MC_SQL = """
INSERT INTO "StudentProgress"
    (student_id, exercise_id, submitted_answer, is_correct,
     attempt_number, answered_at)
SELECT %s, ac.exercise_id, ac.choice_text, ac.is_correct,
       (SELECT COUNT(*) + 1
        FROM "StudentProgress" sp
        WHERE sp.student_id = %s AND sp.exercise_id = ac.exercise_id),
       NOW()
FROM "AnswerChoice" ac
WHERE ac.choice_id = %s AND ac.exercise_id = %s
RETURNING progress_id, is_correct;
"""

# Free response: is_correct is required by the database.
# Save False initially; a teacher can review/change it later.
INSERT_FR_SQL = """
INSERT INTO "StudentProgress"
    (student_id, exercise_id, submitted_answer, is_correct,
     attempt_number, answered_at)
VALUES (
    %s, %s, %s, FALSE,
    (SELECT COUNT(*) + 1
     FROM "StudentProgress"
     WHERE student_id = %s AND exercise_id = %s),
    NOW()
)
RETURNING progress_id;
"""

RECENT_SQL = """
SELECT sp.progress_id, e.question_text, sp.submitted_answer,
       sp.is_correct, sp.answered_at
FROM "StudentProgress" sp
JOIN "Exercise" e ON e.exercise_id = sp.exercise_id
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
    "Who is answering?",
    students,
    format_func=lambda s: s["name"]
)

topics = load(TOPICS_SQL)
if not topics:
    st.info("No topics in the database yet.")
    st.stop()

topic = st.selectbox(
    "Topic",
    topics,
    format_func=lambda t: f"{t['course_code']} - {t['topic_name']}",
)

# Select a practice unit within the chosen topic.
units = load(UNITS_SQL, (topic["topic_id"],))
if not units:
    st.info("No practice units in this topic yet.")
    st.stop()

unit = st.selectbox(
    "Practice unit",
    units,
    format_func=lambda u: u["unit_name"],
)

# Only display exercises from the selected practice unit.
exercises = load(EXERCISES_SQL, (unit["unit_id"],))
if not exercises:
    st.info("No exercises in this practice unit yet.")
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
            "Pick one:",
            list(labels),
            format_func=lambda cid: labels[cid],
            index=None
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
                    (
                        student["student_id"],
                        student["student_id"],
                        choice_id,
                        exercise["exercise_id"],
                    ),
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
                    (
                        student["student_id"],
                        exercise["exercise_id"],
                        free_text.strip(),
                        student["student_id"],
                        exercise["exercise_id"],
                    ),
                )
                st.success("Answer submitted! Your teacher will review it.")
    except Exception as e:  # noqa: BLE001
        st.error(friendly_error(e))

st.subheader("Your recent attempts")
st.dataframe(
    load(RECENT_SQL, (student["student_id"],)),
    hide_index=True,
    use_container_width=True
)
