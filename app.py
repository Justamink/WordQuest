"""Role-aware navigation for WordQuest."""
import streamlit as st

from auth import _render_logged_out

st.set_page_config(page_title="WordQuest", page_icon="🧭", layout="wide")

account = st.session_state.get("account")
if not account:
    _render_logged_out()
    st.stop()

if account.get("role") == "student":
    pages = {
        "Student": [
            st.Page("pages/0_Home.py", title="Home", icon="🏠", default=True),
            st.Page("pages/1_Practice.py", title="Practice", icon="📝"),
            st.Page("pages/3_Badges.py", title="Badges", icon="🏅"),
        ]
    }
elif account.get("role") == "teacher":
    pages = {
        "Teacher": [
            st.Page(
                "pages/6_Manage_Classes.py",
                title="Manage Classes",
                icon="🎓",
                default=True,
            ),
            st.Page("pages/8_Create_Student.py", title="Create Student", icon="👩‍🎓"),
            st.Page("pages/7_Manage_Units.py", title="Manage Units", icon="📚"),
            st.Page("pages/2_Add_Exercise.py", title="Add Exercise", icon="➕"),
            st.Page("pages/4_Grade_Answers.py", title="Grade Answers", icon="✅"),
            st.Page("pages/5_Manage_Exercises.py", title="Manage Exercises", icon="🗂️"),
        ]
    }
else:
    st.error("This account has an invalid role. Please log out and sign in again.")
    st.stop()

navigation = st.navigation(pages, position="sidebar")
navigation.run()
