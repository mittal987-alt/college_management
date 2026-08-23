// Eligibility.jsx — exam eligibility checker
import { useEffect, useState } from "react";
import { getEligibility, linkRollNo } from "../api";

export default function Eligibility() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rollInput, setRollInput] = useState("");
  const [linking, setLinking] = useState(false);
  const [linkMsg, setLinkMsg] = useState(null);

  async function load() {
    setLoading(true);
    try { setData(await getEligibility()); } catch {}
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function handleLink() {
    if (!rollInput.trim()) return;
    setLinking(true);
    try {
      await linkRollNo(rollInput.trim());
      setLinkMsg({ type: "success", text: "Linked! Refreshing..." });
      setTimeout(load, 1000);
    } catch (e) {
      setLinkMsg({ type: "error", text: e.message });
    }
    setLinking(false);
  }

  if (loading) return <div className="page"><div className="spinner" /></div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1>🔔 Exam Eligibility</h1>
        <p>Check if you can sit for end-semester exams</p>
      </div>

      {!data?.linked && (
        <div className="card">
          <div className="alert alert-info mb-2">Link your roll number to see live eligibility data.</div>
          <label className="label">Roll Number</label>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <input className="input" value={rollInput} onChange={e => setRollInput(e.target.value)} placeholder="e.g. BCA001" />
            <button className="btn btn-primary" onClick={handleLink} disabled={linking}>
              {linking ? <span className="spinner" /> : "Link"}
            </button>
          </div>
          {linkMsg && <div className={`alert alert-${linkMsg.type === "success" ? "success" : "error"} mt-1`}>{linkMsg.text}</div>}
        </div>
      )}

      {data?.linked && !data?.subjects && (
        <div className="alert alert-info">{data.message || "No data recorded yet."}</div>
      )}

      {data?.subjects && (
        <>
          <div className="card mb-2" style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            <span className="text-muted text-sm">Roll: <b>{data.roll_no}</b></span>
            <span className="text-muted text-sm">Min. Attendance: <b>{data.required_attendance_pct}%</b></span>
            <span className="text-muted text-sm">Min. Internals: <b>{data.required_internal_pct}%</b></span>
          </div>

          {data.subjects.map(s => {
            const icon = s.eligible ? "✅" : "❌";
            const color = s.eligible ? "var(--green)" : "var(--red)";
            const cls = s.eligible ? "ok" : "bad";
            const reasons = [];
            if (!s.attendance_ok) reasons.push(`Attendance ${s.attendance_pct.toFixed(1)}% is below ${data.required_attendance_pct}%`);
            if (s.internal_marks_ok === false) reasons.push(`Internals ${s.internal_marks_pct}% is below ${data.required_internal_pct}%`);
            else if (s.internal_marks_pct === null) reasons.push("No internal marks recorded yet");
            const detail = reasons.length ? reasons.join(" · ") : "All criteria met";

            return (
              <div key={s.subject} className={`subject-row ${cls}`}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontWeight: 600 }}>{icon} {s.subject}</span>
                  <span style={{ color, fontWeight: 700 }}>{s.eligible ? "ELIGIBLE" : "NOT ELIGIBLE"}</span>
                </div>
                <div className="text-muted text-sm mt-1">{detail}</div>
              </div>
            );
          })}

          <div className={`alert ${data.all_eligible ? "alert-success" : "alert-error"} mt-2`}>
            {data.all_eligible
              ? "🎉 You are eligible to appear in all end-semester examinations!"
              : "⚠️ You may NOT be eligible for some exams. Please contact your class teacher."}
          </div>
        </>
      )}
    </div>
  );
}
