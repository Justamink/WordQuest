"""Account creation and authentication UI for WordQuest."""
import base64
import hashlib
import hmac
import secrets

import streamlit as st

from db import get_conn, query, friendly_error

SCRYPT_N = 2**14 #CPU/Memory cost parameter
SCRYPT_R = 8 #block size parameter
SCRYPT_P = 1 #parallelization Parameter
PASSWORD_MIN_LENGTH = 6

#encrypt the password to be safe
def hash_password(password):
    #Scrypt salt encryption is a secure method for storing passwords
    #Scrypt: A password-based key derivation function that is intentionally memory-hard and computationally expensive
    #Salt: A string of random data added to a user's password before it is run through the scrypt algorithm

    #create a password
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=32, #derivation key length
    )
    return "scrypt${}${}${}${}${}".format(
        SCRYPT_N,
        SCRYPT_R,
        SCRYPT_P,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password, encoded_hash):
    """Verify an encoded scrypt hash without leaking comparison timing."""
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded_hash.split("$", 5) #variables retrieved from encoded_hash
        
        if algorithm != "scrypt":
            return False

        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def _login(email, password):
    sql = """
    SELECT a.account_id, a.email, a.password_hash, a.role,
           a.student_id, a.teacher_id,
           COALESCE(s.first_name, t.first_name) AS first_name,
           COALESCE(s.last_name, t.last_name) AS last_name
    FROM "Account" a
    LEFT JOIN "Student" s ON s.student_id = a.student_id
    LEFT JOIN "Teacher" t ON t.teacher_id = a.teacher_id
    WHERE lower(a.email) = lower(%s);
    """
    with get_conn() as conn:
        row = conn.execute(sql, (email.strip(),)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return {key: value for key, value in row.items() if key != "password_hash"}


def _create_account(
    first_name,
    last_name,
    email,
    password,
    role,
    *,
    class_id=None,
    class_teacher_id=None,
):
    """Create a profile and its login account atomically."""
    email = email.strip().lower()
    first_name = first_name.strip()
    last_name = last_name.strip()
    password_hash = hash_password(password)

    with get_conn() as conn:
        if class_id is not None:
            if role != "student" or class_teacher_id is None:
                raise ValueError("Only a student account can be assigned to a class.")
            owned_class = conn.execute(
                'SELECT 1 FROM "ClassSection" WHERE class_id = %s AND teacher_id = %s;',
                (class_id, class_teacher_id),
            ).fetchone()
            if not owned_class:
                raise ValueError("That class is not assigned to your teacher account.")

        existing = conn.execute(
            """
            SELECT EXISTS (SELECT 1 FROM "Account" WHERE lower(email) = %s)
                OR EXISTS (SELECT 1 FROM "Student" WHERE lower(email) = %s)
                OR EXISTS (SELECT 1 FROM "Teacher" WHERE lower(email) = %s)
                AS email_exists;
            """,
            (email, email, email),
        ).fetchone()["email_exists"]
        if existing:
            raise ValueError("An account or profile already uses that email address.")

        if role == "student":
            profile = conn.execute(
                """
                INSERT INTO "Student" (first_name, last_name, email, created_at)
                VALUES (%s, %s, %s, CURRENT_DATE)
                RETURNING student_id;
                """,
                (first_name, last_name, email),
            ).fetchone()
            student_id, teacher_id = profile["student_id"], None
        else:
            profile = conn.execute(
                """
                INSERT INTO "Teacher" (first_name, last_name, email)
                VALUES (%s, %s, %s)
                RETURNING teacher_id;
                """,
                (first_name, last_name, email),
            ).fetchone()
            student_id, teacher_id = None, profile["teacher_id"]

        account = conn.execute(
            """
            INSERT INTO "Account"
                (email, password_hash, role, student_id, teacher_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING account_id;
            """,
            (email, password_hash, role, student_id, teacher_id),
        ).fetchone()

        if class_id is not None:
            conn.execute(
                """
                INSERT INTO "Enrollment"
                    (student_id, class_id, enrollment_date, status)
                VALUES (%s, %s, CURRENT_DATE, 'active');
                """,
                (student_id, class_id),
            )

    return {
        "account_id": account["account_id"],
        "email": email,
        "role": role,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "first_name": first_name,
        "last_name": last_name,
    }


def create_student_account_for_teacher(
    first_name, last_name, email, password, teacher_id, class_id
):
    """Create a student account and enroll them in the teacher's own class."""
    return _create_account(
        first_name,
        last_name,
        email,
        password,
        "student",
        class_id=class_id,
        class_teacher_id=teacher_id,
    )


#visible when user isn't logged in (needs to log in or sign up)
def _render_logged_out():
    st.title("🧭 WordQuest")
    st.caption("Sign in to practice English or manage course content.")
    login_tab, signup_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            if not email.strip() or not password:
                st.warning("Enter your email address and password.")
            else:
                try:
                    account = _login(email, password)
                    if account is None:
                        st.error("The email address or password is incorrect.")
                    else:
                        st.session_state["account"] = account
                        st.rerun()
                except Exception as error:  # noqa: BLE001
                    st.error(friendly_error(error))

    with signup_tab:
        with st.form("signup_form"):
            role = st.selectbox("Account type", ["student", "teacher"])
            first_name = st.text_input("First name")
            last_name = st.text_input("Last name")
            email = st.text_input("Email address", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirmation = st.text_input(
                "Confirm password", type="password", key="signup_password_confirm"
            )
            submitted = st.form_submit_button("Create account", type="primary")

        if submitted:
            if not all((first_name.strip(), last_name.strip(), email.strip(), password)):
                st.warning("Complete every field to create an account.")
            elif "@" not in email or email.startswith("@") or email.endswith("@"):
                st.warning("Enter a valid email address.")
            elif len(password) < PASSWORD_MIN_LENGTH:
                st.warning(f"Use a password with at least {PASSWORD_MIN_LENGTH} characters.")
            elif password != confirmation:
                st.warning("The passwords do not match.")
            else:
                try:
                    st.session_state["account"] = _create_account(
                        first_name, last_name, email, password, role
                    )
                    st.success("Account created. You are now logged in.")
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
                except Exception as error:  # noqa: BLE001
                    st.error(friendly_error(error))

#used to change passwords and log out
def _render_account_controls():
    account = st.session_state["account"]
    with st.sidebar:
        st.caption(f"Signed in as **{account['first_name']} {account['last_name']}**")
        st.caption(f"{account['role'].title()} · {account['email']}")
        if st.button("Log out", use_container_width=True):
            st.session_state.pop("account", None)
            st.session_state.pop("current_student_id", None)
            st.rerun()

        with st.expander("Update password"):
            with st.form("password_update_form"):
                current = st.text_input("Current password", type="password")
                new = st.text_input("New password", type="password")
                confirm = st.text_input("Confirm new password", type="password")
                submitted = st.form_submit_button("Save password")

            if submitted:
                if not current or not new or not confirm:
                    st.warning("Complete every password field.")
                elif len(new) < PASSWORD_MIN_LENGTH:
                    st.warning(f"Use a password with at least {PASSWORD_MIN_LENGTH} characters.")
                elif new != confirm:
                    st.warning("The new passwords do not match.")
                else:
                    try:
                        with get_conn() as conn:
                            row = conn.execute(
                                'SELECT password_hash FROM "Account" WHERE account_id = %s;',
                                (account["account_id"],),
                            ).fetchone()
                            if not row or not verify_password(current, row["password_hash"]):
                                st.error("The current password is incorrect.")
                            else:
                                conn.execute(
                                    'UPDATE "Account" SET password_hash = %s WHERE account_id = %s;',
                                    (hash_password(new), account["account_id"]),
                                )
                                st.success("Password updated.")
                    except Exception as error:  # noqa: BLE001
                        st.error(friendly_error(error))

#a newly registered student can join a class to access the class's content
def _render_student_class_selection(account):
    """Let a newly registered student choose a teacher's course section."""
    st.header("Choose your teacher and course")
    st.caption(
        "Your account is ready. Select a teacher and one of their course "
        "sections to finish setting up your student account."
    )
    try:
        teachers = query(
            """
            SELECT DISTINCT t.teacher_id, t.first_name, t.last_name
            FROM "Teacher" t
            JOIN "ClassSection" cs ON cs.teacher_id = t.teacher_id
            JOIN "Course" c ON c.course_id = cs.course_id
            ORDER BY t.last_name, t.first_name;
            """
        )
    except Exception as error:  # noqa: BLE001
        st.error(friendly_error(error))
        return

    if not teachers:
        st.info("No teachers have course sections available yet. Try again later.")
        return

    teachers_by_id = {row["teacher_id"]: row for row in teachers}
    teacher_id = st.selectbox(
        "Teacher",
        list(teachers_by_id),
        format_func=lambda tid: (
            f"{teachers_by_id[tid]['first_name']} {teachers_by_id[tid]['last_name']}"
        ),
        key="enrollment_teacher_id",
    )
    try:
        sections = query(
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
        return

    if not sections:
        st.info("This teacher has no available course sections yet.")
        return

    section = st.selectbox(
        "Course section",
        sections,
        format_func=lambda row: (
            f"{row['course_code']} — {row['course_name']} · "
            f"Section {row['section_number']} · {row['semester']} {row['year']}"
        ),
        key="enrollment_class_id",
    )
    if st.button("Join this class", type="primary"):
        try:
            with get_conn() as conn:
                enrollment = conn.execute(
                    """
                    INSERT INTO "Enrollment"
                        (student_id, class_id, enrollment_date, status)
                    SELECT %s, cs.class_id, CURRENT_DATE, 'active'
                    FROM "ClassSection" cs
                    WHERE cs.class_id = %s AND cs.teacher_id = %s
                    ON CONFLICT (student_id, class_id) DO UPDATE
                        SET status = 'active'
                    RETURNING enrollment_id;
                    """,
                    (account["student_id"], section["class_id"], teacher_id),
                ).fetchone()
            if enrollment:
                st.success("You joined the class.")
                st.rerun()
            st.error("That course section is no longer available.")
        except Exception as error:  # noqa: BLE001
            st.error(friendly_error(error))


def require_login():
    """Render authentication controls and return whether a user is signed in."""
    if "account" not in st.session_state:
        _render_logged_out()
        return False
    _render_account_controls()
    account = st.session_state["account"]
    if account["role"] == "student":
        try:
            enrollment = query(
                """
                SELECT EXISTS (
                    SELECT 1 FROM "Enrollment"
                    WHERE student_id = %s AND status = 'active'
                ) AS enrolled;
                """,
                (account["student_id"],),
            )[0]["enrolled"]
        except Exception as error:  # noqa: BLE001
            st.error(friendly_error(error))
            return False
        if not enrollment:
            _render_student_class_selection(account)
            return False
    return True


def require_role(*roles):
    """Stop a page unless its session belongs to one of the allowed roles."""
    if not require_login():
        st.stop()
    account = st.session_state.get("account")
    if not account or account.get("role") not in roles:
        st.error("Your account does not have permission to view this page.")
        st.stop()
    return account
