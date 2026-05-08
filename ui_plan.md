Here's the full UI plan, followed by a mockup of the interface:
Overall layout: A sidebar holds the logged-in student's profile info and navigation. The main content area has two tabs — "My Courses" and "Enroll in a Course."
Sidebar — static, always visible:

Student avatar with initials, name, email, and user ID pulled from CURRENT_STUDENT
A summary widget showing counts from service.get_student_summary(user_id) — total records, enrolled, and unenrolled — stored in st.session_state["summary"]
A "Refresh" button that re-fetches the summary and updates session state

Tab 1 — My courses:

Two st.columns for layout: a wide left column with an st.dataframe of the student's currently enrolled courses (from db.get_student_enrollments(user_id), stored in st.session_state["enrolled_courses"]), and a narrow right column with instructions/status messages
Below the dataframe, each row has a "Unenroll" button (keyed by course_id) that calls service.unenroll_student(user_id, course_id), then clears and re-fetches st.session_state["enrolled_courses"] and st.session_state["summary"]

Tab 2 — Enroll in a course:

st.text_input for the enrollment key, stored to st.session_state["enrollment_key_input"]
An "Enroll" button that calls service.enroll_student(user_id, email, key) — on success, shows st.success() with the course name; on failure, shows st.error()
On success, invalidates and re-fetches st.session_state["enrolled_courses"] and st.session_state["summary"]
An expandable st.expander("Browse available courses") with an st.dataframe of db.get_available_course_keys() so students can look up keys