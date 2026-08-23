import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { getMe } from "./api";

// Components
import Sidebar from "./components/Sidebar";

// Pages
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import Attendance from "./pages/Attendance";
import Eligibility from "./pages/Eligibility";
import Timetable from "./pages/Timetable";
import Calendar from "./pages/Calendar";
import CgpaCalculator from "./pages/CgpaCalculator";
import LeaveApplication from "./pages/LeaveApplication";

// Admin Pages
import AdminDashboard from "./pages/Admin/Dashboard";
import UploadStudents from "./pages/Admin/UploadStudents";
import UploadAttendance from "./pages/Admin/UploadAttendance";
import UploadTimetable from "./pages/Admin/UploadTimetable";
import UploadCalendar from "./pages/Admin/UploadCalendar";

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then(u => setUser(u))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "var(--bg)" }}>
        <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar user={user} onLogout={() => setUser(null)} />
        <main className="main">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<Chat user={user} />} />
            <Route path="/attendance" element={<Attendance />} />
            <Route path="/eligibility" element={<Eligibility />} />
            <Route path="/timetable" element={<Timetable />} />
            <Route path="/calendar" element={<Calendar />} />
            <Route path="/cgpa" element={<CgpaCalculator />} />
            <Route path="/leave" element={<LeaveApplication />} />

            {/* Admin Routes */}
            {user.is_admin ? (
              <>
                <Route path="/admin/dashboard" element={<AdminDashboard />} />
                <Route path="/admin/upload-students" element={<UploadStudents />} />
                <Route path="/admin/upload-attendance" element={<UploadAttendance />} />
                <Route path="/admin/upload-timetable" element={<UploadTimetable />} />
                <Route path="/admin/upload-calendar" element={<UploadCalendar />} />
              </>
            ) : (
              <Route path="/admin/*" element={<Navigate to="/chat" replace />} />
            )}

            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
