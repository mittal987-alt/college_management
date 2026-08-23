// Admin/UploadAttendance.jsx
import { useState } from "react";
import { uploadAttendance } from "../../api";

export default function UploadAttendance() {
  const [file, setFile] = useState(null);
  const [subject, setSubject] = useState("");
  const [sessionDate, setSessionDate] = useState(new Date().toISOString().split("T")[0]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file || !subject.trim()) return;
    setUploading(true);
    setResult(null);
    try {
      const res = await uploadAttendance(file, subject.trim(), sessionDate);
      setResult({ type: "success", text: `Saved ${res.saved} records. Skipped ${res.skipped}.` });
    } catch (err) {
      setResult({ type: "error", text: err.message });
    }
    setUploading(false);
  }

  return (
    <div className="page">
      <div className="page-header">
        <span className="badge badge-admin" style={{ marginBottom: "0.5rem" }}>ADMIN</span>
        <h1>📊 Upload Attendance</h1>
        <p>Upload a CSV, JSON, or PDF attendance sheet</p>
      </div>

      <div className="card">
        <p className="text-muted mb-2">
          Required columns: <b>roll_no</b>, <b>status</b> (present/absent).
        </p>
        <form onSubmit={handleUpload}>
          <div className="form-row">
            <div className="form-group">
              <label className="label">Subject *</label>
              <input className="input" required value={subject} onChange={e => setSubject(e.target.value)} placeholder="e.g. Database Systems" />
            </div>
            <div className="form-group">
              <label className="label">Class Date *</label>
              <input type="date" className="input" required value={sessionDate} onChange={e => setSessionDate(e.target.value)} />
            </div>
          </div>
          <div className="form-group">
            <label className="label">File (CSV, JSON, PDF)</label>
            <input type="file" className="input" accept=".csv,.json,.pdf" onChange={e => setFile(e.target.files[0])} />
          </div>
          <button className="btn btn-primary mt-1" type="submit" disabled={!file || !subject.trim() || uploading}>
            {uploading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : "📤 Upload"}
          </button>
        </form>
        {result && <div className={`alert alert-${result.type} mt-2`}>{result.text}</div>}
      </div>
    </div>
  );
}
