// Admin/Dashboard.jsx — usage stats for admin users
import { useEffect, useState } from "react";
import { getAdminStats, getAdminConfig, updateAdminConfig } from "../../api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [config, setConfig] = useState(null);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");

  useEffect(() => {
    getAdminStats().then(setStats).catch(() => {});
    getAdminConfig().then(setConfig).catch(() => {});
  }, []);

  async function saveConfig() {
    setSaving(true);
    try {
      await updateAdminConfig(config);
      setSavedMsg("Saved ✅");
      setTimeout(() => setSavedMsg(""), 2500);
    } catch {}
    setSaving(false);
  }

  if (!stats) return <div className="page"><div className="spinner" /></div>;

  const qtData = Object.entries(stats.query_type_counts || {}).map(([k, v]) => ({ name: k, count: v }));
  const dvData = Object.entries(stats.daily_volume || {}).sort().map(([d, v]) => ({ date: d.slice(5), count: v }));
  const drData = Object.entries(stats.daily_down_rate || {}).sort().map(([d, r]) => ({ date: d.slice(5), rate: r }));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <span className="badge badge-admin" style={{ marginBottom: "0.5rem" }}>ADMIN</span>
          <h1>🛠️ Admin Dashboard</h1>
          <p>Usage insights for the College Assistant</p>
        </div>
      </div>

      <div className="metric-row">
        <div className="metric-card">
          <div className="metric-label">Questions Asked</div>
          <div className="metric-value">{stats.total_questions}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Unique Students</div>
          <div className="metric-value">{stats.unique_students}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">👎 Rate</div>
          <div className="metric-value" style={{ color: stats.down_rate > 30 ? "var(--red)" : "var(--green)" }}>
            {stats.down_rate.toFixed(1)}%
          </div>
        </div>
      </div>

      {qtData.length > 0 && (
        <>
          <h3 style={{ fontWeight: 700, marginBottom: "0.75rem" }}>Query Volume by Category</h3>
          <div className="card mb-2" style={{ padding: "1rem 0.5rem" }}>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={qtData}>
                <XAxis dataKey="name" tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
                <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 8 }} />
                <Bar dataKey="count" fill="var(--primary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {dvData.length > 0 && (
        <>
          <h3 style={{ fontWeight: 700, margin: "1rem 0 0.75rem" }}>Query Volume Over Time</h3>
          <div className="card mb-2" style={{ padding: "1rem 0.5rem" }}>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={dvData}>
                <XAxis dataKey="date" tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
                <YAxis tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 8 }} />
                <Line type="monotone" dataKey="count" stroke="var(--primary)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {drData.length > 0 && (
        <>
          <h3 style={{ fontWeight: 700, margin: "1rem 0 0.75rem" }}>👎 Rate Over Time</h3>
          <div className="card mb-2" style={{ padding: "1rem 0.5rem" }}>
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={drData}>
                <XAxis dataKey="date" tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
                <YAxis tick={{ fill: "var(--text-muted)", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: 8 }} />
                <Line type="monotone" dataKey="rate" stroke="var(--red)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      <h3 style={{ fontWeight: 700, margin: "1rem 0 0.75rem" }}>Most Asked Questions</h3>
      <div className="card mb-2">
        <table>
          <thead><tr><th>Query</th><th>Count</th></tr></thead>
          <tbody>
            {stats.top_queries.map((q, i) => (
              <tr key={i}><td>{q.query || "—"}</td><td>{q.count}</td></tr>
            ))}
            {stats.top_queries.length === 0 && <tr><td colSpan={2} className="text-muted text-sm">No data yet.</td></tr>}
          </tbody>
        </table>
      </div>

      {config && (
        <>
          <h3 style={{ fontWeight: 700, margin: "1rem 0 0.75rem" }}>⚙️ Eligibility Rules</h3>
          <div className="card">
            <div className="form-row">
              <div className="form-group">
                <label className="label">Minimum Attendance %</label>
                <input type="number" className="input" min={0} max={100} value={config.min_attendance_pct}
                  onChange={e => setConfig(c => ({ ...c, min_attendance_pct: Number(e.target.value) }))} />
              </div>
              <div className="form-group">
                <label className="label">Minimum Internal Marks %</label>
                <input type="number" className="input" min={0} max={100} value={config.min_internal_pct}
                  onChange={e => setConfig(c => ({ ...c, min_internal_pct: Number(e.target.value) }))} />
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
              <button className="btn btn-primary" onClick={saveConfig} disabled={saving}>
                {saving ? <span className="spinner" style={{ width: 14, height: 14 }} /> : "💾 Save Rules"}
              </button>
              {savedMsg && <span style={{ color: "var(--green)", fontSize: "0.85rem" }}>{savedMsg}</span>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
