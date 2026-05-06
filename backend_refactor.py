"""
Module 8 Student Enrollment — refactored backend.
 
Architecture
------------
EnrollmentDatabase   All SQLite operations. No validation, no business logic.
EnrollmentService    Orchestration, enrollment-key logic, summary/counting,
                     and JSON snapshot export.
main()               Thin runner that wires both classes and demonstrates
                     behavior.
 
Constants and status strings stay at module level so both classes can share
them without creating an awkward ownership dependency.
 
Run with:
    enrollment_manager.py
"""
 
from __future__ import annotations
 
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional
 
 
# ---------------------------------------------------------------------------
# Module-level constants — shared by both layers
# ---------------------------------------------------------------------------
 
DB_PATH = Path(__file__).with_name("student_enrollment_practice.db")
SNAPSHOT_PATH = Path(__file__).with_name("student_enrollment_snapshot.json")
 
STATUS_ENROLLED = "enrolled"
STATUS_UNENROLLED = "unenrolled"
 
CURRENT_STUDENT = {
    "user_id": "u100",
    "name": "Maya Patel",
    "email": "maya.patel@example.edu",
}
 
AVAILABLE_COURSE_KEYS = [
    {
        "course_id": "MISY350",
        "course_name": "Python for Business Analytics",
        "instructor": "Dr. Rivera",
        "enrollment_key": "MISY350-SPRING",
    },
    {
        "course_id": "DATA210",
        "course_name": "Data Storytelling",
        "instructor": "Prof. Morgan",
        "enrollment_key": "DATA210-SPRING",
    },
    {
        "course_id": "WEB220",
        "course_name": "Web Apps With Streamlit",
        "instructor": "Dr. Chen",
        "enrollment_key": "WEB220-SPRING",
    },
]
 
SAMPLE_ENROLLMENTS = [
    ("u100", "maya.patel@example.edu", "MISY350", STATUS_ENROLLED),
    ("u100", "maya.patel@example.edu", "DATA210", STATUS_UNENROLLED),
    ("u101", "alex@example.edu", "MISY350", STATUS_ENROLLED),
    ("u102", "blair@example.edu", "WEB220", STATUS_ENROLLED),
]
 
 
# ---------------------------------------------------------------------------
# Database layer
# ---------------------------------------------------------------------------
 
class EnrollmentDatabase:
    """
    All SQLite operations for the enrollment system.
 
    Every method either queries or mutates the database and returns raw
    data.  No validation, no business decisions, no file I/O live here.
    """
 
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
 
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
 
    def _connect(self) -> sqlite3.Connection:
        """Open and return a database connection."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection
 
    @staticmethod
    def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        """Convert a list of SQLite Row objects into plain dictionaries."""
        return [dict(row) for row in rows]
 
    # ------------------------------------------------------------------
    # Schema and seed
    # ------------------------------------------------------------------
 
    def create_tables(self) -> None:
        """Create the courses and enrollments tables if they do not exist."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    course_id       TEXT PRIMARY KEY,
                    course_name     TEXT NOT NULL,
                    instructor      TEXT NOT NULL,
                    enrollment_key  TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS enrollments (
                    enrollment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         TEXT NOT NULL,
                    email           TEXT NOT NULL,
                    course_id       TEXT NOT NULL,
                    status          TEXT NOT NULL DEFAULT 'enrolled',
                    enrolled_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, course_id),
                    FOREIGN KEY(course_id) REFERENCES courses(course_id)
                )
                """
            )
 
    def seed_sample_data(self) -> None:
        """Insert course records and sample enrollment rows."""
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO courses (
                    course_id, course_name, instructor, enrollment_key
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        course["course_id"],
                        course["course_name"],
                        course["instructor"],
                        course["enrollment_key"],
                    )
                    for course in AVAILABLE_COURSE_KEYS
                ],
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                """,
                SAMPLE_ENROLLMENTS,
            )
 
    # ------------------------------------------------------------------
    # Course queries
    # ------------------------------------------------------------------
 
    def get_available_course_keys(self) -> list[dict[str, Any]]:
        """Return all courses with their enrollment keys, ordered by course_id."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                ORDER BY course_id
                """
            ).fetchall()
        return self._rows_to_dicts(rows)
 
    def get_course_by_key(self, enrollment_key: str) -> Optional[dict[str, Any]]:
        """Return the course row matching enrollment_key, or None."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                WHERE enrollment_key = ?
                """,
                (enrollment_key.strip().upper(),),
            ).fetchone()
        return dict(row) if row else None
 
    # ------------------------------------------------------------------
    # Enrollment queries
    # ------------------------------------------------------------------
 
    def get_student_enrollments(self, user_id: str) -> list[dict[str, Any]]:
        """Return active (enrolled) courses for one student."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ? AND e.status = ?
                ORDER BY c.course_id
                """,
                (user_id, STATUS_ENROLLED),
            ).fetchall()
        return self._rows_to_dicts(rows)
 
    def get_student_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        """Return all enrollment records for one student, including unenrolled."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ?
                ORDER BY c.course_id
                """,
                (user_id,),
            ).fetchall()
        return self._rows_to_dicts(rows)
 
    def get_student_course_record(
        self,
        user_id: str,
        course_id: str,
    ) -> Optional[dict[str, Any]]:
        """Return one student's enrollment record for one course, or None."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT enrollment_id, user_id, email, course_id, status, enrolled_at
                FROM enrollments
                WHERE user_id = ? AND course_id = ?
                """,
                (user_id, course_id),
            ).fetchone()
        return dict(row) if row else None
 
    def get_all_enrollment_records(self) -> list[dict[str, Any]]:
        """Return every enrollment record joined with course details."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                ORDER BY e.user_id, e.course_id
                """
            ).fetchall()
        return self._rows_to_dicts(rows)
 
    # ------------------------------------------------------------------
    # Enrollment mutations
    # ------------------------------------------------------------------
 
    def insert_or_update_enrollment(
        self,
        user_id: str,
        email: str,
        course_id: str,
        status: str,
    ) -> None:
        """
        Insert a new enrollment row, or update email/status/timestamp if
        a record for (user_id, course_id) already exists.
        """
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, course_id)
                DO UPDATE SET
                    email       = excluded.email,
                    status      = excluded.status,
                    enrolled_at = CURRENT_TIMESTAMP
                """,
                (user_id, email, course_id, status),
            )
 
    def update_enrollment_status(
        self,
        user_id: str,
        course_id: str,
        status: str,
    ) -> bool:
        """
        Update the status field for one enrollment row.
        Returns True if a row was affected, False otherwise.
        """
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE enrollments
                SET status = ?
                WHERE user_id = ? AND course_id = ?
                """,
                (status, user_id, course_id),
            )
        return cursor.rowcount > 0
 
 
# ---------------------------------------------------------------------------
# Service layer
# ---------------------------------------------------------------------------
 
class EnrollmentService:
    """
    Business logic and orchestration for the enrollment system.
 
    All enrollment-key validation, summary counting, and JSON export live
    here.  Database access happens exclusively through self.db.
    """
 
    def __init__(self, db: EnrollmentDatabase) -> None:
        self.db = db
 
    # ------------------------------------------------------------------
    # Enrollment actions
    # ------------------------------------------------------------------
 
    def enroll_student(
        self,
        user_id: str,
        email: str,
        enrollment_key: str,
    ) -> Optional[dict[str, Any]]:
        """
        Enroll or reactivate a student using an enrollment key.
 
        Validates inputs, verifies the key maps to a real course, writes
        the enrollment record, and returns the saved record.
        Returns None if any validation step fails.
        """
        # Input validation — business rule, belongs in the service layer
        if not user_id or not email or "@" not in email or not enrollment_key:
            return None
 
        # Enrollment-key logic — verify the key exists
        course = self.db.get_course_by_key(enrollment_key)
        if not course:
            return None
 
        # Write the record through the database layer
        self.db.insert_or_update_enrollment(
            user_id,
            email,
            course["course_id"],
            STATUS_ENROLLED,
        )
 
        # Return the saved record so callers get confirmation
        return self.db.get_student_course_record(user_id, course["course_id"])
 
    def unenroll_student(self, user_id: str, course_id: str) -> bool:
        """
        Soft-unenroll a student by setting status to unenrolled.
 
        Validates inputs and delegates the status update to the database
        layer.  The row is never deleted.
        Returns True if a row was updated, False otherwise.
        """
        # Input validation — business rule, belongs in the service layer
        if not user_id or not course_id:
            return False
 
        return self.db.update_enrollment_status(
            user_id,
            course_id,
            STATUS_UNENROLLED,
        )
 
    # ------------------------------------------------------------------
    # Summary and reporting
    # ------------------------------------------------------------------
 
    def get_student_summary(self, user_id: str) -> dict[str, int]:
        """
        Return enrollment counts for one student.
 
        Counting logic lives here in the service layer; raw records come
        from the database layer.
        """
        summary = {
            "total_records": 0,
            STATUS_ENROLLED: 0,
            STATUS_UNENROLLED: 0,
        }
 
        for record in self.db.get_student_enrollment_history(user_id):
            summary["total_records"] += 1
            status = record["status"]
            if status in summary:
                summary[status] += 1
 
        return summary
 
    def export_database_snapshot(self, path: Path = SNAPSHOT_PATH) -> None:
        """
        Write seeded database content to a JSON file.
 
        Assembles data from the database layer and handles file I/O.
        Useful for inspecting the seeded state without opening SQLite.
        """
        snapshot = {
            "current_student": CURRENT_STUDENT,
            "available_course_keys": self.db.get_available_course_keys(),
            "enrollment_table": self.db.get_all_enrollment_records(),
        }
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
 
 
# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
 
def main() -> None:
    """Wire both classes and demonstrate enrollment behavior."""
    db = EnrollmentDatabase()
    service = EnrollmentService(db)
 
    db.create_tables()
    db.seed_sample_data()
 
    user_id = CURRENT_STUDENT["user_id"]
    email = CURRENT_STUDENT["email"]
 
    print("Current student:")
    print(CURRENT_STUDENT)
 
    print("\nAvailable enrollment keys:")
    print(db.get_available_course_keys())
 
    print("\nInitial enrolled classes:")
    print(db.get_student_enrollments(user_id))
 
    print("\nStudent enters key DATA210-SPRING:")
    print(service.enroll_student(user_id, email, "DATA210-SPRING"))
 
    print("\nUpdated enrolled classes:")
    print(db.get_student_enrollments(user_id))
 
    print("\nStudent summary:")
    print(service.get_student_summary(user_id))
 
    service.export_database_snapshot()
    print(f"\nDatabase snapshot written to: {SNAPSHOT_PATH}")
 
 
if __name__ == "__main__":
    main()