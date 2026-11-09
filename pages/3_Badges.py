"""A student views their earned badges."""
import streamlit as st

from auth import require_role
from db import query, friendly_error

st.set_page_config(page_title="Badges", page_icon="🏅")
st.title("🏅 My Badges")
account = require_role("student")

EARNED_SQL = """
SELECT b.name AS badge_name, b.description, sb.earned_at
FROM "StudentBadge" sb
JOIN "Badge" b ON b.badge_id = sb.badge_id
WHERE sb.student_id = %s
ORDER BY sb.earned_at DESC, b.name;
"""

try:
    badges = query(EARNED_SQL, (account["student_id"],))
except Exception as error:  # noqa: BLE001
    st.error(friendly_error(error))
    st.stop()

if badges:
    st.dataframe(badges, hide_index=True, use_container_width=True)
else:
    st.info("You haven't earned any badges yet. Keep practicing!")
