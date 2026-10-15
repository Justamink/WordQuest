"""S2: A teacher adds a question and answer options (Insert)."""
import streamlit as st

from db import query, get_conn, friendly_error

st.set_page_config(page_title="Add Exercise", page_icon="➕")
st.title("➕ Add Exercise")

# ---------------- SQL ----------------
UNITS_SQL = """
SELECT u.unit_id, u.title AS unit_name, t.name AS topic_name
FROM "PracticeUnit" u
JOIN "Topic" t ON t.topic_id = u.topic_id
ORDER BY t.name, u.title;
"""

INSERT_EXERCISE_SQL = """
INSERT INTO "Exercise"
    (unit_id, question_text, question_type, difficulty,
     free_response_answer, points)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING exercise_id;
"""

INSERT_CHOICE_SQL = """
INSERT INTO "AnswerChoice"
    (exercise_id, choice_text, is_correct, display_order)
VALUES (%s, %s, %s, %s);
"""

QUESTION_TYPES = [
    "multiple_choice",
    "multi_select",
    "fill_in_blank",
    "free_response",
]
# Values as stored in the database's question_type column.
DB_TYPE_VALUES = {
    "multiple_choice": "multiple choice",
    "multi_select": "multi select",
    "fill_in_blank": "fill in the blank",
    "free_response": "free response",
}
TYPE_LABELS = {
    "multiple_choice": "Multiple choice (one correct answer)",
    "multi_select": "Multi-select (one or more correct answers)",
    "fill_in_blank": "Fill in the blank (auto-graded)",
    "free_response": "Free response",
}

AUTO_GRADED = "Enter a correct answer (auto-graded)"
MANUAL_GRADED = "No stored answer (grade manually later)"

try:
    units = query(UNITS_SQL)
except Exception as e:  # noqa: BLE001
    st.error(friendly_error(e))
    st.stop()

if not units:
    st.info("Create a practice unit first.")
    st.stop()

# Widgets live outside a form so the answer fields can appear/disappear.
unit = st.selectbox(
    "Practice unit", units,
    format_func=lambda u: f"{u['topic_name']} / {u['unit_name']}"
)
question = st.text_area("Question")
qtype = st.selectbox(
    "Question type", QUESTION_TYPES,
    format_func=lambda t: TYPE_LABELS[t],
)
difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"])
points = st.number_input("Points", min_value=1, value=10, step=1)

choice_texts = []
correct_set = set()          # indexes (0-3) of correct options
free_response_answer = None
manual_grading = False

if qtype in ("multiple_choice", "multi_select"):
    st.markdown("**Answer options** (fill at least two)")
    for label in ["A", "B", "C", "D"]:
        choice_texts.append(st.text_input(f"Option {label}", key=f"opt_{label}"))

    if qtype == "multiple_choice":
        correct_set = {
            st.radio(
                "Which option is correct?",
                [0, 1, 2, 3],
                format_func=lambda i: f"Option {'ABCD'[i]}",
                horizontal=True,
            )
        }
    else:
        correct_set = set(
            st.multiselect(
                "Which options are correct? (select all that apply)",
                [0, 1, 2, 3],
                format_func=lambda i: f"Option {'ABCD'[i]}",
            )
        )

elif qtype == "fill_in_blank":
    st.caption(
        "Use a run of underscores in the question text to mark the blank, "
        "e.g. \"The past tense of 'run' is ____.\""
    )
    free_response_answer = st.text_input("Correct answer for the blank")

else:  # free_response
    grading_mode = st.radio(
        "Grading",
        [AUTO_GRADED, MANUAL_GRADED],
        help=(
            "Manually graded answers are reviewed by a teacher on the "
            "Grade Answers page."
        ),
    )
    manual_grading = grading_mode == MANUAL_GRADED

    if manual_grading:
        st.caption(
            "No correct answer will be stored. Student answers will be "
            "reviewed on the Grade Answers page."
        )
    else:
        free_response_answer = st.text_input("Correct free-response answer")

if st.button("Add exercise"):
    filled = [(i, t.strip()) for i, t in enumerate(choice_texts) if t.strip()]
    filled_idx = {i for i, _ in filled}

    if not question.strip():
        st.warning("Please enter a question.")
    elif qtype in ("multiple_choice", "multi_select") and len(filled) < 2:
        st.warning("This question type needs at least two options.")
    elif qtype == "multiple_choice" and not correct_set <= filled_idx:
        st.warning("The option marked correct must not be empty.")
    elif qtype == "multi_select" and not correct_set:
        st.warning("Select at least one correct option.")
    elif qtype == "multi_select" and not correct_set <= filled_idx:
        st.warning("Every option marked correct must be filled in.")
    elif qtype == "fill_in_blank" and not (free_response_answer or "").strip():
        st.warning("Please enter the correct answer for the blank.")
    elif (
        qtype == "free_response"
        and not manual_grading
        and not (free_response_answer or "").strip()
    ):
        st.warning(
            "Please enter a correct free-response answer, or choose "
            "manual grading."
        )
    else:
        try:
            # One transaction: the exercise and all its options succeed or fail together.
            with get_conn() as conn:
                new_id = conn.execute(
                    INSERT_EXERCISE_SQL,
                    (
                        unit["unit_id"],
                        question.strip(),
                        DB_TYPE_VALUES[qtype],
                        difficulty,
                        free_response_answer.strip()
                        if free_response_answer is not None else None,
                        int(points),
                    )
                ).fetchone()["exercise_id"]

                for i, text in filled:
                    conn.execute(
                        INSERT_CHOICE_SQL,
                        (new_id, text, i in correct_set, i + 1)
                    )

            st.success(f"Exercise #{new_id} added.")
        except Exception as e:  # noqa: BLE001
            st.error(friendly_error(e))