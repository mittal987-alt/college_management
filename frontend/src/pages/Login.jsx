// Login.jsx — authentication screen for Google or email/password flows
import { useState } from "react";
import { loginUrl, loginWithEmail, signupWithEmail } from "../api";

const EMPTY_FORM = { name: "", email: "", password: "" };

export default function Login({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState(EMPTY_FORM);
  const [status, setStatus] = useState({ type: "", message: "" });
  const [loading, setLoading] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setStatus({ type: "", message: "" });

    try {
      const request = mode === "login" ? loginWithEmail : signupWithEmail;
      const payload = mode === "login"
        ? { email: form.email, password: form.password }
        : { name: form.name, email: form.email, password: form.password };

      const data = await request(payload);
      if (onAuthenticated) {
        onAuthenticated(data.user);
      } else {
        window.location.reload();
      }
    } catch (error) {
      setStatus({ type: "error", message: error.message || "Authentication failed." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-bg-orb login-bg-orb-1" />
      <div className="login-bg-orb login-bg-orb-2" />
      <div className="login-bg-orb login-bg-orb-3" />

      <div className="login-container">
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

        <div className="login-right">
          <div className="login-card">
            <div className="login-card-icon">🎓</div>
            <h2 className="login-card-title">{mode === "login" ? "Welcome back" : "Create account"}</h2>
            <p className="login-card-sub">
              {mode === "login"
                ? "Sign in with your email and password or continue with Google."
                : "Set up your account to access academic tools and AI support."}
            </p>

            <div className="auth-mode-toggle" aria-label="Authentication mode selector">
              <button
                type="button"
                className={`auth-mode-btn ${mode === "login" ? "active" : ""}`}
                onClick={() => setMode("login")}
              >
                Sign in
              </button>
              <button
                type="button"
                className={`auth-mode-btn ${mode === "signup" ? "active" : ""}`}
                onClick={() => setMode("signup")}
              >
                Sign up
              </button>
            </div>

            <form className="auth-form" onSubmit={handleSubmit}>
              {mode === "signup" && (
                <div className="auth-field">
                  <label htmlFor="name">Full name</label>
                  <input
                    id="name"
                    name="name"
                    className="auth-input"
                    type="text"
                    placeholder="Your full name"
                    value={form.name}
                    onChange={handleChange}
                    required
                  />
                </div>
              )}

              <div className="auth-field">
                <label htmlFor="email">Email address</label>
                <input
                  id="email"
                  name="email"
                  className="auth-input"
                  type="email"
                  placeholder="you@college.edu"
                  value={form.email}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="auth-field">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  name="password"
                  className="auth-input"
                  type="password"
                  placeholder="Enter your password"
                  value={form.password}
                  onChange={handleChange}
                  required
                  minLength={6}
                />
              </div>

              {status.message && (
                <div className={`auth-status ${status.type === "error" ? "auth-status-error" : "auth-status-success"}`}>
                  {status.message}
                </div>
              )}

              <button type="submit" className="auth-submit" disabled={loading}>
                {loading ? "Please wait..." : (mode === "login" ? "Sign in" : "Create account")}
              </button>
            </form>

            <div className="auth-divider">
              <span>or</span>
            </div>

            <a href={loginUrl()} className="google-btn-link">
              <button type="button" className="google-btn">
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
