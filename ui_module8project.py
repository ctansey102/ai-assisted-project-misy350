"""
Streamlit UI for the Student Enrollment System (Module 8).

Run with:
    streamlit run enrollment_app.py

Assumes backend_refactor.py is in the same directory and the database
has already been seeded (main() has been called at least once), or call
db.create_tables() + db.seed_sample_data() on first run.
"""

import streamlit as st

from backend_refactor import (
    CURRENT_STUDENT,
    EnrollmentDatabase,
    EnrollmentService,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Course Enrollment",
    page_icon="🎓",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Backend wiring — cached so instances are reused across reruns
# ---------------------------------------------------------------------------

@st.cache_resource
def get_service() -> tuple[EnrollmentDatabase, EnrollmentService]:
    db = EnrollmentDatabase()
    db.create_tables()
    db.seed_sample_data()
    return db, EnrollmentService(db)


db, service = get_service()

USER_ID = CURRENT_STUDENT["user_id"]
EMAIL   = CURRENT_STUDENT["email"]
NAME    = CURRENT_STUDENT["name"]

# ---------------------------------------------------------------------------
# Session-state initialisation (runs once per session)
# ---------------------------------------------------------------------------

def refresh_state() -> None:
    """Re-fetch mutable session state from the service/db layer."""
    st.session_state["enrolled_courses"] = db.get_student_enrollments(USER_ID)
    st.session_state["summary"]          = service.get_student_summary(USER_ID)


if "enrolled_courses" not in st.session_state:
    refresh_state()

if "last_action_msg" not in st.session_state:
    st.session_state["last_action_msg"] = None   # (text, type) or None

if "enrollment_key_input" not in st.session_state:
    st.session_state["enrollment_key_input"] = ""

# ---------------------------------------------------------------------------
# Sidebar — student profile + summary
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🎓 Student Portal")
    st.divider()

    # Profile card
    initials = "".join(w[0] for w in NAME.split())
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
          <div style="
            width:46px; height:46px; border-radius:50%;
            background:#dbeafe; color:#1d4ed8;
            display:flex; align-items:center; justify-content:center;
            font-weight:600; font-size:15px; flex-shrink:0;">
            {initials}
          </div>
          <div>
            <div style="font-weight:600; font-size:15px;">{NAME}</div>
            <div style="font-size:12px; color:gray;">{USER_ID}</div>
          </div>
        </div>
        <div style="font-size:12px; color:gray; margin-bottom:4px;">{EMAIL}</div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Summary metrics — read from session state
    summary = st.session_state["summary"]
    st.markdown("**Enrollment summary**")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total",      summary["total_records"])
    col_b.metric("Enrolled",   summary["enrolled"])
    col_c.metric("Unenrolled", summary["unenrolled"])

    st.divider()

    if st.button("🔄 Refresh", use_container_width=True):
        refresh_state()
        st.rerun()

# ---------------------------------------------------------------------------
# Main area — tabs
# ---------------------------------------------------------------------------

tab_my, tab_enroll = st.tabs(["📚 My Courses", "🔑 Enroll in a Course"])

# ── Tab 1 — My Courses ──────────────────────────────────────────────────────

with tab_my:

    # Show any action feedback at the top
    if st.session_state["last_action_msg"]:
        msg, kind = st.session_state["last_action_msg"]
        (st.success if kind == "success" else st.error)(msg)
        st.session_state["last_action_msg"] = None

    st.subheader("Active enrollments")

    enrolled = st.session_state["enrolled_courses"]

    if not enrolled:
        st.info("You are not currently enrolled in any courses.")
    else:
        col_table, col_hint = st.columns([2, 1])

        with col_table:
            # Display columns only — drop internal fields
            display_cols = ["course_id", "course_name", "instructor", "enrolled_at", "status"]
            display_rows = [{k: row[k] for k in display_cols} for row in enrolled]

            st.dataframe(
                display_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "course_id":   st.column_config.TextColumn("Course ID",   width="small"),
                    "course_name": st.column_config.TextColumn("Course name", width="medium"),
                    "instructor":  st.column_config.TextColumn("Instructor",  width="medium"),
                    "enrolled_at": st.column_config.TextColumn("Enrolled at", width="medium"),
                    "status":      st.column_config.TextColumn("Status",      width="small"),
                },
            )

        with col_hint:
            st.markdown(
                """
                **How to unenroll**

                Select a course from the dropdown below and click **Unenroll**.
                Your record is kept and marked *unenrolled* — it is never deleted.

                To re-enroll later, use the **Enroll in a Course** tab with the same key.
                """
            )

        st.divider()
        st.markdown("**Unenroll from a course**")

        # Build a label → course_id map for the selectbox
        course_options = {
            f"{row['course_id']} — {row['course_name']}": row["course_id"]
            for row in enrolled
        }

        selected_label = st.selectbox(
            "Select a course to unenroll from",
            options=list(course_options.keys()),
            index=0,
        )

        if st.button("Unenroll", type="secondary"):
            selected_course_id = course_options[selected_label]
            selected_row = next(r for r in enrolled if r["course_id"] == selected_course_id)
            success = service.unenroll_student(USER_ID, selected_course_id)
            if success:
                st.session_state["last_action_msg"] = (
                    f"You have been unenrolled from {selected_row['course_name']}.",
                    "success",
                )
            else:
                st.session_state["last_action_msg"] = (
                    f"Could not unenroll from {selected_course_id}. Please try again.",
                    "error",
                )
            refresh_state()
            st.rerun()

# ── Tab 2 — Enroll in a Course ───────────────────────────────────────────────

with tab_enroll:

    st.subheader("Enroll with an enrollment key")

    col_form, col_info = st.columns([2, 1])

    with col_form:
        enrollment_key = st.text_input(
            "Enrollment key",
            placeholder="e.g. DATA210-SPRING",
            key="enrollment_key_input",
            help="Keys are case-insensitive. Ask your instructor if you don't have one.",
        )

        if st.button("Enroll", type="primary", use_container_width=False):
            if not enrollment_key.strip():
                st.error("Please enter an enrollment key.")
            else:
                result = service.enroll_student(USER_ID, EMAIL, enrollment_key.strip())
                if result:
                    course_name = next(
                        (c["course_name"] for c in db.get_available_course_keys()
                         if c["course_id"] == result["course_id"]),
                        result["course_id"],
                    )
                    st.success(f"Successfully enrolled in **{course_name}**!")
                    refresh_state()
                else:
                    st.error(
                        "Enrollment failed. Check that the key is correct and try again."
                    )

    with col_info:
        st.markdown(
            """
            **Tips**
            - Keys look like `COURSEID-TERM` (e.g. `WEB220-SPRING`)
            - Keys are not case-sensitive
            - Re-entering a key for a course you dropped will re-enroll you
            """
        )

    st.divider()

    with st.expander("Browse available courses and their enrollment keys"):
        available = db.get_available_course_keys()
        st.dataframe(
            available,
            use_container_width=True,
            hide_index=True,
            column_config={
                "course_id":      st.column_config.TextColumn("Course ID",       width="small"),
                "course_name":    st.column_config.TextColumn("Course name",     width="medium"),
                "instructor":     st.column_config.TextColumn("Instructor",      width="medium"),
                "enrollment_key": st.column_config.TextColumn("Enrollment key",  width="medium"),
            },
        )