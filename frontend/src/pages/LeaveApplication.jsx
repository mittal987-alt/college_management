// LeaveApplication.jsx — AI-powered leave letter generator
import { useState } from "react";
import { generateLeave } from "../api";

const PROGRAMMES = ["BCA", "BBA", "B.Com (H)"];
const SEMESTERS = ["1st", "2nd", "3rd", "4th", "5th", "6th"];

export default function LeaveApplication() {
  const today = new Date().toISOString().split("T")[0];
  const [form, setForm] = useState({
    student_name: "", roll_no: "", programme: "BCA", semester: "1st",
    from_date: today, to_date: today, reason: "", hod_name: "",
  });
  const [loading, setLoading] = useState(false);
  const [letter, setLetter] = useState("");
  const [error, setError] = useState("");

  function update(k, v) { setForm(f => ({ ...f, [k]: v })); }

  async function generate() {
    if (!form.student_name.trim() || !form.reason.trim()) {
      setError("Please fill in your name and reason for leave."); return;
    }
    setError(""); setLoading(true);
    try {
      const res = await generateLeave(form);
      setLetter(res.letter);
    } catch (e) {
      setError(e.message || "Failed to generate letter. Please try again.");
    }
    setLoading(false);
  }

  function download() {
    const blob = new Blob([letter], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `leave_application_${form.student_name.replace(/\s+/g, "_")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>📝 Leave Application Generator</h1>
        <p>Generate a formal leave application letter for your HOD in seconds</p>
      </div>

      <div className="card">
        <div className="form-row">
          <div className="form-group">
            <label className="label">Full Name *</label>
            <input className="input" placeholder="Rahul Kumar" value={form.student_name}
              onChange={e => update("student_name", e.target.value)} />
          </div>
          <div className="form-group">
            <label className="label">Roll Number</label>
            <input className="input" placeholder="BCA/2024/001" value={form.roll_no}
              onChange={e => update("roll_no", e.target.value)} />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="label">Programme</label>
            <select className="select" value={form.programme} onChange={e => update("programme", e.target.value)}>
              {PROGRAMMES.map(p => <option key={p}>{p}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="label">Semester</label>
            <select className="select" value={form.semester} onChange={e => update("semester", e.target.value)}>
              {SEMESTERS.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="label">Leave From</label>
            <input type="date" className="input" value={form.from_date} onChange={e => update("from_date", e.target.value)} />
          </div>
          <div className="form-group">
            <label className="label">Leave Till</label>
            <input type="date" className="input" value={form.to_date} onChange={e => update("to_date", e.target.value)} />
          </div>
        </div>

        <div className="form-group">
          <label className="label">Reason for Leave *</label>
          <textarea className="input" rows={3} style={{ resize: "vertical" }}
            placeholder="e.g. I am suffering from high fever and have been advised rest by the doctor for 3 days."
            value={form.reason} onChange={e => update("reason", e.target.value)} />
        </div>

        <div className="form-group">
          <label className="label">HOD's Name (optional)</label>
          <input className="input" placeholder="Dr. Sharma" value={form.hod_name}
            onChange={e => update("hod_name", e.target.value)} />
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <button className="btn btn-primary w-full" style={{ justifyContent: "center", padding: "0.75rem" }}
          onClick={generate} disabled={loading}>
          {loading ? <><span className="spinner" style={{ width: 16, height: 16 }} /> &nbsp; Generating...</> : "✨ Generate Application"}
        </button>
      </div>

      {letter && (
        <>
          <h3 style={{ margin: "1.5rem 0 0.75rem", fontWeight: 700 }}>📄 Your Leave Application</h3>
          <div style={{
            background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "var(--radius)",
            padding: "1.5rem 2rem", fontFamily: "Georgia, serif",
            lineHeight: 1.9, whiteSpace: "pre-wrap", fontSize: "0.9rem", marginBottom: "1rem",
          }}>
            {letter}
          </div>
          <button className="btn btn-ghost" onClick={download}>⬇️ Download as .txt</button>
        </>
      )}
    </div>
  );
}
