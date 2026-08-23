// CgpaCalculator.jsx — pure frontend CGPA calculator (no API call needed)
import { useState } from "react";

const GRADE_SCALE = {
  "O  (91-100)": 10, "A+ (81-90)": 9, "A  (71-80)": 8,
  "B+ (61-70)": 7,  "B  (51-60)": 6, "C  (41-50)": 5, "F  (0-40)": 0,
};
const GRADE_OPTIONS = Object.keys(GRADE_SCALE);

function empty(nSubs) {
  return Array.from({ length: nSubs }, (_, i) => ({ name: `Subject ${i + 1}`, credits: 4, grade: GRADE_OPTIONS[0] }));
}

export default function CgpaCalculator() {
  const [nSems, setNSems] = useState(1);
  const [nSubs, setNSubs] = useState(5);
  const [sems, setSems] = useState([empty(5)]);
  const [result, setResult] = useState(null);

  function sync(newNSems, newNSubs) {
    setSems(prev => {
      const next = [];
      for (let i = 0; i < newNSems; i++) {
        const existing = prev[i] || [];
        const adjusted = [];
        for (let j = 0; j < newNSubs; j++) {
          adjusted.push(existing[j] || { name: `Subject ${j + 1}`, credits: 4, grade: GRADE_OPTIONS[0] });
        }
        next.push(adjusted);
      }
      return next;
    });
    setResult(null);
  }

  function updateField(si, sj, field, val) {
    setSems(prev => prev.map((sem, i) =>
      i === si ? sem.map((sub, j) => j === sj ? { ...sub, [field]: val } : sub) : sem
    ));
    setResult(null);
  }

  function calculate() {
    let totalCreditAll = 0, totalWeightAll = 0;
    const semResults = sems.map(sem => {
      const tc = sem.reduce((a, s) => a + Number(s.credits), 0);
      const tw = sem.reduce((a, s) => a + Number(s.credits) * GRADE_SCALE[s.grade], 0);
      totalCreditAll += tc;
      totalWeightAll += tw;
      return { sgpa: tc > 0 ? tw / tc : 0, subjects: sem };
    });
    setResult({ semResults, cgpa: totalCreditAll > 0 ? totalWeightAll / totalCreditAll : 0 });
  }

  const cgpaColor = !result ? "#fff"
    : result.cgpa >= 7 ? "var(--green)"
    : result.cgpa >= 5 ? "var(--orange)"
    : "var(--red)";

  return (
    <div className="page">
      <div className="page-header">
        <h1>🧮 CGPA Calculator</h1>
        <p>Calculate your semester GPA and cumulative CGPA on a 10-point scale</p>
      </div>

      <div className="card mb-2">
        <div className="form-row">
          <div className="form-group">
            <label className="label">Number of Semesters</label>
            <input type="number" className="input" min={1} max={8} value={nSems}
              onChange={e => { const v = Math.max(1, Math.min(8, Number(e.target.value))); setNSems(v); sync(v, nSubs); }} />
          </div>
          <div className="form-group">
            <label className="label">Subjects per Semester</label>
            <input type="number" className="input" min={1} max={10} value={nSubs}
              onChange={e => { const v = Math.max(1, Math.min(10, Number(e.target.value))); setNSubs(v); sync(nSems, v); }} />
          </div>
        </div>
      </div>

      {sems.map((sem, si) => (
        <div key={si} className="card mb-2">
          <h3 style={{ fontWeight: 700, marginBottom: "0.75rem" }}>Semester {si + 1}</h3>
          <div className="cgpa-row-header">
            <span className="label mb-0">Subject</span>
            <span className="label mb-0" style={{ textAlign: "center" }}>Credits</span>
            <span className="label mb-0" style={{ textAlign: "center" }}>Grade</span>
          </div>
          {sem.map((sub, sj) => (
            <div key={sj} className="cgpa-row">
              <input className="input" value={sub.name} placeholder={`Subject ${sj + 1}`}
                onChange={e => updateField(si, sj, "name", e.target.value)} />
              <input type="number" className="input" min={1} max={6} value={sub.credits}
                onChange={e => updateField(si, sj, "credits", e.target.value)} />
              <select className="select" value={sub.grade}
                onChange={e => updateField(si, sj, "grade", e.target.value)}>
                {GRADE_OPTIONS.map(g => <option key={g}>{g}</option>)}
              </select>
            </div>
          ))}
          {result && (
            <div style={{ marginTop: "0.5rem", color: "var(--primary)", fontWeight: 700 }}>
              SGPA: {result.semResults[si].sgpa.toFixed(2)}
            </div>
          )}
        </div>
      ))}

      <button className="btn btn-primary" onClick={calculate} style={{ width: "100%", justifyContent: "center", padding: "0.75rem" }}>
        Calculate CGPA
      </button>

      {result && (
        <div style={{ textAlign: "center", marginTop: "1.5rem", padding: "2rem", background: "var(--bg2)", borderRadius: "var(--radius)", border: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>Your CGPA</div>
          <div style={{ fontSize: "3rem", fontWeight: 800, color: cgpaColor, letterSpacing: "-0.03em" }}>
            {result.cgpa.toFixed(2)}
          </div>
          <div style={{ fontSize: "1rem", color: "var(--text-muted)" }}>/ 10.00</div>
        </div>
      )}
    </div>
  );
}
