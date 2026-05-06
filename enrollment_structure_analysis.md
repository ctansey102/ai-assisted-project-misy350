Your method map is solid and shows good instincts. Here are the places worth examining more carefully:

Disagreements or Tensions Worth Discussing
seed_sample_data as Single Task
You marked this Single Task, but it inserts into both courses and enrollments in one function. That's the same mixed-task concern as create_tables, which you correctly marked Mixed (Same Layer). These two are symmetric — both touch two tables.
get_all_enrollment_records as Service
This is a straightforward SELECT with a JOIN — no business logic, no orchestration. It looks more like a Database function than a Service one. It's very similar in character to get_student_enrollment_history, which you put in Database.
soft_unenroll_student as Reads Global State
It doesn't actually read any global state — it only takes user_id and course_id as parameters and runs an UPDATE. The state behavior is closer to Requires Passing State, same as get_student_enrollments.
main runner as Self-Contained / Constants/Config
Main actually orchestrates quite a bit — it calls create_tables, seed_sample_data, enroll_with_key, get_student_enrollments, get_student_summary, and export_database_snapshot. That's not really self-contained or config-like. It's closer to a runner that Reads Global State (CURRENT_STUDENT) and coordinates across layers.

Structural Issues the Map Reveals
enroll_with_key is doing four jobs
You correctly flagged it as Cross Layer. Specifically: input validation (service), course lookup (database), enrollment write (database), and then a re-fetch to return the result (database). When you split this, the service layer should own the validation and orchestration, and the database layer should own the two SQL operations.
SNAPSHOT_PATH and file I/O sitting in Database
export_database_snapshot writes to disk, which is neither a database concern nor a pure service concern — it's closer to an infrastructure or output concern. Grouping SNAPSHOT_PATH with DB constants is a mild category mismatch worth noticing.
Global state is doing a lot of quiet work
CURRENT_STUDENT, DB_PATH, AVAILABLE_COURSE_KEYS, and SAMPLE_ENROLLMENTS are all module-level. Some functions pull from these implicitly, others take parameters explicitly. That inconsistency is the root cause of your Reads Global State vs. Requires Passing State split — and it's one of the main things a class structure would clean up by moving that state into __init__.
STATUS_ENROLLED / STATUS_UNENROLLED ownership is ambiguous
You put these in Database, but they're used in service-layer logic too (get_student_summary checks status in summary). They're really shared constants that both layers depend on, which suggests they belong in a shared config or constants location rather than inside either class.

The one thing your map does really well is consistently identifying Cross Layer as "Needs Splitting" rather than just assigning it to whichever layer dominates. That's the right call — the split is more important than which layer wins.