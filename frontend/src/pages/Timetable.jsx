// Timetable.jsx — class schedule viewer with "NOW" highlighting
import { useEffect, useState } from "react";
import { getTimetable } from "../api";

const PROGRAMMES = ["BCA", "BBA", "B.Com (H)"];

function nowHour() {
  const now = new Date();
  return { h: now.getHours(), m: now.getMinutes() };
}

function isCurrentSlot(time, isToday) {
  if (!isToday || !time.includes("-")) return false;
  try {
    const [start, end] = time.split("-");
    const sh = parseInt(start.split(":")[0]);
    const eh = parseInt(end.split(":")[0]);
    const { h } = nowHour();
    return sh <= h && h < eh;
  } catch { return false; }
}

export default function Timetable() {
  const [programme, setProgramme] = useState("BCA");
  const [data, setData] = useState(null);
  const [day, setDay] = useState(null);
  const [loading, setLoading] = useState(true);

  async function load(prog, d) {
    setLoading(true);
    try { setData(await getTimetable(prog, d)); } catch {}
    setLoading(false);
  }

  useEffect(() => { load(programme, day); }, [programme, day]);

  const isToday = data?.day === data?.today;

  return (
    <div className="page">
      <div className="page-header">
        <h1>🗓️ Class Timetable</h1>
        <p>Your daily class schedule</p>
      </div>

      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <div>
          <label className="label">Programme</label>
          <select className="select" style={{ width: 180 }} value={programme}
            onChange={e => { setProgramme(e.target.value); setDay(null); }}>
            {PROGRAMMES.map(p => <option key={p}>{p}</option>)}
          </select>
        </div>
        {data?.available_days && (
          <div>
            <label className="label">Day</label>
            <select className="select" style={{ width: 160 }} value={data.day}
              onChange={e => setDay(e.target.value)}>
              {data.available_days.map(d => <option key={d}>{d}</option>)}
            </select>
          </div>
        )}
      </div>

      {loading && <div className="spinner" />}

      {!loading && data && (
        <>
          <h3 style={{ marginBottom: "0.75rem", fontWeight: 700 }}>
            {programme} — {data.day} {isToday && <span style={{ color: "var(--primary)", fontSize: "0.85rem", fontWeight: 500 }}>· Today</span>}
          </h3>
          {data.slots.map((slot, i) => {
            if (slot.subject === "LUNCH BREAK") {
              return (
                <div key={i} style={{
                  textAlign: "center", color: "var(--text-muted)", padding: "0.5rem 0",
                  borderTop: "1px dashed var(--border)", borderBottom: "1px dashed var(--border)",
                  margin: "0.25rem 0", fontSize: "0.85rem"
                }}>
                  🍽️ LUNCH BREAK · 12:00 – 13:00
                </div>
              );
            }
            const current = isCurrentSlot(slot.time, isToday);
            return (
              <div key={i} className={`timetable-slot${current ? " current" : ""}`}>
                <div className="timetable-slot-time">
                  {slot.time}
                  {current && <span className="now-badge">▶ NOW</span>}
                </div>
                <div className="timetable-slot-subject">{slot.subject}</div>
                {(slot.room || slot.teacher) && (
                  <div className="timetable-slot-meta">
                    {slot.room && `Room ${slot.room}`}{slot.room && slot.teacher && " · "}{slot.teacher}
                  </div>
                )}
              </div>
            );
          })}
        </>
      )}

      {!loading && data?.slots?.length === 0 && (
        <div className="alert alert-info">No timetable found for this selection.</div>
      )}
    </div>
  );
}
