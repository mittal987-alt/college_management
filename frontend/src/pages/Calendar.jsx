// Calendar.jsx — academic calendar with type filters and upcoming highlights
import { useEffect, useState } from "react";
import { getCalendar } from "../api";

const TYPE_CONFIG = {
  exam:     { emoji: "📝", color: "#ef4444", label: "Exam" },
  holiday:  { emoji: "🏖️", color: "#22c55e", label: "Holiday" },
  deadline: { emoji: "⏰", color: "#f97316", label: "Deadline" },
  event:    { emoji: "🎉", color: "#8b5cf6", label: "Event" },
};

export default function Calendar() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTypes, setActiveTypes] = useState(Object.keys(TYPE_CONFIG));
  const [showPast, setShowPast] = useState(false);

  useEffect(() => {
    getCalendar()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page"><div className="spinner" /></div>;

  const events = (data?.events || [])
    .filter(e => activeTypes.includes(e.type))
    .filter(e => showPast || e.days_away >= 0)
    .sort((a, b) => a.days_away - b.days_away);

  const upcoming7 = events.filter(e => e.days_away >= 0 && e.days_away <= 7);

  function toggleType(t) {
    setActiveTypes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);
  }

  function daysLabel(d) {
    if (d === 0) return "Today!";
    if (d === 1) return "Tomorrow";
    if (d > 0) return `In ${d} days`;
    return `${Math.abs(d)} days ago`;
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>📅 Academic Calendar</h1>
        <p>Upcoming exams, holidays, deadlines, and events</p>
      </div>

      {/* Filters */}
      <div className="card mb-2" style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "center" }}>
        {Object.entries(TYPE_CONFIG).map(([t, cfg]) => (
          <label key={t} style={{ display: "flex", alignItems: "center", gap: "0.4rem", cursor: "pointer", userSelect: "none" }}>
            <input type="checkbox" checked={activeTypes.includes(t)} onChange={() => toggleType(t)} style={{ accentColor: cfg.color }} />
            <span style={{ fontSize: "0.85rem" }}>{cfg.emoji} {cfg.label}</span>
          </label>
        ))}
        <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", cursor: "pointer", marginLeft: "auto" }}>
          <input type="checkbox" checked={showPast} onChange={() => setShowPast(v => !v)} />
          <span style={{ fontSize: "0.85rem" }}>Show past</span>
        </label>
      </div>

      {/* Next 7 days */}
      {upcoming7.length > 0 && (
        <>
          <h3 style={{ marginBottom: "0.6rem", fontWeight: 700 }}>🔔 Next 7 Days</h3>
          {upcoming7.map((e, i) => {
            const cfg = TYPE_CONFIG[e.type] || { emoji: "📌", color: "var(--primary)", label: e.type };
            return (
              <div key={i} className="cal-event" style={{ borderColor: cfg.color, marginBottom: "0.4rem" }}>
                <div style={{ fontWeight: 600 }}>{cfg.emoji} {e.title}</div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
                  {e.date} &nbsp;·&nbsp;
                  <span style={{ color: cfg.color }}>{daysLabel(e.days_away)}</span>
                </div>
              </div>
            );
          })}
          <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "1.25rem 0" }} />
        </>
      )}

      {/* All events */}
      <h3 style={{ marginBottom: "0.6rem", fontWeight: 700 }}>📋 All Events</h3>
      {events.length === 0 && <div className="alert alert-info">No events match your filters.</div>}
      {events.map((e, i) => {
        const cfg = TYPE_CONFIG[e.type] || { emoji: "📌", color: "var(--primary)", label: e.type };
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: "1rem", padding: "0.55rem 0", borderBottom: "1px solid var(--border)" }}>
            <span style={{ width: 60, fontSize: "0.82rem", fontWeight: 700, color: "var(--text-muted)", flexShrink: 0 }}>
              {new Date(e.date).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
            </span>
            <span style={{ flex: 1, fontSize: "0.9rem" }}>{cfg.emoji} {e.title}</span>
            <span style={{ fontSize: "0.78rem", color: cfg.color, flexShrink: 0 }}>{daysLabel(e.days_away)}</span>
          </div>
        );
      })}
    </div>
  );
}
