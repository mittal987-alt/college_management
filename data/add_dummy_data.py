import db

def add_dummy_data():
    db.init_db()
    
    # Check if students exist
    conn = db.get_connection()
    count = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    conn.close()
    
    if count == 0:
        print('Adding dummy students...')
        db.save_student('BCA001', 'rahul@college.edu', 'Rahul Kumar', 'BCA')
        db.save_student('BCA002', 'priya@college.edu', 'Priya Singh', 'BCA')
        db.save_student('BCA003', 'aman@college.edu', 'Aman Verma', 'BCA')
        db.save_student('BCA004', 'admin1@college.edu', 'Admin Student', 'BCA')
        
        print('Adding dummy attendance sessions...')
        db.record_attendance_session('BCA001', 'Mathematics', '2026-08-20', 'present')
        db.record_attendance_session('BCA001', 'Programming in C', '2026-08-20', 'present')
        db.record_attendance_session('BCA002', 'Mathematics', '2026-08-20', 'absent')
        db.record_attendance_session('BCA003', 'Mathematics', '2026-08-20', 'present')
        db.record_attendance_session('BCA004', 'Mathematics', '2026-08-20', 'present')
        db.record_attendance_session('BCA004', 'Programming in C', '2026-08-20', 'present')
        
        print('Adding dummy marks...')
        db.save_marks('BCA001', 'Mathematics', 28, 30)
        db.save_marks('BCA001', 'Programming in C', 25, 30)
        db.save_marks('BCA002', 'Mathematics', 15, 30)
        db.save_marks('BCA003', 'Mathematics', 20, 30)
        db.save_marks('BCA004', 'Mathematics', 30, 30)
        db.save_marks('BCA004', 'Programming in C', 28, 30)
        
        print('Adding dummy config...')
        db.set_config('min_attendance_pct', '75')
        db.set_config('min_internal_pct', '40')
        print('Dummy data added successfully.')
    else:
        print('Dummy data already exists.')

if __name__ == '__main__':
    add_dummy_data()
