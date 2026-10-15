"""WordQuest home page: student dashboard + connection status.

Run with:  streamlit run app.py
"""
import streamlit as st

from db import query, friendly_error

st.set_page_config(page_title="WordQuest", page_icon="🧭", layout="wide")

# ---------------- SQL ----------------
STUDENTS_SQL = """
SELECT student_id, first_name, last_name,
       first_name || ' ' || last_name AS name
FROM "Student"
ORDER BY last_name, first_name;
"""

STATS_SQL = """
SELECT COUNT(*) AS attempts,
       COUNT(*) FILTER (WHERE is_correct) AS correct,
       COUNT(DISTINCT exercise_id) AS exercises_tried
FROM "StudentProgress"
WHERE student_id = %s;
"""

# Points from exercises answered correctly at least once (counted once each).
POINTS_SQL = """
SELECT COALESCE(SUM(e.points), 0) AS points
FROM "Exercise" e
WHERE e.exercise_id IN (
    SELECT exercise_id
    FROM "StudentProgress"
    WHERE student_id = %s AND is_correct
);
"""

STREAK_SQL = """
SELECT current_streak, longest_streak, last_practice_day
FROM "Streak"
WHERE student_id = %s;
"""

BADGES_SQL = """
SELECT b.name, b.description, b.badge_type, sb.earned_at,
       t.name AS topic_name
FROM "StudentBadge" sb
JOIN "Badge" b ON b.badge_id = sb.badge_id
LEFT JOIN "Topic" t ON t.topic_id = b.topic_id
WHERE sb.student_id = %s
ORDER BY sb.earned_at DESC, b.name;
"""

BADGE_TOTAL_SQL = """
SELECT COUNT(*) AS n FROM "Badge";
"""

RECENT_TOPICS_SQL = """
SELECT t.name AS topic_name, c.course_code,
       COUNT(*) AS attempts,
       COUNT(*) FILTER (WHERE sp.is_correct) AS correct,
       MAX(sp.answered_at) AS last_practiced
FROM "StudentProgress" sp
JOIN "Exercise" e ON e.exercise_id = sp.exercise_id
JOIN "PracticeUnit" u ON u.unit_id = e.unit_id
JOIN "Topic" t ON t.topic_id = u.topic_id
JOIN "ClassSection" cs ON cs.class_id = t.class_id
JOIN "Course" c ON c.course_id = cs.course_id
WHERE sp.student_id = %s
GROUP BY t.topic_id, t.name, c.course_code
ORDER BY last_practiced DESC
LIMIT 5;
"""

RECENT_ATTEMPTS_SQL = """
SELECT sp.answered_at, t.name AS topic_name, e.question_text,
       sp.submitted_answer, sp.is_correct
FROM "StudentProgress" sp
JOIN "Exercise" e ON e.exercise_id = sp.exercise_id
JOIN "PracticeUnit" u ON u.unit_id = e.unit_id
JOIN "Topic" t ON t.topic_id = u.topic_id
WHERE sp.student_id = %s
ORDER BY sp.answered_at DESC
LIMIT 8;
"""

CLASSES_SQL = """
SELECT c.course_code, c.course_name, cs.section_number,
       cs.semester, cs.year,
       te.first_name || ' ' || te.last_name AS teacher,
       en.status
FROM "Enrollment" en
JOIN "ClassSection" cs ON cs.class_id = en.class_id
JOIN "Course" c ON c.course_id = cs.course_id
JOIN "Teacher" te ON te.teacher_id = cs.teacher_id
WHERE en.student_id = %s
ORDER BY cs.year DESC, cs.semester, c.course_code;
"""


def load(sql, params=None):
    try:
        return query(sql, params)
    except Exception as e:  # noqa: BLE001
        st.error(friendly_error(e))
        st.stop()


def short(text, n):
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


# ---------------- Connection check ----------------
try:
    info = query("SELECT current_database() AS db, version() AS version;")[0]
except Exception as e:  # noqa: BLE001
    st.error(friendly_error(e))
    st.stop()

# ---------------- Header + "log in" selector ----------------
students = load(STUDENTS_SQL)

head_left, head_right = st.columns([3, 2], vertical_alignment="bottom")

with head_left:
    st.title("🧭 WordQuest")
    st.caption(
        "Practice English with topic-based exercises, earn badges, and give "
        "teachers insight into where students need more practice."
    )

if not students:
    st.info("No students in the database yet.")
    st.stop()

by_id = {s["student_id"]: s for s in students}
ids = list(by_id)
if st.session_state.get("current_student_id") not in by_id:
    st.session_state["current_student_id"] = ids[0]

with head_right:
    student_id = st.selectbox(
        "Logged in as",
        ids,
        key="current_student_id",
        format_func=lambda i: by_id[i]["name"],
    )

student = by_id[student_id]
st.subheader(f"Welcome back, {student['first_name']}! 👋")

# ---------------- Load this student's data ----------------
stats = load(STATS_SQL, (student_id,))[0]
points = load(POINTS_SQL, (student_id,))[0]["points"]
streak_rows = load(STREAK_SQL, (student_id,))
badges = load(BADGES_SQL, (student_id,))
badge_total = load(BADGE_TOTAL_SQL)[0]["n"]
recent_topics = load(RECENT_TOPICS_SQL, (student_id,))
recent_attempts = load(RECENT_ATTEMPTS_SQL, (student_id,))
classes = load(CLASSES_SQL, (student_id,))

streak = streak_rows[0] if streak_rows else None
attempts = stats["attempts"]
accuracy = round(100 * stats["correct"] / attempts) if attempts else None

# ---------------- Metric tiles ----------------
tiles = [
    (
        "🔥 Current streak",
        f"{streak['current_streak']} day(s)" if streak else "0 days",
        None,
    ),
    (
        "🏆 Longest streak",
        f"{streak['longest_streak']} day(s)" if streak else "0 days",
        None,
    ),
    ("🏅 Badges earned", f"{len(badges)} of {badge_total}", None),
    (
        "✅ Accuracy",
        f"{accuracy}%" if accuracy is not None else "—",
        f"{stats['correct']} of {attempts} attempts correct"
        if attempts else None,
    ),
    (
        "⭐ Points earned",
        f"{points}",
        "Counted once per exercise answered correctly",
    ),
]

for col, (label, value, hint) in zip(st.columns(len(tiles)), tiles):
    with col:
        with st.container(border=True):
            st.metric(label, value, help=hint)

if streak:
    st.caption(f"Last practiced on {streak['last_practice_day']:%b %d, %Y}.")

# ---------------- Main body ----------------
left, right = st.columns([3, 2])

with left:
    st.markdown("#### 📚 Recently practiced topics")
    if not recent_topics:
        st.info("No practice yet. Open the Practice page to get started!")
    for t in recent_topics:
        pct = round(100 * t["correct"] / t["attempts"]) if t["attempts"] else 0
        with st.container(border=True):
            st.markdown(f"**{t['topic_name']}** · {t['course_code']}")
            st.progress(
                pct / 100,
                text=f"{pct}% correct ({t['correct']} of {t['attempts']})",
            )
            st.caption(f"Last practiced {t['last_practiced']:%b %d, %Y %I:%M %p}")

    st.markdown("#### 📝 Recent attempts")
    if not recent_attempts:
        st.caption("Your latest answers will show up here.")
    else:
        st.dataframe(
            [
                {
                    "When": a["answered_at"].strftime("%b %d, %I:%M %p"),
                    "Topic": a["topic_name"],
                    "Question": short(a["question_text"], 60),
                    "Your answer": short(a["submitted_answer"], 40),
                    "Result": "✅ Correct" if a["is_correct"] else "❌ Not correct",
                }
                for a in recent_attempts
            ],
            hide_index=True,
            use_container_width=True,
        )
        st.caption(
            "Free-response answers show as not correct until a teacher "
            "reviews them."
        )

with right:
    st.markdown("#### 🏅 My badges")
    if not badges:
        st.info("No badges yet. Keep practicing to earn your first one!")
    for b in badges[:6]:
        with st.container(border=True):
            st.markdown(f"🏅 **{b['name']}**")
            st.caption(b["description"])
            detail = f"Earned {b['earned_at']:%b %d, %Y}"
            if b["topic_name"]:
                detail += f" · {b['topic_name']}"
            st.caption(detail)
    if len(badges) > 6:
        st.caption(f"+ {len(badges) - 6} more badge(s) on the Badges page.")

    st.markdown("#### 🎓 My classes")
    if not classes:
        st.caption("Not enrolled in any classes yet.")
    for c in classes:
        with st.container(border=True):
            st.markdown(f"**{c['course_code']}** · {c['course_name']}")
            st.caption(
                f"Section {c['section_number']} · {c['semester']} {c['year']}"
                f" · {c['teacher']} · {c['status']}"
            )

# ---------------- Screens guide ----------------
with st.expander("Screens"):
    st.markdown(
        """
| Screen | What you can do | Scenario |
|---|---|---|
| Practice | View and answer practice questions | S1 |
| Add Exercise | Add a question (multiple choice, multi select, fill in the blank, or free response) | S2 |
| Badges | Award a badge to a student and view earned badges | Additional feature |
| Grade Answers | Review free-response answers | Additional feature |
| Manage Exercises | Search, filter, edit and delete exercises | S3 / S4 |

Use the sidebar to navigate.
"""
    )

# ---------------- Database connection ----------------
st.divider()
st.subheader("Database Connection")
st.success(f"Connected to PostgreSQL database '{info['db']}'")
st.caption(info["version"])

with st.expander("Table Row Counts"):
    TABLES = [
        "Student", "Course", "ClassSection", "Topic", "PracticeUnit",
        "Exercise", "AnswerChoice", "StudentProgress", "Badge",
        "StudentBadge",
    ]
    counts = []
    for t in TABLES:
        try:
            n = query(f'SELECT COUNT(*) AS n FROM "{t}";')[0]["n"]
            counts.append({"table": t, "rows": n})
        except Exception:  # noqa: BLE001  (table name may differ in your schema)
            counts.append({"table": t, "rows": "n/a"})
    st.dataframe(counts, hide_index=True, use_container_width=True)