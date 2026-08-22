import json, pathlib
pathlib.Path("data").mkdir(exist_ok=True)
calendar = [{"date":"2026-08-18","title":"Independence Day (Observed)","type":"holiday"},{"date":"2026-08-22","title":"Internal Assessment 1 - BCA Sem 1","type":"exam"},{"date":"2026-08-22","title":"Internal Assessment 1 - BBA Sem 1","type":"exam"},{"date":"2026-08-22","title":"Internal Assessment 1 - B.Com (H) Sem 1","type":"exam"},{"date":"2026-08-25","title":"Assignment Submission Deadline - DBMS (BCA)","type":"deadline"},{"date":"2026-08-27","title":"Sports Day","type":"event"},{"date":"2026-09-01","title":"Fee Payment Last Date (Sem 1)","type":"deadline"},{"date":"2026-09-05","title":"Teachers Day Celebration","type":"event"},{"date":"2026-09-10","title":"Internal Assessment 2 - All Programmes","type":"exam"},{"date":"2026-09-15","title":"Project Proposal Submission Deadline","type":"deadline"},{"date":"2026-09-16","title":"Ganesh Chaturthi Holiday","type":"holiday"},{"date":"2026-09-20","title":"Mid-Semester Break Begins","type":"holiday"},{"date":"2026-09-22","title":"Mid-Semester Break Ends","type":"holiday"},{"date":"2026-09-25","title":"Guest Lecture - Industry Expert","type":"event"},{"date":"2026-10-02","title":"Gandhi Jayanti Holiday","type":"holiday"},{"date":"2026-10-08","title":"Internal Assessment 3 - All Programmes","type":"exam"},{"date":"2026-10-12","title":"Annual Cultural Fest Day 1","type":"event"},{"date":"2026-10-13","title":"Annual Cultural Fest Day 2","type":"event"},{"date":"2026-10-20","title":"Assignment Submission Deadline - All Subjects","type":"deadline"},{"date":"2026-10-24","title":"Dussehra Holiday","type":"holiday"},{"date":"2026-11-01","title":"Practical Examination Begins","type":"exam"},{"date":"2026-11-05","title":"Practical Examination Ends","type":"exam"},{"date":"2026-11-10","title":"Diwali Holiday Begins","type":"holiday"},{"date":"2026-11-14","title":"Diwali Holiday Ends","type":"holiday"},{"date":"2026-11-20","title":"End-Semester Theory Exam Begins","type":"exam"},{"date":"2026-12-05","title":"End-Semester Theory Exam Ends","type":"exam"},{"date":"2026-12-10","title":"Result Declaration (Tentative)","type":"event"},{"date":"2026-12-15","title":"Winter Break Begins","type":"holiday"},{"date":"2027-01-03","title":"Classes Resume (Sem 2)","type":"event"}]
slots_bca_mon = [{"time":"9:00-10:00","subject":"Mathematics","room":"101","teacher":"Dr. Sharma"},{"time":"10:00-11:00","subject":"Programming in C","room":"Lab-1","teacher":"Ms. Gupta"},{"time":"11:00-12:00","subject":"DBMS","room":"102","teacher":"Dr. Verma"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Computer Networks","room":"103","teacher":"Mr. Yadav"},{"time":"14:00-15:00","subject":"Communication Skills","room":"104","teacher":"Ms. Singh"}]
slots_bca_tue = [{"time":"9:00-10:00","subject":"DBMS","room":"102","teacher":"Dr. Verma"},{"time":"10:00-11:00","subject":"Mathematics","room":"101","teacher":"Dr. Sharma"},{"time":"11:00-12:00","subject":"Programming Lab","room":"Lab-1","teacher":"Ms. Gupta"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Web Technologies","room":"105","teacher":"Mr. Kumar"},{"time":"14:00-15:00","subject":"Computer Networks","room":"103","teacher":"Mr. Yadav"}]
slots_bca_wed = [{"time":"9:00-10:00","subject":"Web Technologies","room":"105","teacher":"Mr. Kumar"},{"time":"10:00-11:00","subject":"DBMS Lab","room":"Lab-2","teacher":"Dr. Verma"},{"time":"11:00-12:00","subject":"Mathematics","room":"101","teacher":"Dr. Sharma"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Communication Skills","room":"104","teacher":"Ms. Singh"},{"time":"14:00-15:00","subject":"Programming in C","room":"Lab-1","teacher":"Ms. Gupta"}]
slots_bca_thu = [{"time":"9:00-10:00","subject":"Computer Networks","room":"103","teacher":"Mr. Yadav"},{"time":"10:00-11:00","subject":"Web Technologies","room":"105","teacher":"Mr. Kumar"},{"time":"11:00-12:00","subject":"DBMS","room":"102","teacher":"Dr. Verma"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Mathematics","room":"101","teacher":"Dr. Sharma"},{"time":"14:00-15:00","subject":"Library / Self Study","room":"Library","teacher":""}]
slots_bca_fri = [{"time":"9:00-10:00","subject":"Communication Skills","room":"104","teacher":"Ms. Singh"},{"time":"10:00-11:00","subject":"Computer Networks Lab","room":"Lab-3","teacher":"Mr. Yadav"},{"time":"11:00-12:00","subject":"Web Technologies","room":"105","teacher":"Mr. Kumar"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Programming in C","room":"Lab-1","teacher":"Ms. Gupta"},{"time":"14:00-15:00","subject":"Seminar / Activity","room":"Seminar Hall","teacher":""}]
slots_bca_sat = [{"time":"9:00-10:00","subject":"Mathematics","room":"101","teacher":"Dr. Sharma"},{"time":"10:00-11:00","subject":"DBMS","room":"102","teacher":"Dr. Verma"},{"time":"11:00-12:00","subject":"Doubt Clearing Session","room":"101","teacher":"Faculty"}]
slots_bba_mon = [{"time":"9:00-10:00","subject":"Business Communication","room":"201","teacher":"Ms. Nair"},{"time":"10:00-11:00","subject":"Principles of Management","room":"202","teacher":"Dr. Mehta"},{"time":"11:00-12:00","subject":"Business Economics","room":"203","teacher":"Dr. Joshi"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Accounting","room":"204","teacher":"Mr. Patel"},{"time":"14:00-15:00","subject":"Computer Applications","room":"Lab-4","teacher":"Ms. Rao"}]
slots_bba_tue = [{"time":"9:00-10:00","subject":"Accounting","room":"204","teacher":"Mr. Patel"},{"time":"10:00-11:00","subject":"Business Communication","room":"201","teacher":"Ms. Nair"},{"time":"11:00-12:00","subject":"Marketing Management","room":"205","teacher":"Dr. Bose"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Principles of Management","room":"202","teacher":"Dr. Mehta"},{"time":"14:00-15:00","subject":"Business Economics","room":"203","teacher":"Dr. Joshi"}]
slots_bba_wed = [{"time":"9:00-10:00","subject":"Marketing Management","room":"205","teacher":"Dr. Bose"},{"time":"10:00-11:00","subject":"Computer Applications Lab","room":"Lab-4","teacher":"Ms. Rao"},{"time":"11:00-12:00","subject":"Business Communication","room":"201","teacher":"Ms. Nair"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Accounting","room":"204","teacher":"Mr. Patel"},{"time":"14:00-15:00","subject":"Principles of Management","room":"202","teacher":"Dr. Mehta"}]
slots_bba_thu = [{"time":"9:00-10:00","subject":"Business Economics","room":"203","teacher":"Dr. Joshi"},{"time":"10:00-11:00","subject":"Marketing Management","room":"205","teacher":"Dr. Bose"},{"time":"11:00-12:00","subject":"Accounting","room":"204","teacher":"Mr. Patel"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Business Communication","room":"201","teacher":"Ms. Nair"},{"time":"14:00-15:00","subject":"Library / Self Study","room":"Library","teacher":""}]
slots_bba_fri = [{"time":"9:00-10:00","subject":"Principles of Management","room":"202","teacher":"Dr. Mehta"},{"time":"10:00-11:00","subject":"Business Economics","room":"203","teacher":"Dr. Joshi"},{"time":"11:00-12:00","subject":"Marketing Management","room":"205","teacher":"Dr. Bose"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Accounting","room":"204","teacher":"Mr. Patel"},{"time":"14:00-15:00","subject":"Seminar / Activity","room":"Seminar Hall","teacher":""}]
slots_bba_sat = [{"time":"9:00-10:00","subject":"Business Communication","room":"201","teacher":"Ms. Nair"},{"time":"10:00-11:00","subject":"Marketing Management","room":"205","teacher":"Dr. Bose"},{"time":"11:00-12:00","subject":"Doubt Clearing Session","room":"202","teacher":"Faculty"}]
slots_bc_mon = [{"time":"9:00-10:00","subject":"Financial Accounting","room":"301","teacher":"Prof. Agarwal"},{"time":"10:00-11:00","subject":"Business Law","room":"302","teacher":"Adv. Sharma"},{"time":"11:00-12:00","subject":"Economics","room":"303","teacher":"Dr. Pandey"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Statistics","room":"304","teacher":"Mr. Tiwari"},{"time":"14:00-15:00","subject":"Computer Applications","room":"Lab-4","teacher":"Ms. Rao"}]
slots_bc_tue = [{"time":"9:00-10:00","subject":"Statistics","room":"304","teacher":"Mr. Tiwari"},{"time":"10:00-11:00","subject":"Financial Accounting","room":"301","teacher":"Prof. Agarwal"},{"time":"11:00-12:00","subject":"Corporate Accounting","room":"305","teacher":"Prof. Agarwal"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Business Law","room":"302","teacher":"Adv. Sharma"},{"time":"14:00-15:00","subject":"Economics","room":"303","teacher":"Dr. Pandey"}]
slots_bc_wed = [{"time":"9:00-10:00","subject":"Corporate Accounting","room":"305","teacher":"Prof. Agarwal"},{"time":"10:00-11:00","subject":"Computer Applications Lab","room":"Lab-4","teacher":"Ms. Rao"},{"time":"11:00-12:00","subject":"Financial Accounting","room":"301","teacher":"Prof. Agarwal"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Statistics","room":"304","teacher":"Mr. Tiwari"},{"time":"14:00-15:00","subject":"Business Law","room":"302","teacher":"Adv. Sharma"}]
slots_bc_thu = [{"time":"9:00-10:00","subject":"Economics","room":"303","teacher":"Dr. Pandey"},{"time":"10:00-11:00","subject":"Corporate Accounting","room":"305","teacher":"Prof. Agarwal"},{"time":"11:00-12:00","subject":"Statistics","room":"304","teacher":"Mr. Tiwari"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Financial Accounting","room":"301","teacher":"Prof. Agarwal"},{"time":"14:00-15:00","subject":"Library / Self Study","room":"Library","teacher":""}]
slots_bc_fri = [{"time":"9:00-10:00","subject":"Business Law","room":"302","teacher":"Adv. Sharma"},{"time":"10:00-11:00","subject":"Economics","room":"303","teacher":"Dr. Pandey"},{"time":"11:00-12:00","subject":"Corporate Accounting","room":"305","teacher":"Prof. Agarwal"},{"time":"12:00-13:00","subject":"LUNCH BREAK","room":"","teacher":""},{"time":"13:00-14:00","subject":"Statistics","room":"304","teacher":"Mr. Tiwari"},{"time":"14:00-15:00","subject":"Seminar / Activity","room":"Seminar Hall","teacher":""}]
slots_bc_sat = [{"time":"9:00-10:00","subject":"Financial Accounting","room":"301","teacher":"Prof. Agarwal"},{"time":"10:00-11:00","subject":"Corporate Accounting","room":"305","teacher":"Prof. Agarwal"},{"time":"11:00-12:00","subject":"Doubt Clearing Session","room":"302","teacher":"Faculty"}]
timetable = {"BCA":{"Monday":slots_bca_mon,"Tuesday":slots_bca_tue,"Wednesday":slots_bca_wed,"Thursday":slots_bca_thu,"Friday":slots_bca_fri,"Saturday":slots_bca_sat},"BBA":{"Monday":slots_bba_mon,"Tuesday":slots_bba_tue,"Wednesday":slots_bba_wed,"Thursday":slots_bba_thu,"Friday":slots_bba_fri,"Saturday":slots_bba_sat},"B.Com (H)":{"Monday":slots_bc_mon,"Tuesday":slots_bc_tue,"Wednesday":slots_bc_wed,"Thursday":slots_bc_thu,"Friday":slots_bc_fri,"Saturday":slots_bc_sat}}
pathlib.Path("data/academic_calendar.json").write_text(json.dumps(calendar, indent=2), encoding="utf-8")
pathlib.Path("data/timetable.json").write_text(json.dumps(timetable, indent=2), encoding="utf-8")

import sys
import os

# Add parent directory to path so we can import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import db
    db.init_db()
    
    conn = db.get_connection()
    count = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    conn.close()
    
    if count == 0:
        print("Adding dummy database records...")
        db.save_student('BCA001', 'rahul@college.edu', 'Rahul Kumar', 'BCA')
        db.save_student('BCA002', 'priya@college.edu', 'Priya Singh', 'BCA')
        db.save_student('BCA003', 'aman@college.edu', 'Aman Verma', 'BCA')
        db.save_student('BCA004', 'admin1@college.edu', 'Admin Student', 'BCA')
        
        db.record_attendance_session('BCA001', 'Mathematics', '2026-08-20', 'present')
        db.record_attendance_session('BCA001', 'Programming in C', '2026-08-20', 'present')
        db.record_attendance_session('BCA002', 'Mathematics', '2026-08-20', 'absent')
        db.record_attendance_session('BCA003', 'Mathematics', '2026-08-20', 'present')
        db.record_attendance_session('BCA004', 'Mathematics', '2026-08-20', 'present')
        db.record_attendance_session('BCA004', 'Programming in C', '2026-08-20', 'present')
        
        db.save_marks('BCA001', 'Mathematics', 28, 30)
        db.save_marks('BCA001', 'Programming in C', 25, 30)
        db.save_marks('BCA002', 'Mathematics', 15, 30)
        db.save_marks('BCA003', 'Mathematics', 20, 30)
        db.save_marks('BCA004', 'Mathematics', 30, 30)
        db.save_marks('BCA004', 'Programming in C', 28, 30)
        
        db.set_config('min_attendance_pct', '75')
        db.set_config('min_internal_pct', '40')
        print("Dummy database records added.")
    else:
        print("Database already has records, skipping dummy data injection.")
except ImportError:
    print("Could not import db module, skipping database initialization.")

print("OK")
