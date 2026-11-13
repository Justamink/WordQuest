"""Teachers create a student account and enroll the student in their class."""
import streamlit as st

from auth import create_student_account_for_teacher, PASSWORD_MIN_LENGTH, require_role
from db import query, friendly_error

st.set_page_config(page_title="Create Student", page_icon="👩‍🎓")
st.title("👩‍🎓 Create a Student User")
account = require_role("teacher")
teacher_id = account["teacher_id"]

try:
    classes = query(
        """
        SELECT cs.class_id, c.course_code, c.course_name,
               cs.section_number, cs.semester, cs.year
        FROM "ClassSection" cs
        JOIN "Course" c ON c.course_id = cs.course_id
        WHERE cs.teacher_id = %s
        ORDER BY c.course_code, cs.year DESC, cs.semester, cs.section_number;
        """,
        (teacher_id,),
    )
except Exception as error:  # noqa: BLE001
    st.error(friendly_error(error))
    st.stop()

if not classes:
    st.info("Create a class before adding student users.")
    st.stop()

with st.form("create_student_account_form", clear_on_submit=True):
    class_section = st.selectbox(
        "Class section",
        classes,
        format_func=lambda row: (
            f"{row['course_code']} — {row['course_name']} · "
            f"Section {row['section_number']} · {row['semester']} {row['year']}"
        ),
    )
    first_name = st.text_input("First name")
    last_name = st.text_input("Last name")
    email = st.text_input("Student email")
    password = st.text_input("Temporary password", type="password")
    confirmation = st.text_input("Confirm temporary password", type="password")
    submitted = st.form_submit_button("Create student account", type="primary")

if submitted:
    normalized_email = email.strip()
    if not all((first_name.strip(), last_name.strip(), normalized_email, password)):
        st.warning("Complete every field to create the student account.")
    elif "@" not in normalized_email or normalized_email.startswith("@") or normalized_email.endswith("@"):
        st.warning("Enter a valid email address.")
    elif len(password) < PASSWORD_MIN_LENGTH:
        st.warning(
            f"Use a temporary password with at least {PASSWORD_MIN_LENGTH} characters."
        )
    elif password != confirmation:
        st.warning("The passwords do not match.")
    else:
        try:
            student = create_student_account_for_teacher(
                first_name,
                last_name,
                normalized_email,
                password,
                teacher_id,
                class_section["class_id"],
            )
            st.success(
                f"Student account created and enrolled in the selected class "
                f"(student ID {student['student_id']})."
            )
        except ValueError as error:
            st.error(str(error))
        except Exception as error:  # noqa: BLE001
            st.error(friendly_error(error))
