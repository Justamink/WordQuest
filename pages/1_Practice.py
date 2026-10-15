"""S1: A student views questions in a practice unit (Read/Search) and answers them."""
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
# free_response_answer is used only for grading, never shown to the student.
EXERCISES_SQL = """
SELECT e.exercise_id, e.question_text, e.question_type, e.points,
       e.free_response_answer, u.title AS unit_name
FROM "Exercise" e
JOIN "PracticeUnit" u ON u.unit_id = e.unit_id
WHERE u.unit_id = %s
ORDER BY e.exercise_id;
"""

# is_correct is used for grading only and is not displayed to the student.
CHOICES_SQL = """
SELECT choice_id, choice_text, is_correct
FROM "AnswerChoice"
WHERE exercise_id = %s
ORDER BY display_order NULLS LAST, choice_id;
"""

# One insert for every question type; is_correct is decided in Python.
# StudentProgress does not have a choice_id column, so the chosen option(s)
# are saved as text in submitted_answer.
INSERT_ATTEMPT_SQL = """
INSERT INTO "StudentProgress"
    (student_id, exercise_id, submitted_answer, is_correct,
     attempt_number, answered_at)
VALUES (
    %s, %s, %s, %s,
    (SELECT COUNT(*) + 1
     FROM "StudentProgress"
     WHERE student_id = %s AND exercise_id = %s),
    NOW()
)
RETURNING progress_id;
"""

RECENT_SQL = """
SELECT sp.progress_id, sp.attempt_number, sp.submitted_answer,
       sp.is_correct, sp.answered_at
FROM "StudentProgress" sp
WHERE sp.student_id = %s AND sp.exercise_id = %s
ORDER BY sp.answered_at DESC, sp.progress_id DESC
LIMIT 10;
"""

# ---------------- Helpers ----------------
TYPE_ALIASES = {
    "fill_in_the_blank": "fill_in_blank",
    "multiple_select": "multi_select",
    "multiselect": "multi_select",
    "short_answer": "free_response",
}

TYPE_HINTS = {
    "multiple_choice": "Multiple choice: pick one answer.",
    "multi_select": "Multi select: choose every answer that applies.",
    "fill_in_blank": "Fill in the blank: type the missing word or phrase.",
    "free_response": "Free response: write your answer.",
}


def norm_type(raw):
    """Turn 'Multiple Choice' / 'fill in the blank' into a stable key."""
    t = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    return TYPE_ALIASES.get(t, t)


def norm_answer(text):
    """Case-insensitive, whitespace-insensitive comparison form."""
    return " ".join((text or "").lower().split())


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

# Shares the "logged in" student with the home page dashboard.
by_id = {s["student_id"]: s for s in students}
ids = list(by_id)
if st.session_state.get("current_student_id") not in by_id:
    st.session_state["current_student_id"] = ids[0]

student_id = st.selectbox(
    "Who is answering?",
    ids,
    key="current_student_id",
    format_func=lambda i: by_id[i]["name"],
)
student = by_id[student_id]

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

ex_id = exercise["exercise_id"]
qtype = norm_type(exercise["question_type"])
stored_answer = (exercise["free_response_answer"] or "").strip()

st.markdown(f"### {exercise['question_text']}")
st.caption(
    f"{TYPE_HINTS.get(qtype, 'Write your answer.')} "
    f"· {exercise['points']} point(s)"
)

choices = []
if qtype in ("multiple_choice", "multi_select"):
    choices = load(CHOICES_SQL, (ex_id,))
    if not choices:
        st.info("This exercise has no answer options yet.")
        st.stop()

labels = {c["choice_id"]: c["choice_text"] for c in choices}

# The form key includes the exercise id so answers reset between exercises.
with st.form(f"answer_form_{ex_id}"):
    choice_id = None
    selected_ids = []
    typed = ""

    if qtype == "multiple_choice":
        choice_id = st.radio(
            "Pick one:",
            list(labels),
            format_func=lambda cid: labels[cid],
            index=None,
            key=f"mc_{ex_id}",
        )
    elif qtype == "multi_select":
        selected_ids = st.multiselect(
            "Select all that apply:",
            list(labels),
            format_func=lambda cid: labels[cid],
            key=f"ms_{ex_id}",
        )
    elif qtype == "fill_in_blank":
        typed = st.text_input("Your answer for the blank", key=f"fib_{ex_id}")
    else:  # free_response (and any unrecognized type)
        typed = st.text_area("Your answer", key=f"fr_{ex_id}")

    submitted = st.form_submit_button("Submit answer")

if submitted:
    answer_text = None
    is_correct = False
    needs_review = False   # True when a teacher has to grade it
    ready = True

    if qtype == "multiple_choice":
        if choice_id is None:
            st.warning("Please select an answer first.")
            ready = False
        else:
            picked = next(c for c in choices if c["choice_id"] == choice_id)
            answer_text = picked["choice_text"]
            is_correct = bool(picked["is_correct"])

    elif qtype == "multi_select":
        if not selected_ids:
            st.warning("Please select at least one answer first.")
            ready = False
        else:
            # Keep the options in their display order when saving.
            answer_text = "; ".join(
                c["choice_text"] for c in choices
                if c["choice_id"] in selected_ids
            )
            correct_ids = {
                c["choice_id"] for c in choices if c["is_correct"]
            }
            # Correct only if the selection matches the correct set exactly.
            is_correct = set(selected_ids) == correct_ids

    else:  # fill_in_blank / free_response
        if not typed.strip():
            st.warning("Please type an answer first.")
            ready = False
        else:
            answer_text = typed.strip()
            if stored_answer:
                # Auto-graded: compare against the stored correct answer.
                is_correct = norm_answer(answer_text) == norm_answer(
                    stored_answer
                )
            else:
                # No stored answer: a teacher grades it later.
                needs_review = True

    if ready:
        try:
            execute(
                INSERT_ATTEMPT_SQL,
                (
                    student["student_id"],
                    ex_id,
                    answer_text,
                    is_correct,
                    student["student_id"],
                    ex_id,
                ),
            )
            if needs_review:
                st.success("Answer submitted! Your teacher will review it.")
            elif is_correct:
                st.success("Correct! 🎉")
            elif qtype == "multi_select":
                st.error(
                    "Not quite. Remember to choose every correct answer, "
                    "and only the correct ones."
                )
            else:
                st.error("Not quite. Try another exercise!")
        except Exception as e:  # noqa: BLE001
            st.error(friendly_error(e))

st.subheader("Your recent attempts on this exercise")
recent = load(RECENT_SQL, (student["student_id"], ex_id))
if recent:
    st.dataframe(recent, hide_index=True, use_container_width=True)
else:
    st.caption("You haven't attempted this exercise yet.")