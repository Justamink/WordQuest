"""Manage exercises: S3 Update and S4 Delete."""
import streamlit as st

from db import query, get_conn, friendly_error

st.set_page_config(page_title="Manage Exercises", page_icon="🗂️")
st.title("🗂️ Manage Exercises")

# ---------------- SQL ----------------
SEARCH_SQL = """
SELECT e.exercise_id, e.question_text, e.question_type,
       e.difficulty, e.points, e.free_response_answer,
       u.title AS unit_name,
       (SELECT COUNT(*)
        FROM "AnswerChoice" a
        WHERE a.exercise_id = e.exercise_id) AS num_choices,
       (SELECT COUNT(*)
        FROM "StudentProgress" sp
        WHERE sp.exercise_id = e.exercise_id) AS num_attempts
FROM "Exercise" e
JOIN "PracticeUnit" u ON u.unit_id = e.unit_id
WHERE e.question_text ILIKE %s
ORDER BY e.exercise_id;
"""

CHOICES_SQL = """
SELECT choice_id, choice_text, is_correct
FROM "AnswerChoice"
WHERE exercise_id = %s
ORDER BY display_order NULLS LAST, choice_id;
"""

UPDATE_SQL = """
UPDATE "Exercise"
SET question_text = %s,
    difficulty = %s,
    points = %s,
    free_response_answer = %s
WHERE exercise_id = %s;
"""

UPDATE_CHOICE_SQL = """
UPDATE "AnswerChoice"
SET choice_text = %s,
    is_correct = %s
WHERE choice_id = %s AND exercise_id = %s;
"""

DELETE_CHOICES_SQL = """
DELETE FROM "AnswerChoice"
WHERE exercise_id = %s;
"""

DELETE_SQL = """
DELETE FROM "Exercise"
WHERE exercise_id = %s;
"""

CHECK_ATTEMPTS_SQL = """
SELECT COUNT(*) AS num_attempts
FROM "StudentProgress"
WHERE exercise_id = %s;
"""

# ---------------- UI ----------------

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

keyword = st.text_input("Search question text")

try:
    rows = query(SEARCH_SQL, (f"%{keyword}%",))
except Exception as e:  # noqa: BLE001
    st.error(friendly_error(e))
    st.stop()

st.dataframe(rows, hide_index=True, use_container_width=True)

if not rows:
    st.info("No exercises match your search.")
    st.stop()

target = st.selectbox(
    "Select an exercise",
    rows,
    format_func=lambda r: (
        f"#{r['exercise_id']} - {r['question_text'][:60]}"
    ),
)

try:
    choices = query(
        CHOICES_SQL,
        (target["exercise_id"],)
    )
except Exception as e:
    st.error(friendly_error(e))
    st.stop()

# ---------------- S3: UPDATE ----------------

st.subheader("Edit an exercise")

with st.form(f"edit_form_{target['exercise_id']}"):

    question = st.text_area(
        "Question text",
        value=target["question_text"]
    )

    difficulty = st.text_input(
        "Difficulty",
        value=target["difficulty"]
    )

    points = st.number_input(
        "Points",
        min_value=1,
        value=max(1, int(target["points"])),
        step=1
    )

    free_response_answer = None
    updated_choices = []
    correct_choice_id = None

    if target["question_type"] == "free_response":

        free_response_answer = st.text_input(
            "Correct free-response answer",
            value=target["free_response_answer"] or ""
        )

    elif target["question_type"] == "multiple_choice":

        st.markdown("**Answer options**")

        for choice in choices:
            new_text = st.text_input(
                f"Option #{choice['choice_id']}",
                value=choice["choice_text"],
                key=(
                    f"choice_{target['exercise_id']}_"
                    f"{choice['choice_id']}"
                ),
            )

            updated_choices.append(
                (choice["choice_id"], new_text)
            )

        if choices:
            choice_ids = [c["choice_id"] for c in choices]

            current_correct = next(
                (
                    c["choice_id"]
                    for c in choices
                    if c["is_correct"]
                ),
                choice_ids[0]
            )

            correct_choice_id = st.radio(
                "Correct answer",
                choice_ids,
                index=choice_ids.index(current_correct),
                format_func=lambda cid: (
                    next(
                        c["choice_text"]
                        for c in choices
                        if c["choice_id"] == cid
                    )
                ),
            )

    save = st.form_submit_button("Save changes")

if save:
    if not question.strip():
        st.warning("Question text cannot be empty.")

    elif not difficulty.strip():
        st.warning("Difficulty cannot be empty.")

    elif (
        target["question_type"] == "free_response"
        and not (free_response_answer or "").strip()
    ):
        st.warning("Please enter a correct free-response answer.")

    elif any(
        not text.strip()
        for _, text in updated_choices
    ):
        st.warning("Answer options cannot be empty.")

    else:
        try:
            with get_conn() as conn:

                conn.execute(
                    UPDATE_SQL,
                    (
                        question.strip(),
                        difficulty.strip(),
                        int(points),
                        (
                            free_response_answer.strip()
                            if free_response_answer is not None
                            else None
                        ),
                        target["exercise_id"],
                    )
                )

                for choice_id, text in updated_choices:
                    conn.execute(
                        UPDATE_CHOICE_SQL,
                        (
                            text.strip(),
                            choice_id == correct_choice_id,
                            choice_id,
                            target["exercise_id"],
                        )
                    )

            st.session_state["flash"] = (
                f"Exercise #{target['exercise_id']} updated."
            )
            st.rerun()

        except Exception as e:
            st.error(friendly_error(e))


# ---------------- S4: DELETE ----------------

st.subheader("Delete an exercise")

st.warning(
    f"This exercise has {target['num_choices']} answer option(s) "
    f"and {target['num_attempts']} student attempt(s)."
)

if target["num_attempts"] > 0:
    st.info(
        "This exercise cannot be deleted because students have "
        "already submitted answers. Their progress must be preserved."
    )

else:
    confirm = st.checkbox(
        "Yes, I'm sure I want to delete this exercise",
        key=f"delete_confirm_{target['exercise_id']}"
    )

    if st.button("Delete exercise", disabled=not confirm):
        try:
            with get_conn() as conn:

                # Recheck before deleting.
                attempts = conn.execute(
                    CHECK_ATTEMPTS_SQL,
                    (target["exercise_id"],)
                ).fetchone()["num_attempts"]

                if attempts > 0:
                    raise ValueError(
                        "This exercise now has student attempts "
                        "and cannot be deleted."
                    )

                # Delete answer options first, then the exercise.
                conn.execute(
                    DELETE_CHOICES_SQL,
                    (target["exercise_id"],)
                )

                deleted = conn.execute(
                    DELETE_SQL,
                    (target["exercise_id"],)
                ).rowcount

                if deleted != 1:
                    raise ValueError(
                        "The exercise no longer exists."
                    )

            st.session_state["flash"] = (
                f"Exercise #{target['exercise_id']} deleted."
            )
            st.rerun()

        except Exception as e:
            st.error(friendly_error(e))
