// Attendance.jsx — subject-wise attendance tracker
import { useEffect, useState } from "react";
import { getAttendance, linkRollNo } from "../api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

export default function Attendance() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rollInput, setRollInput] = useState("");
  const [linking, setLinking] = useState(false);
  const [linkMsg, setLinkMsg] = useState(null);

  async function load() {
    setLoading(true);
    try { setData(await getAttendance()); } catch {}
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function handleLink() {
    if (!rollInput.trim()) return;
    setLinking(true);
    try {
      await linkRollNo(rollInput.trim());
      setLinkMsg({ type: "success", text: "Linked successfully! Refreshing..." });
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
        <h1>📊 Attendance Tracker</h1>
        <p>Subject-wise attendance and eligibility overview</p>
      </div>

      {!data?.linked && (
        <div className="card">
          <div className="alert alert-info mb-2">Your account is not linked to a roll number yet.</div>
          <label className="label">Your Roll Number</label>
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
        <div className="alert alert-info">{data.message || "No attendance data recorded yet."}</div>
      )}

      {data?.subjects && (
        <>
          <div className="metric-row">
            <div className="metric-card">
              <div className="metric-label">Total Held</div>
              <div className="metric-value">{data.subjects.reduce((a, s) => a + s.held, 0)}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Total Attended</div>
              <div className="metric-value">{data.subjects.reduce((a, s) => a + s.attended, 0)}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Overall %</div>
              <div className="metric-value" style={{ color: data.overall_eligible ? "var(--green)" : "var(--red)" }}>
                {data.overall_pct?.toFixed(1)}%
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Required</div>
              <div className="metric-value">{data.required_pct?.toFixed(0)}%</div>
            </div>
          </div>

          <h3 style={{ marginBottom: "0.75rem", fontWeight: 700 }}>Subject-wise Breakdown</h3>
          {data.subjects.map(s => {
            const ok = s.eligible;
            return (
              <div key={s.subject} className={`subject-row ${ok ? "ok" : "bad"}`}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: 600 }}>{ok ? "✅" : "❌"} {s.subject}</span>
                  <span style={{ color: ok ? "var(--green)" : "var(--red)", fontWeight: 700, fontSize: "1.05rem" }}>
                    {s.pct.toFixed(1)}%
                  </span>
                </div>
                <div className="text-muted text-sm">{s.attended}/{s.held} classes attended</div>
                <div className="progress-bar mt-1">
                  <div className="progress-fill" style={{ width: `${Math.min(s.pct, 100)}%`, background: ok ? "var(--green)" : "var(--red)" }} />
                </div>
              </div>
            );
          })}

          <h3 style={{ margin: "1.5rem 0 0.75rem", fontWeight: 700 }}>Attendance Chart</h3>
          <div className="card" style={{ padding: "1rem 0.5rem" }}>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={data.subjects.map(s => ({ name: s.subject.split(" ").slice(-1)[0], pct: s.pct }))}>
                <XAxis dataKey="name" tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
                <YAxis domain={[0, 100]} tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 8 }} />
                <ReferenceLine y={data.required_pct} stroke="var(--red)" strokeDasharray="4 4" />
                <Bar dataKey="pct" fill="var(--primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
