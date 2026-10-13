"""S3: A student earns a badge (Read + Insert)."""
import streamlit as st

from db import query, execute, friendly_error

st.set_page_config(page_title="Badges", page_icon="🏅")
st.title("🏅 Badges")

# ---------------- SQL ----------------
STUDENTS_SQL = "SELECT student_id, name FROM student ORDER BY name;"

BADGES_SQL = "SELECT badge_id, badge_name FROM badge ORDER BY badge_name;"

EARNED_SQL = """
SELECT b.badge_name, sb.earned_at
FROM student_badge sb
JOIN badge b ON b.badge_id = sb.badge_id
WHERE sb.student_id = %s
ORDER BY sb.earned_at DESC;
"""

AWARD_SQL = """
INSERT INTO student_badge (student_id, badge_id, earned_at)
VALUES (%s, %s, NOW());
"""


def load(sql, params=None):
    try:
        return query(sql, params)
    except Exception as e:  # noqa: BLE001
        st.error(friendly_error(e))
        st.stop()


students = load(STUDENTS_SQL)
badges = load(BADGES_SQL)
if not students or not badges:
    st.info("Add students and badges first.")
    st.stop()

student = st.selectbox("Student", students, format_func=lambda s: s["name"])

st.subheader("Badges earned")
st.dataframe(load(EARNED_SQL, (student["student_id"],)), hide_index=True, use_container_width=True)

st.subheader("Award a badge")
with st.form("award_form"):
    badge = st.selectbox("Badge", badges, format_func=lambda b: b["badge_name"])
    go = st.form_submit_button("Award badge")

if go:
    try:
        execute(AWARD_SQL, (student["student_id"], badge["badge_id"]))
        st.success(f"{student['name']} earned '{badge['badge_name']}'! 🏅")
        st.rerun()
    except Exception as e:  # noqa: BLE001
        # Composite PK (student_id, badge_id) blocks duplicate awards.
        st.error(
            f"{student['name']} already has this badge."
            if "unique" in str(e).lower() or "duplicate" in str(e).lower()
            else friendly_error(e)
        )