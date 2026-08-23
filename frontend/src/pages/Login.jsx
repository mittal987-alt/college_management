// Login.jsx — Premium login page for College Assistant
import { loginUrl } from "../api";

export default function Login() {
  return (
    <div className="login-page">
      {/* Animated background orbs */}
      <div className="login-bg-orb login-bg-orb-1" />
      <div className="login-bg-orb login-bg-orb-2" />
      <div className="login-bg-orb login-bg-orb-3" />

      <div className="login-container">
        {/* Left panel — branding */}
        <div className="login-left">
          <div className="login-brand">
            <div className="login-brand-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 10v6M2 10l10-5 10 5-10 5z"/>
                <path d="M6 12v5c3 3 9 3 12 0v-5"/>
              </svg>
            </div>
            <span className="login-brand-name">CollegeBot</span>
          </div>

          <div className="login-hero-text">
            <h1 className="login-hero-h1">Your Academic<br /><span className="login-hero-accent">AI Assistant</span></h1>
            <p className="login-hero-sub">Everything you need for college, in one intelligent portal.</p>
          </div>

          <div className="login-features">
            {[
              { icon: "📊", label: "Live Attendance Tracking" },
              { icon: "🗓️", label: "Class Timetable & Calendar" },
              { icon: "🧮", label: "CGPA Calculator" },
              { icon: "🤖", label: "AI Chatbot with RAG" },
            ].map(({ icon, label }) => (
              <div key={label} className="login-feature-row">
                <span className="login-feature-icon">{icon}</span>
                <span className="login-feature-label">{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel — sign in card */}
        <div className="login-right">
          <div className="login-card">
            <div className="login-card-icon">🎓</div>
            <h2 className="login-card-title">Welcome back</h2>
            <p className="login-card-sub">Sign in with your college Google account to continue</p>

            <a href={loginUrl()} className="google-btn-link">
              <button className="google-btn">
                <svg width="20" height="20" viewBox="0 0 48 48">
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                </svg>
                Continue with Google
              </button>
            </a>

            <p className="login-card-disclaimer">
              Access is restricted to authorised college accounts only.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
