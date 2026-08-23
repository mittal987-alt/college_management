// Admin/UploadStudents.jsx
import { useState } from "react";
import { uploadStudents } from "../../api";

export default function UploadStudents() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setResult(null);
    try {
      const res = await uploadStudents(file);
      setResult({ type: "success", text: `Saved ${res.saved} student records.` });
    } catch (err) {
      setResult({ type: "error", text: err.message });
    }
    setUploading(false);
  }

  return (
    <div className="page">
      <div className="page-header">
        <span className="badge badge-admin" style={{ marginBottom: "0.5rem" }}>ADMIN</span>
        <h1>👥 Upload Students</h1>
        <p>Upload a CSV or JSON roster of students</p>
      </div>

      <div className="card">
        <p className="text-muted mb-2">
          Required columns: <b>roll_no</b>. Optional: <b>name</b>, <b>email</b>, <b>programme</b>.
        </p>
        <form onSubmit={handleUpload}>
          <div className="form-group">
            <label className="label">File (CSV or JSON)</label>
            <input type="file" className="input" accept=".csv,.json" onChange={e => setFile(e.target.files[0])} />
          </div>
          <button className="btn btn-primary mt-1" type="submit" disabled={!file || uploading}>
            {uploading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : "📤 Upload"}
          </button>
        </form>
        {result && <div className={`alert alert-${result.type} mt-2`}>{result.text}</div>}
      </div>
    </div>
  );
}
