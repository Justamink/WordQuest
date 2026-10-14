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

try:
    units = query(UNITS_SQL)
except Exception as e:  # noqa: BLE001
    st.error(friendly_error(e))
    st.stop()

if not units:
    st.info("Create a practice unit first.")
    st.stop()

# Widgets live outside a form so the choice fields can appear/disappear.
unit = st.selectbox(
    "Practice unit", units,
    format_func=lambda u: f"{u['topic_name']} / {u['unit_name']}"
)
question = st.text_area("Question")
qtype = st.selectbox("Question type", ["multiple_choice", "free_response"])
difficulty = st.text_input("Difficulty", value="easy")
points = st.number_input("Points", min_value=1, value=10, step=1)

choice_texts = []
correct_idx = 0
free_response_answer = None

if qtype == "multiple_choice":
    st.markdown("**Answer options** (fill at least two)")
    for label in ["A", "B", "C", "D"]:
        choice_texts.append(st.text_input(f"Option {label}", key=f"opt_{label}"))
    correct_idx = st.radio(
        "Which option is correct?",
        [0, 1, 2, 3],
        format_func=lambda i: f"Option {'ABCD'[i]}",
        horizontal=True,
    )
else:
    free_response_answer = st.text_input("Correct free-response answer")

if st.button("Add exercise"):
    filled = [(i, t.strip()) for i, t in enumerate(choice_texts) if t.strip()]
    if not question.strip():
        st.warning("Please enter a question.")
    elif not difficulty.strip():
        st.warning("Please enter a difficulty.")
    elif qtype == "multiple_choice" and len(filled) < 2:
        st.warning("A multiple-choice question needs at least two options.")
    elif qtype == "multiple_choice" and correct_idx not in [i for i, _ in filled]:
        st.warning("The option marked correct must not be empty.")
    elif qtype == "free_response" and not free_response_answer.strip():
        st.warning("Please enter a correct free-response answer.")
    else:
        try:
            # One transaction: the exercise and all its options succeed or fail together.
            with get_conn() as conn:
                new_id = conn.execute(
                    INSERT_EXERCISE_SQL,
                    (
                        unit["unit_id"],
                        question.strip(),
                        qtype,
                        difficulty.strip(),
                        free_response_answer.strip()
                        if free_response_answer is not None else None,
                        int(points),
                    )
                ).fetchone()["exercise_id"]

                for i, text in filled:
                    conn.execute(
                        INSERT_CHOICE_SQL,
                        (new_id, text, i == correct_idx, i + 1)
                    )

            st.success(f"Exercise #{new_id} added.")
        except Exception as e:  # noqa: BLE001
            st.error(friendly_error(e))