// Chat.jsx — College Assistant chatbot with IDE aesthetic
import { useState, useEffect, useRef } from "react";
import { Send, Plus, X, Settings2, Command, MessageSquare } from "lucide-react";
import { streamChat, getConversations, getConversation, setFeedback } from "../api";

const PROGRAMMES = ["BCA", "BBA", "B.Com (H)"];
const LANGUAGES = ["English", "Hindi"];

const SUGGESTIONS = [
  "Check my attendance",
  "Am I eligible for exams?",
  "Today's classes?",
  "Fee refund policy",
];

function genId() { return Math.random().toString(36).slice(2, 14); }

// Simple parser to format steps and bold text
function formatContent(text) {
  if (!text) return null;
  // Convert numbered lists (1., 2., etc) to checklist style
  const parts = text.split(/(?=\n\d+\.\s)/g);
  
  return parts.map((part, i) => {
    const match = part.match(/^\n?(\d+)\.\s(.*)/s);
    if (match) {
      // It's a step
      const rawText = match[2];
      // Format basic bold markdown **text**
      const formattedText = rawText.split(/(\*\*.*?\*\*)/g).map((chunk, j) => {
        if (chunk.startsWith('**') && chunk.endsWith('**')) {
          return <span key={j} style={{ color: "var(--text)", fontWeight: 600 }}>{chunk.slice(2, -2)}</span>;
        }
        return chunk;
      });

      return (
        <div key={i} style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem", paddingLeft: "0.5rem", borderLeft: "1px solid var(--border)" }}>
          <span style={{ color: "var(--primary)" }}>[0{match[1]}]</span>
          <span>{formattedText}</span>
        </div>
      );
    } else {
      // Standard paragraph
      const formattedText = part.split(/(\*\*.*?\*\*)/g).map((chunk, j) => {
        if (chunk.startsWith('**') && chunk.endsWith('**')) {
          return <span key={j} style={{ color: "var(--text)", fontWeight: 600 }}>{chunk.slice(2, -2)}</span>;
        }
        return chunk;
      });
      return <div key={i} style={{ marginBottom: "0.5rem" }}>{formattedText}</div>;
    }
  });
}

export default function Chat({ user }) {
  const [programme, setProgramme] = useState("BCA");
  const [language, setLanguage] = useState("English");
  const [convId, setConvId] = useState(() => genId());
  const [messages, setMessages] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [input, setInput] = useState("");
  const [streamText, setStreamText] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  
  const bottomRef = useRef(null);

  useEffect(() => {
    getConversations().then(setConversations).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

  function newChat() {
    setConvId(genId());
    setMessages([]);
    setStreamText("");
  }

  async function loadConv(id) {
    try {
      const data = await getConversation(id);
      setConvId(id);
      setMessages(data.messages || []);
      setStreamText("");
    } catch {}
  }

  function closeTab(e, id) {
    e.stopPropagation();
    // If it's active, open a new one
    if (id === convId) {
      newChat();
    }
    // Remove from local state
    setConversations(prev => prev.filter(c => c.id !== id));
  }

  async function sendMessage(text) {
    if (!text.trim() || streaming) return;
    const query = text.trim();
    setInput("");
    setStreaming(true);
    setStreamText("");

    setMessages(prev => [...prev, { role: "user", content: query }]);

    let fullText = "";
    let finalMeta = null;

    try {
      for await (const event of streamChat({ query, programme, conv_id: convId, language })) {
        if (event.type === "token") {
          fullText += event.content;
          setStreamText(fullText);
        } else if (event.type === "done") {
          finalMeta = event;
          setConvId(event.conv_id);
        }
      }
    } catch (e) {
      fullText = "ERR: connection_lost";
    }

    setStreamText("");
    setMessages(prev => [
      ...prev,
      {
        role: "assistant",
        content: fullText,
        query_type: finalMeta?.query_type || "general",
        sources: finalMeta?.sources || [],
        query,
        feedback: null,
      },
    ]);
    setStreaming(false);
    getConversations().then(setConversations).catch(() => {});
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  return (
    <div className="main">
      {/* Clean App Header */}
      <div style={{
        padding: "1rem 2rem", borderBottom: "1px solid var(--border)", background: "var(--bg)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0
      }}>
        <h2 style={{ fontSize: "1.25rem", margin: 0, fontWeight: 700, color: "var(--text)" }}>CollegeBot</h2>
        
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {/* History Dropdown */}
          <select 
            className="select" 
            style={{ width: "220px", background: "var(--bg2)", border: "1px solid var(--border)", borderRadius: "8px" }}
            value={convId}
            onChange={e => loadConv(e.target.value)}
          >
            <option value={convId} disabled>Recent Conversations</option>
            {conversations.slice(0, 15).map(c => (
              <option key={c.id} value={c.id}>{c.title}</option>
            ))}
          </select>
          
          {/* Settings Toggle */}
          <div style={{ position: "relative" }}>
            <button className="btn-icon" onClick={() => setShowSettings(!showSettings)} style={{ background: "var(--bg2)", padding: "6px", borderRadius: "8px" }}>
              <Settings2 size={18} />
            </button>
            {showSettings && (
              <div style={{ position: "absolute", right: 0, top: "40px", background: "var(--bg)", border: "1px solid var(--border)", padding: "1.25rem", borderRadius: "12px", zIndex: 10, width: "220px", boxShadow: "0 8px 24px rgba(0,0,0,0.2)" }}>
                <label className="label">Programme</label>
                <select className="select w-full mb-2" value={programme} onChange={e => setProgramme(e.target.value)}>
                  {PROGRAMMES.map(p => <option key={p}>{p}</option>)}
                </select>
                <label className="label">Response Language</label>
                <select className="select w-full" value={language} onChange={e => setLanguage(e.target.value)}>
                  {LANGUAGES.map(l => <option key={l}>{l}</option>)}
                </select>
              </div>
            )}
          </div>

          <button className="btn btn-primary" onClick={newChat} style={{ borderRadius: "8px" }}>
            <Plus size={16} /> New Chat
          </button>
        </div>
      </div>

      {/* Chat Area */}
      <div className="chat-messages" onClick={() => setShowSettings(false)}>
        {messages.length === 0 && !streaming && (
          <div style={{ margin: "auto", textAlign: "center", color: "var(--text-muted)" }}>
            <div style={{ background: "var(--primary-dim)", width: "64px", height: "64px", borderRadius: "16px", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 1.5rem", color: "var(--primary)" }}>
              <MessageSquare size={32} />
            </div>
            <h3 style={{ color: "var(--text)", fontSize: "1.25rem", fontWeight: 600, marginBottom: "0.5rem" }}>How can I help you today?</h3>
            <div style={{ fontSize: "0.95rem" }}>Select a suggestion below or type your question.</div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            {msg.role === "assistant" && (
              <div className="bot-header">
                <span className="bot-name">CollegeBot</span>
                {msg.query_type && <span className="tag-code">{msg.query_type}</span>}
              </div>
            )}
            
            <div className="chat-bubble">
              {msg.role === "assistant" ? formatContent(msg.content) : msg.content}
            </div>
            
            {msg.sources?.length > 0 && (
              <div style={{ marginTop: "0.75rem" }}>
                {msg.sources.map((s, si) => (
                  <span key={si} className="source-chip" title={s.label}>
                    📄 {s.label}
                  </span>
                ))}
              </div>
            )}
            
            {msg.role === "assistant" && (
              <div className="feedback-row">
                <button className={`feedback-btn${msg.feedback === "up" ? " active" : ""}`} onClick={() => setFeedback(convId, i, "up")}>👍</button>
                <button className={`feedback-btn${msg.feedback === "down" ? " active" : ""}`} onClick={() => setFeedback(convId, i, "down")}>👎</button>
              </div>
            )}
          </div>
        ))}

        {streaming && (
          <div className="chat-msg assistant">
             <div className="bot-header"><span className="bot-name">CollegeBot</span></div>
             <div className="chat-bubble loading-log">
               {streamText ? formatContent(streamText) : "Thinking..."}
               <span className="blinking-cursor"></span>
             </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Terminal Input Area */}
      <div className="chat-input-wrapper" onClick={() => setShowSettings(false)}>
        <div className="suggestion-chips">
          {SUGGESTIONS.map(s => (
            <button key={s} className="suggest-chip" onClick={() => sendMessage(s)}>
              {s}
            </button>
          ))}
        </div>
        
        <div className="terminal-input-row">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your question here..."
            rows={1}
            disabled={streaming}
            autoFocus
          />
          <button
            className="btn-icon"
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || streaming}
            style={{ color: input.trim() ? "var(--primary)" : "var(--text-muted)", background: input.trim() ? "var(--primary-dim)" : "transparent", padding: "8px", borderRadius: "8px" }}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
