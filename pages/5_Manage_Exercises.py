"""Manage exercises: S3 Update and S4 Delete."""
import streamlit as st

from db import query, get_conn, friendly_error

st.set_page_config(page_title="Manage Exercises", page_icon="🗂️")
st.title("🗂️ Manage Exercises")

AUTO_GRADED = "Enter a correct answer (auto-graded)"
MANUAL_GRADED = "No stored answer (grade manually later)"

# ---------------- SQL ----------------
SEARCH_SQL = """
SELECT e.exercise_id, e.question_text, e.question_type,
       e.difficulty, e.points, e.free_response_answer,
       u.unit_id, u.title AS unit_name,
       (SELECT COUNT(*)
        FROM "AnswerChoice" a
        WHERE a.exercise_id = e.exercise_id) AS num_choices,
       (SELECT COUNT(*)
        FROM "StudentProgress" sp
        WHERE sp.exercise_id = e.exercise_id) AS num_attempts
FROM "Exercise" e
JOIN "PracticeUnit" u ON u.unit_id = e.unit_id
WHERE e.question_text ILIKE %s
  AND (%s::text IS NULL OR e.question_type = %s::text)
  AND (%s::text IS NULL OR e.difficulty = %s::text)
  AND (%s::int IS NULL OR e.unit_id = %s::int)
ORDER BY e.exercise_id;
"""

TYPES_SQL = """
SELECT DISTINCT question_type FROM "Exercise" ORDER BY question_type;
"""

DIFFICULTIES_SQL = """
SELECT DISTINCT difficulty FROM "Exercise" ORDER BY difficulty;
"""

UNITS_SQL = """
SELECT unit_id, title FROM "PracticeUnit" ORDER BY title, unit_id;
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

# Load filter options from the database.
try:
    type_options = [r["question_type"] for r in query(TYPES_SQL)]
    difficulty_options = [r["difficulty"] for r in query(DIFFICULTIES_SQL)]
    unit_options = query(UNITS_SQL)
except Exception as e:  # noqa: BLE001
    st.error(friendly_error(e))
    st.stop()

keyword = st.text_input("Search question text")

col_type, col_diff, col_unit = st.columns(3)

with col_type:
    type_filter = st.selectbox(
        "Question type",
        [None] + type_options,
        format_func=lambda t: "All types" if t is None else t,
    )

with col_diff:
    difficulty_filter = st.selectbox(
        "Difficulty",
        [None] + difficulty_options,
        format_func=lambda d: "All difficulties" if d is None else d,
    )

with col_unit:
    unit_filter = st.selectbox(
        "Unit",
        [None] + [u["unit_id"] for u in unit_options],
        format_func=lambda uid: (
            "All units"
            if uid is None
            else next(
                f"{u['title']} (#{u['unit_id']})"
                for u in unit_options
                if u["unit_id"] == uid
            )
        ),
    )

try:
    rows = query(
        SEARCH_SQL,
        (
            f"%{keyword}%",
            type_filter, type_filter,
            difficulty_filter, difficulty_filter,
            unit_filter, unit_filter,
        ),
    )
except Exception as e:  # noqa: BLE001
    st.error(friendly_error(e))
    st.stop()

st.caption(f"{len(rows)} exercise(s) found.")
st.dataframe(rows, hide_index=True, use_container_width=True)

if not rows:
    st.info("No exercises match your search and filters.")
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

# Normalize the stored type so values like "Multiple Choice" or
# "fill-in-the-blank" are still recognized.
_TYPE_ALIASES = {
    "fill_in_the_blank": "fill_in_blank",
    "multiple_select": "multi_select",
    "multiselect": "multi_select",
    "short_answer": "free_response",
}
_raw_type = (
    str(target["question_type"]).strip().lower()
    .replace(" ", "_").replace("-", "_")
)
qtype = _TYPE_ALIASES.get(_raw_type, _raw_type)

# ---------------- S3: UPDATE ----------------

st.subheader("Edit an exercise")

if target["num_attempts"] > 0:
    st.warning(
        f"⚠️ Students have already submitted {target['num_attempts']} "
        "attempt(s) on this exercise. Changing the question, answer "
        "options or correct answer will NOT re-grade those attempts. "
        "Their saved results stay as they were, so they may no longer "
        "match the new answer key."
    )

with st.form(f"edit_form_{target['exercise_id']}"):

    question = st.text_area(
        "Question text",
        value=target["question_text"]
    )

    # Keep any existing non-standard value selectable so it isn't lost.
    difficulty_choices = ["easy", "medium", "hard"]
    if target["difficulty"] not in difficulty_choices:
        difficulty_choices.append(target["difficulty"])

    difficulty = st.selectbox(
        "Difficulty",
        difficulty_choices,
        index=difficulty_choices.index(target["difficulty"]),
    )

    points = st.number_input(
        "Points",
        min_value=1,
        value=max(1, int(target["points"])),
        step=1
    )

    free_response_answer = None
    updated_choices = []
    correct_choice_ids = set()
    manual_grading = False

    if qtype == "fill_in_blank":

        free_response_answer = st.text_input(
            "Correct answer for the blank",
            value=target["free_response_answer"] or ""
        )

    elif qtype == "free_response":

        has_answer = bool((target["free_response_answer"] or "").strip())

        grading_mode = st.radio(
            "Grading",
            [AUTO_GRADED, MANUAL_GRADED],
            index=0 if has_answer else 1,
            help=(
                "Manually graded answers are reviewed by a teacher on the "
                "Grade Answers page."
            ),
        )
        manual_grading = grading_mode == MANUAL_GRADED

        free_response_answer = st.text_input(
            "Correct free-response answer (only used if auto-graded)",
            value=target["free_response_answer"] or ""
        )

        if manual_grading:
            # No stored answer for manually graded questions.
            free_response_answer = None

    elif qtype in ("multiple_choice", "multi_select"):

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

            def _choice_label(cid):
                return next(
                    c["choice_text"]
                    for c in choices
                    if c["choice_id"] == cid
                )

            if qtype == "multi_select":
                correct_choice_ids = set(
                    st.multiselect(
                        "Correct answers (select all that apply)",
                        choice_ids,
                        default=[
                            c["choice_id"] for c in choices if c["is_correct"]
                        ],
                        format_func=_choice_label,
                    )
                )
            else:
                correct_choice_ids = {
                    st.radio(
                        "Correct answer",
                        choice_ids,
                        index=choice_ids.index(current_correct),
                        format_func=_choice_label,
                    )
                }

    else:
        st.info(
            f"The question type '{target['question_type']}' isn't "
            "recognized, so its answer can't be edited here. Expected one "
            "of: multiple_choice, multi_select, fill_in_blank, "
            "free_response."
        )

    if qtype in ("multiple_choice", "multi_select") and not choices:
        st.info("This exercise has no answer options saved yet.")

    save = st.form_submit_button("Save changes")

if save:
    if not question.strip():
        st.warning("Question text cannot be empty.")

    elif not difficulty.strip():
        st.warning("Difficulty cannot be empty.")

    elif (
        qtype == "fill_in_blank"
        and not (free_response_answer or "").strip()
    ):
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

    elif (
        qtype == "multi_select"
        and not correct_choice_ids
    ):
        st.warning("Select at least one correct answer.")

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
                            (free_response_answer.strip() or None)
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
                            choice_id in correct_choice_ids,
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