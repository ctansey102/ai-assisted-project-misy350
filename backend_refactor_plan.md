Layered OOP Refactor Plan
Target Architecture
Two classes with a clean dependency direction:
ServiceLayer  →  DatabaseLayer  →  SQLite
ServiceLayer owns DatabaseLayer. Nothing flows the other direction.

Constants and Config
Keep as module-level, not inside either class:

DB_PATH
SNAPSHOT_PATH
STATUS_ENROLLED
STATUS_UNENROLLED
CURRENT_STUDENT
AVAILABLE_COURSE_KEYS
SAMPLE_ENROLLMENTS

Rationale: both classes depend on the status constants, and the seed data and paths are configuration — not behavior. Putting them in a class would create an awkward ownership question. Leave them where they are.

Class 1: EnrollmentDatabase
Responsibility: All SQLite operations. No validation, no business decisions, no file I/O.
Constructor __init__:

Accept db_path as a parameter with DB_PATH as the default
Store it as self.db_path
This eliminates the implicit global dependency in connect()

Methods to move in directly (minimal change needed):

connect() → becomes self._connect(), uses self.db_path instead of the global
create_tables()
seed_sample_data()
rows_to_dicts() → can become a static method since it touches no state
get_available_course_keys()
get_course_by_key()
get_student_enrollments()
get_student_enrollment_history()
get_student_course_record()
get_all_enrollment_records()

Methods to receive split pieces from mixed functions:

insert_or_update_enrollment(user_id, email, course_id, status) — the raw INSERT from enroll_with_key
update_enrollment_status(user_id, course_id, status) — the raw UPDATE from soft_unenroll_student

What stays out:

Input validation
Business decisions like "is this key valid?"
File I/O
Snapshot assembly

Class 2: EnrollmentService
Responsibility: Business logic, orchestration, and output. Talks to the database only through EnrollmentDatabase.
Constructor __init__:

Accept a db parameter of type EnrollmentDatabase
Store it as self.db
This makes the dependency explicit and testable

Methods to move in directly (minimal change needed):

get_student_summary() → calls self.db.get_student_enrollment_history()
export_database_snapshot() → calls multiple self.db methods, writes JSON

Methods assembled from the split mixed functions:
enroll_student(user_id, email, enrollment_key):

Input validation lives here (not in the database layer)
Calls self.db.get_course_by_key() to verify the key exists
Calls self.db.insert_or_update_enrollment() to write the record
Calls self.db.get_student_course_record() to return the result
All four steps of the original enroll_with_key are now explicit and each lives in the right layer

unenroll_student(user_id, course_id):

Input validation lives here
Calls self.db.update_enrollment_status() to do the actual UPDATE
Returns the boolean result

Order of Operations for Implementation

Create EnrollmentDatabase and move all pure DB functions in
Verify main() still runs with direct db. calls
Extract the two new split methods (insert_or_update_enrollment, update_enrollment_status)
Create EnrollmentService with self.db
Move get_student_summary and export_database_snapshot into service
Implement enroll_student and unenroll_student using the split pieces
Update main() to wire both classes and run through service
Delete the old module-level functions
