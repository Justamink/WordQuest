"""Teachers create their classes and manage enrollment."""
import streamlit as st

from auth import require_role
from db import query, get_conn, friendly_error

st.set_page_config(page_title="Manage Classes", page_icon="🎓")
st.title("🎓 Manage Classes and Enrollment")
account = require_role("teacher")
teacher_id = account["teacher_id"]

try:
    courses = query('SELECT course_id, course_code, course_name FROM "Course" ORDER BY course_code;')
    classes = query(
        """
        SELECT cs.class_id, c.course_code, cs.section_number, cs.semester, cs.year
        FROM "ClassSection" cs
        JOIN "Course" c ON c.course_id = cs.course_id
        WHERE cs.teacher_id = %s
        ORDER BY cs.year DESC, cs.semester, c.course_code;
        """,
        (teacher_id,),
    )
except Exception as error:  # noqa: BLE001
    st.error(friendly_error(error))
    st.stop()

with st.expander("Create a class", expanded=not classes):
    if not courses:
        st.info("Add a course to the Course table before creating a class.")
    else:
        with st.form("create_class_form"):
            course = st.selectbox(
                "Course", courses,
                format_func=lambda row: f"{row['course_code']} — {row['course_name']}",
            )
            crn = st.number_input("CRN", min_value=1, step=1)
            section_number = st.number_input("Section number", min_value=1, step=1)
            semester = st.selectbox(
                "Semester", ["Spring", "Summer 1", "Summer 2", "Fall", "Winter"]
            )
            year = st.number_input("Year", min_value=2000, max_value=2100, value=2026)
            create = st.form_submit_button("Create class", type="primary")
        if create:
            try:
                with get_conn() as conn:
                    row = conn.execute(
                        """
                        INSERT INTO "ClassSection"
                            (CRN, course_id, section_number, semester, year, teacher_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING class_id;
                        """,
                        (int(crn), course["course_id"], int(section_number), semester,
                         int(year), teacher_id),
                    ).fetchone()
                st.success(f"Class created (section #{row['class_id']}).")
                st.rerun()
            except Exception as error:  # noqa: BLE001
                st.error(friendly_error(error))

if not classes:
    st.info("Create a class before assigning students.")
    st.stop()

class_by_id = {row["class_id"]: row for row in classes}
selected_class_id = st.selectbox(
    "Your class sections",
    list(class_by_id),
    format_func=lambda cid: (
        f"{class_by_id[cid]['course_code']} · Section "
        f"{class_by_id[cid]['section_number']} · "
        f"{class_by_id[cid]['semester']} {class_by_id[cid]['year']}"
    ),
)

st.subheader("Assign or update enrollment")
st.caption("Use the student ID provided by the student. Only enrolled students in your class appear below.")
with st.form("enrollment_form"):
    student_id = st.number_input("Student ID", min_value=1, step=1)
    status = st.selectbox("Enrollment status", ["active", "inactive"])
    save_enrollment = st.form_submit_button("Save enrollment", type="primary")

if save_enrollment:
    try:
        with get_conn() as conn:
            enrollment = conn.execute(
                """
                INSERT INTO "Enrollment" (student_id, class_id, enrollment_date, status)
                SELECT s.student_id, cs.class_id, CURRENT_DATE, %s
                FROM "Student" s
                JOIN "ClassSection" cs ON cs.class_id = %s
                WHERE s.student_id = %s AND cs.teacher_id = %s
                ON CONFLICT (student_id, class_id) DO UPDATE
                    SET status = EXCLUDED.status
                RETURNING enrollment_id;
                """,
                (status, selected_class_id, int(student_id), teacher_id),
            ).fetchone()
        if enrollment:
            st.success("Enrollment saved.")
            st.rerun()
        st.error("Student or class could not be found for this enrollment.")
    except Exception as error:  # noqa: BLE001
        st.error(friendly_error(error))

st.subheader("Students and progress in this class")
try:
    roster = query(
        """
        SELECT s.student_id, s.first_name, s.last_name, s.email,
               en.status, en.enrollment_date,
               COUNT(sp.progress_id) AS attempts,
               COUNT(sp.progress_id) FILTER (WHERE sp.is_correct) AS correct
        FROM "Enrollment" en
        JOIN "ClassSection" cs ON cs.class_id = en.class_id
        JOIN "Student" s ON s.student_id = en.student_id
        LEFT JOIN "Topic" t ON t.class_id = cs.class_id
        LEFT JOIN "PracticeUnit" u ON u.topic_id = t.topic_id
        LEFT JOIN "Exercise" e ON e.unit_id = u.unit_id
        LEFT JOIN "StudentProgress" sp
               ON sp.exercise_id = e.exercise_id AND sp.student_id = s.student_id
        WHERE cs.class_id = %s AND cs.teacher_id = %s
        GROUP BY s.student_id, s.first_name, s.last_name, s.email,
                 en.status, en.enrollment_date
        ORDER BY s.last_name, s.first_name;
        """,
        (selected_class_id, teacher_id),
    )
    if roster:
        st.dataframe(roster, hide_index=True, use_container_width=True)
    else:
        st.info("No students are enrolled in this class yet.")
except Exception as error:  # noqa: BLE001
    st.error(friendly_error(error))
