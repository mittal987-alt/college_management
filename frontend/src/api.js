// api.js — central API client for all backend calls

const BASE = import.meta.env.VITE_API_URL || "";

async function api(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// Auth
export const getMe = () => api("/api/auth/me");
export const logout = () => api("/api/auth/logout", { method: "POST" });
export const loginUrl = () => `${BASE}/api/auth/login`;

// Student data
export const getAttendance = () => api("/api/student/attendance");
export const getEligibility = () => api("/api/student/eligibility");
export const getTimetable = (programme, day) =>
  api(`/api/student/timetable?programme=${encodeURIComponent(programme)}${day ? `&day=${day}` : ""}`);
export const getCalendar = () => api("/api/student/calendar");
export const linkRollNo = (roll_no) =>
  api("/api/student/link", { method: "POST", body: JSON.stringify({ roll_no }) });
export const generateLeave = (data) =>
  api("/api/student/leave", { method: "POST", body: JSON.stringify(data) });

// Chat
export const getConversations = () => api("/api/chat/conversations");
export const getConversation = (id) => api(`/api/chat/conversations/${id}`);
export const setFeedback = (conv_id, msg_index, feedback) =>
  api(`/api/chat/conversations/${conv_id}/feedback`, {
    method: "POST",
    body: JSON.stringify({ msg_index, feedback }),
  });

// Chat stream — returns an EventSource-like async generator via fetch + ReadableStream
export async function* streamChat({ query, programme, conv_id, language }) {
  const res = await fetch(`${BASE}/api/chat/stream`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, programme, conv_id, language }),
  });
  if (!res.ok) throw new Error("Chat request failed");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          yield JSON.parse(line.slice(6));
        } catch {}
      }
    }
  }
}

// Admin
export const getAdminStats = () => api("/api/admin/stats");
export const getAdminConfig = () => api("/api/admin/config");
export const updateAdminConfig = (data) =>
  api("/api/admin/config", { method: "PUT", body: JSON.stringify(data) });

export const uploadStudents = (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return fetch(`${BASE}/api/admin/upload/students`, {
    method: "POST", credentials: "include", body: fd,
  }).then((r) => r.json());
};

export const uploadAttendance = (file, subject, session_date) => {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("subject", subject);
  fd.append("session_date", session_date);
  return fetch(`${BASE}/api/admin/upload/attendance`, {
    method: "POST", credentials: "include", body: fd,
  }).then((r) => r.json());
};

export const uploadTimetable = (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return fetch(`${BASE}/api/admin/upload/timetable`, {
    method: "POST", credentials: "include", body: fd,
  }).then((r) => r.json());
};

export const uploadCalendar = (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return fetch(`${BASE}/api/admin/upload/calendar`, {
    method: "POST", credentials: "include", body: fd,
  }).then((r) => r.json());
};
