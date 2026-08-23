// Sidebar.jsx — Modern App Style
import { NavLink } from "react-router-dom";
import {
  MessageSquare, CalendarDays, BarChart2, Calculator,
  FileText, Bell, Table2, Users, Upload, CalendarClock,
  CalendarPlus, LayoutDashboard, LogOut
} from "lucide-react";
import { logout } from "../api";

const studentNav = [
  { to: "/chat",       label: "Chat",               Icon: MessageSquare },
  { to: "/calendar",   label: "Academic Calendar",  Icon: CalendarDays },
  { to: "/attendance", label: "Attendance Tracker", Icon: BarChart2 },
  { to: "/cgpa",       label: "CGPA Calculator",    Icon: Calculator },
  { to: "/leave",      label: "Leave Application",  Icon: FileText },
  { to: "/eligibility",label: "Exam Eligibility",   Icon: Bell },
  { to: "/timetable",  label: "Timetable",          Icon: Table2 },
];

const adminNav = [
  { to: "/admin/upload-students",    label: "Upload Students",    Icon: Users },
  { to: "/admin/upload-attendance",  label: "Upload Attendance",  Icon: Upload },
  { to: "/admin/upload-timetable",   label: "Upload Timetable",   Icon: CalendarClock },
  { to: "/admin/upload-calendar",    label: "Upload Calendar",    Icon: CalendarPlus },
  { to: "/admin/dashboard",          label: "Admin Dashboard",    Icon: LayoutDashboard },
];

export default function Sidebar({ user, onLogout }) {
  async function handleLogout() {
    await logout();
    onLogout();
  }

  return (
    <nav className="sidebar">
      <div className="sidebar-logo">
        <div style={{ background: "var(--primary)", color: "var(--bg)", width: 32, height: 32, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <MessageSquare size={18} fill="currentColor" />
        </div>
        <span style={{ fontSize: "1rem", fontWeight: 700, letterSpacing: "-0.5px", color: "var(--text)" }}>CollegeBot</span>
      </div>

      <div className="sidebar-section">Student Portal</div>
      <div>
        {studentNav.map(({ to, label, Icon }) => (
          <NavLink
            key={to} to={to}
            className={({ isActive }) => `sidebar-item${isActive ? " active" : ""}`}
          >
            <Icon size={18} style={{ flexShrink: 0 }} /> 
            <span style={{ flex: 1 }}>{label}</span>
          </NavLink>
        ))}
      </div>

      {user?.is_admin && (
        <>
          <div className="sidebar-section" style={{ marginTop: "1rem" }}>Admin Center</div>
          <div>
            {adminNav.map(({ to, label, Icon }) => (
              <NavLink
                key={to} to={to}
                className={({ isActive }) => `sidebar-item${isActive ? " active" : ""}`}
              >
                <Icon size={18} style={{ flexShrink: 0 }} /> 
                <span style={{ flex: 1 }}>{label}</span>
              </NavLink>
            ))}
          </div>
        </>
      )}

      <div className="sidebar-user">
        {user?.picture
          ? <img src={user.picture} alt="avatar" />
          : <div style={{ width: 36, height: 36, borderRadius: "50%", background: "var(--primary-dim)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1rem", fontWeight: 700 }}>
              {(user?.name || "?")[0].toUpperCase()}
            </div>
        }
        <div className="sidebar-user-info">
          <div className="sidebar-user-name">{user?.name || user?.email}</div>
          <div className="sidebar-user-email">{user?.email}</div>
        </div>
        <button className="btn-icon" onClick={handleLogout} title="Logout">
          <LogOut size={16} />
        </button>
      </div>
    </nav>
  );
}
