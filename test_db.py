"""
test_db.py — quick manual test for db.py, using fake data.

Run this with:
    python test_db.py

It will:
  1. Set up the database (safe to run even if it already exists)
  2. Save a fake student, some attendance, some marks, and a config value
  3. Read all of it back and print it
  4. Tell you clearly if anything looks wrong

If everything prints correctly, db.py is working and you can move on to
building the admin upload page. Delete this file (or leave it — it won't
interfere with anything) once you're confident the database layer works.
"""

import db

TEST_ROLL_NO = "TEST01"
TEST_EMAIL = "test.student@example.com"


def run_test():
    print("1. Initializing database...")
    db.init_db()
    print(f"   OK — database file should now exist at: {db.DB_PATH.resolve()}")

    print("\n2. Saving a fake student...")
    db.save_student(TEST_ROLL_NO, TEST_EMAIL, name="Test Student", programme="BCA")
    student = db.get_student(TEST_ROLL_NO)
    print(f"   Saved & read back: {student}")
    assert student is not None, "FAILED: student was not saved"
    assert student["email"] == TEST_EMAIL, "FAILED: email did not match"

    print("\n3. Checking email -> roll number lookup...")
    looked_up_roll_no = db.get_roll_no_by_email(TEST_EMAIL)
    print(f"   Looked up roll_no for {TEST_EMAIL}: {looked_up_roll_no}")
    assert looked_up_roll_no == TEST_ROLL_NO, "FAILED: email lookup did not return correct roll_no"

    print("\n4. Saving fake attendance for two subjects...")
    db.save_attendance(TEST_ROLL_NO, "Business Communication", held=40, attended=32)
    db.save_attendance(TEST_ROLL_NO, "Marketing Management", held=38, attended=20)
    attendance = db.get_attendance(TEST_ROLL_NO)
    print(f"   Read back: {attendance}")
    assert len(attendance) == 2, f"FAILED: expected 2 attendance rows, got {len(attendance)}"

    print("\n5. Saving fake marks...")
    db.save_marks(TEST_ROLL_NO, "Business Communication", internal_marks=22, internal_max=30)
    marks = db.get_marks(TEST_ROLL_NO)
    print(f"   Read back: {marks}")
    assert len(marks) == 1, f"FAILED: expected 1 marks row, got {len(marks)}"

    print("\n6. Setting and reading a config value (eligibility threshold)...")
    db.set_config("min_attendance_pct", "75")
    threshold = db.get_config("min_attendance_pct", default="not set")
    print(f"   min_attendance_pct = {threshold}")
    assert threshold == "75", "FAILED: config value did not round-trip correctly"

    print("\n7. Overwriting attendance to check updates work (not duplicate rows)...")
    db.save_attendance(TEST_ROLL_NO, "Business Communication", held=42, attended=34)
    attendance_after_update = db.get_attendance(TEST_ROLL_NO)
    print(f"   Read back after update: {attendance_after_update}")
    assert len(attendance_after_update) == 2, "FAILED: update created a duplicate row instead of overwriting"

    print("\n✅ ALL CHECKS PASSED — db.py is working correctly.")
    print("   You can now move on to building the admin upload page.")


if __name__ == "__main__":
    run_test()