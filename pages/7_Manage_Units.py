"""Teacher tools for topics, practice units, and unit settings."""
import streamlit as st

from auth import require_role
from db import query, get_conn, friendly_error

st.set_page_config(page_title="Manage Units", page_icon="📚")
st.title("📚 Manage Topics and Practice Units")
account = require_role("teacher")
teacher_id = account["teacher_id"]

try:
    classes = query(
        """
        SELECT cs.class_id, c.course_code, cs.section_number, cs.semester, cs.year
        FROM "ClassSection" cs JOIN "Course" c ON c.course_id = cs.course_id
        WHERE cs.teacher_id = %s
        ORDER BY cs.year DESC, cs.semester, c.course_code;
        """,
        (teacher_id,),
    )
except Exception as error:  # noqa: BLE001
    st.error(friendly_error(error))
    st.stop()

if not classes:
    st.info("Create a class before adding topics or practice units.")
    st.stop()

class_by_id = {row["class_id"]: row for row in classes}
class_id = st.selectbox(
    "Class section", list(class_by_id),
    format_func=lambda cid: (
        f"{class_by_id[cid]['course_code']} · Section "
        f"{class_by_id[cid]['section_number']} · "
        f"{class_by_id[cid]['semester']} {class_by_id[cid]['year']}"
    ),
)

with st.expander("Create a topic"):
    with st.form("create_topic_form"):
        topic_name = st.text_input("Topic name")
        topic_description = st.text_area("Description")
        topic_order = st.number_input("Display order", min_value=1, value=1, step=1)
        add_topic = st.form_submit_button("Create topic")
    if add_topic:
        if not topic_name.strip():
            st.warning("Enter a topic name.")
        else:
            try:
                with get_conn() as conn:
                    created = conn.execute(
                        """
                        INSERT INTO "Topic" (class_id, name, description, display_order)
                        SELECT class_id, %s, %s, %s FROM "ClassSection"
                        WHERE class_id = %s AND teacher_id = %s
                        RETURNING topic_id;
                        """,
                        (topic_name.strip(), topic_description.strip(), int(topic_order),
                         class_id, teacher_id),
                    ).fetchone()
                if created:
                    st.success("Topic created.")
                    st.rerun()
                st.error("This class section is not available to your account.")
            except Exception as error:  # noqa: BLE001
                st.error(friendly_error(error))

try:
    topics = query(
        """
        SELECT topic_id, name, description
        FROM "Topic" WHERE class_id = %s
        ORDER BY display_order NULLS LAST, name;
        """,
        (class_id,),
    )
except Exception as error:  # noqa: BLE001
    st.error(friendly_error(error))
    st.stop()

with st.expander("Create a practice unit"):
    if not topics:
        st.info("Create a topic in this class first.")
    else:
        topic_by_id = {row["topic_id"]: row for row in topics}
        with st.form("create_unit_form"):
            topic_id = st.selectbox(
                "Topic", list(topic_by_id),
                format_func=lambda tid: topic_by_id[tid]["name"],
            )
            title = st.text_input("Practice unit title")
            description = st.text_area("Description", key="unit_description")
            difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"])
            published = st.checkbox("Publish for enrolled students", value=True)
            unlockable = st.checkbox("Lock until a requirement is met")
            unlock_requirement = st.number_input(
                "Unlock requirement", min_value=1, value=1, step=1,
                disabled=not unlockable,
            )
            add_unit = st.form_submit_button("Create practice unit")
        if add_unit:
            if not title.strip():
                st.warning("Enter a practice unit title.")
            else:
                try:
                    with get_conn() as conn:
                        created = conn.execute(
                            """
                            INSERT INTO "PracticeUnit"
                                (topic_id, title, description, difficulty,
                                 is_published, is_unlockable, unlock_requirement)
                            SELECT t.topic_id, %s, %s, %s, %s, %s, %s
                            FROM "Topic" t
                            JOIN "ClassSection" cs ON cs.class_id = t.class_id
                            WHERE t.topic_id = %s AND cs.teacher_id = %s
                            RETURNING unit_id;
                            """,
                            (title.strip(), description.strip(), difficulty, published,
                             unlockable, int(unlock_requirement) if unlockable else None,
                             topic_id, teacher_id),
                        ).fetchone()
                    if created:
                        st.success("Practice unit created.")
                        st.rerun()
                    st.error("This topic is not available to your account.")
                except Exception as error:  # noqa: BLE001
                    st.error(friendly_error(error))

st.subheader("Edit settings or remove a practice unit")
try:
    units = query(
        """
        SELECT u.unit_id, u.title, u.description, u.difficulty,
               u.is_published, u.is_unlockable, u.unlock_requirement,
               t.name AS topic_name,
               COUNT(sp.progress_id) AS attempts
        FROM "PracticeUnit" u
        JOIN "Topic" t ON t.topic_id = u.topic_id
        JOIN "ClassSection" cs ON cs.class_id = t.class_id
        LEFT JOIN "Exercise" e ON e.unit_id = u.unit_id
        LEFT JOIN "StudentProgress" sp ON sp.exercise_id = e.exercise_id
        WHERE cs.teacher_id = %s AND cs.class_id = %s
        GROUP BY u.unit_id, t.name
        ORDER BY t.name, u.title;
        """,
        (teacher_id, class_id),
    )
except Exception as error:  # noqa: BLE001
    st.error(friendly_error(error))
    st.stop()

if not units:
    st.info("No practice units have been created in this class yet.")
    st.stop()

unit_by_id = {row["unit_id"]: row for row in units}
unit_id = st.selectbox(
    "Practice unit", list(unit_by_id),
    format_func=lambda uid: (
        f"{unit_by_id[uid]['topic_name']} / {unit_by_id[uid]['title']}"
    ),
)
unit = unit_by_id[unit_id]

with st.form(f"unit_settings_{unit_id}"):
    updated_title = st.text_input("Title", value=unit["title"])
    updated_description = st.text_area("Description", value=unit["description"])
    difficulty_options = ["easy", "medium", "hard"]
    if unit["difficulty"] not in difficulty_options:
        difficulty_options.append(unit["difficulty"])
    updated_difficulty = st.selectbox(
        "Difficulty", difficulty_options,
        index=difficulty_options.index(unit["difficulty"]),
    )
    updated_published = st.checkbox("Published", value=unit["is_published"])
    updated_unlockable = st.checkbox("Unlockable", value=unit["is_unlockable"])
    updated_requirement = st.number_input(
        "Unlock requirement", min_value=1,
        value=max(1, int(unit["unlock_requirement"] or 1)),
        disabled=not updated_unlockable,
    )
    save_settings = st.form_submit_button("Save unit settings", type="primary")

if save_settings:
    if not updated_title.strip():
        st.warning("The title cannot be empty.")
    else:
        try:
            with get_conn() as conn:
                updated = conn.execute(
                    """
                    UPDATE "PracticeUnit" u
                    SET title = %s, description = %s, difficulty = %s,
                        is_published = %s, is_unlockable = %s,
                        unlock_requirement = %s
                    WHERE u.unit_id = %s
                      AND EXISTS (
                          SELECT 1 FROM "Topic" t
                          JOIN "ClassSection" cs ON cs.class_id = t.class_id
                          WHERE t.topic_id = u.topic_id AND cs.teacher_id = %s
                      );
                    """,
                    (updated_title.strip(), updated_description.strip(),
                     updated_difficulty, updated_published, updated_unlockable,
                     int(updated_requirement) if updated_unlockable else None,
                     unit_id, teacher_id),
                ).rowcount
            if updated:
                st.success("Practice unit settings saved.")
                st.rerun()
            st.error("This practice unit is not available to your account.")
        except Exception as error:  # noqa: BLE001
            st.error(friendly_error(error))

if unit["attempts"]:
    st.info(
        f"This unit has {unit['attempts']} student attempt(s); it cannot be deleted "
        "while progress records depend on it. Unpublish it to remove it from practice."
    )
else:
    confirm_delete = st.checkbox(
        "Confirm deletion of this practice unit",
        key=f"confirm_unit_delete_{unit_id}",
    )
    if st.button("Delete practice unit", disabled=not confirm_delete):
        try:
            with get_conn() as conn:
                conn.execute(
                    """
                    DELETE FROM "AnswerChoice" a
                    USING "Exercise" e
                    WHERE a.exercise_id = e.exercise_id
                      AND e.unit_id = %s
                      AND EXISTS (
                          SELECT 1 FROM "PracticeUnit" owned
                          JOIN "Topic" ot ON ot.topic_id = owned.topic_id
                          JOIN "ClassSection" ocs ON ocs.class_id = ot.class_id
                          WHERE owned.unit_id = e.unit_id
                            AND ocs.teacher_id = %s
                      );
                    """,
                    (unit_id, teacher_id),
                )
                conn.execute(
                    """
                    DELETE FROM "Exercise" e
                    WHERE e.unit_id = %s AND EXISTS (
                        SELECT 1 FROM "PracticeUnit" u
                        JOIN "Topic" t ON t.topic_id = u.topic_id
                        JOIN "ClassSection" cs ON cs.class_id = t.class_id
                        WHERE u.unit_id = e.unit_id AND cs.teacher_id = %s
                    );
                    """,
                    (unit_id, teacher_id),
                )
                deleted = conn.execute(
                    """
                    DELETE FROM "PracticeUnit" u
                    WHERE u.unit_id = %s AND EXISTS (
                        SELECT 1 FROM "Topic" t
                        JOIN "ClassSection" cs ON cs.class_id = t.class_id
                        WHERE t.topic_id = u.topic_id AND cs.teacher_id = %s
                    );
                    """,
                    (unit_id, teacher_id),
                ).rowcount
            if deleted:
                st.success("Practice unit deleted.")
                st.rerun()
            st.error("This practice unit is not available to your account.")
        except Exception as error:  # noqa: BLE001
            st.error(friendly_error(error))
