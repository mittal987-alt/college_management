// Admin/UploadTimetable.jsx
import { useState } from "react";
import { uploadTimetable } from "../../api";

export default function UploadTimetable() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setResult(null);
    try {
      const res = await uploadTimetable(file);
      setResult({ type: "success", text: `Timetable updated. Found programmes: ${res.programmes?.join(", ")}` });
    } catch (err) {
      setResult({ type: "error", text: err.message });
    }
    setUploading(false);
  }

  return (
    <div className="page">
      <div className="page-header">
        <span className="badge badge-admin" style={{ marginBottom: "0.5rem" }}>ADMIN</span>
        <h1>🗓️ Upload Timetable</h1>
        <p>Upload a JSON file containing class schedules</p>
      </div>

      <div className="card">
        <form onSubmit={handleUpload}>
          <div className="form-group">
            <label className="label">Timetable JSON File</label>
            <input type="file" className="input" accept=".json" onChange={e => setFile(e.target.files[0])} />
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
