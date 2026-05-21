import { useEffect, useState, useRef } from "react";
import { startSession, askStream, getHistory, fetchSessions } from "../api";
import MessageBubble from "../components/MessageBubble";
import SourceCard from "../components/SourceCard";
import TypingIndicator from "../components/TypingIndicator";

const SUGGESTIONS = [
  { icon: (
      <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
      </svg>
    ), text: "What B.Tech programs does GNDEC offer?" },
  { icon: (
      <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ), text: "How do I apply for admission?" },
  { icon: (
      <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ), text: "Tell me about the CSE department" },
  { icon: (
      <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ), text: "What are the hostel facilities?" },
  { icon: (
      <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ), text: "What is the fee structure?" },
  { icon: (
      <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ), text: "Tell me about placements at GNDEC" },
];

export default function Chat({ phone, sessionId, onBack, onSelectSession }) {
  const [sessions, setSessions]       = useState([]);
  const [messages, setMessages]       = useState([]);
  const [sources, setSources]         = useState([]);
  const [query, setQuery]             = useState("");
  const [loading, setLoading]         = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);
  const inputRef       = useRef(null);

  useEffect(() => {
    fetchSessions(phone).then((d) => setSessions(d.sessions || []));
    startSession(phone, sessionId);
    getHistory(phone, sessionId).then((h) => setMessages(h || []));
  }, [phone, sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage() {
    if (!query.trim() || loading) return;
    const q = query.trim();
    setQuery("");
    setMessages((m) => [...m, { role: "user", message: q }]);
    setSources([]);
    setLoading(true);

    // Don't add empty bubble yet — TypingIndicator shows while waiting
    // Only add the assistant bubble once first content token arrives

    try {
      let bubbleAdded = false;

      await askStream(phone, sessionId, q, (chunk) => {

        if (chunk.type === "sources") {
          setSources(chunk.data || []);
          return;
        }

        if (chunk.type === "blocked") {
          if (!bubbleAdded) {
            setMessages((m) => [...m, { role: "assistant", message: chunk.message }]);
          } else {
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = { role: "assistant", message: chunk.message };
              return copy;
            });
          }
          setLoading(false);
          return;
        }

        if (chunk.type === "content") {
          if (!bubbleAdded) {
            // First token — add the bubble now (replaces TypingIndicator)
            bubbleAdded = true;
            setMessages((m) => [...m, { role: "assistant", message: chunk.data || "" }]);
          } else {
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = {
                role: "assistant",
                message: (copy[copy.length - 1].message || "") + (chunk.data || ""),
              };
              return copy;
            });
          }
        }
      });

      // If stream ended with no content (edge case), add empty bubble
      if (!bubbleAdded) {
        setMessages((m) => [...m, { role: "assistant", message: "I couldn't generate a response. Please try again." }]);
      }
    } catch {
      setMessages((m) => [...m, {
        role: "assistant",
        message: "Sorry, something went wrong. Please try again.",
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  return (
    <div className="flex h-screen bg-[#080808] overflow-hidden">

      {/* ── Background glows ── */}
      <div className="fixed top-0 right-0 w-[500px] h-[500px] bg-[#e11d48]/5 blur-[120px] rounded-full pointer-events-none" />
      <div className="fixed bottom-0 left-0 w-[400px] h-[400px] bg-[#e11d48]/3 blur-[100px] rounded-full pointer-events-none" />

      {/* ══════════════ SIDEBAR ══════════════ */}
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        fixed md:relative z-30 md:z-auto
        ${sidebarOpen ? "md:w-[280px]" : "md:w-0"}
        w-[280px] h-full flex-shrink-0 transition-all duration-300
        bg-[#0e0e0f] border-r border-[#2d2d2d]/30 flex flex-col overflow-hidden
      `}>

        {/* Sidebar header */}
        <div className="px-4 py-4 flex items-center gap-2.5 flex-shrink-0 border-b border-[#2d2d2d]/30">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#e11d48] to-[#9f1239]
                          flex items-center justify-center text-[10px] font-black text-white flex-shrink-0">
            GN
          </div>
          <div className="min-w-0">
            <p className="text-[#e11d48] text-xs font-bold truncate">GNDEC AI</p>
            <p className="text-[#71717a] text-[10px] truncate">{phone}</p>
          </div>
        </div>

        {/* Back button */}
        <div className="px-3 py-2 border-b border-[#2d2d2d]/30 flex-shrink-0">
          <button
            onClick={onBack}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg
                       text-[#94a3b8] hover:text-[#f8fafc] hover:bg-[#121212] transition text-xs"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            All Conversations
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5">
          <p className="text-[10px] text-[#71717a] uppercase tracking-widest px-1 mb-2 font-medium">
            Past Sessions
          </p>
          {sessions.map((sid, i) => (
            <button
              key={i}
              onClick={() => onSelectSession(sid)}
              className={`w-full px-3 py-2.5 rounded-xl text-left text-xs transition group
                ${sid === sessionId
                  ? "bg-[#e11d48]/10 border border-[#e11d48]/20 text-[#e11d48] glow-primary"
                  : "text-[#94a3b8] hover:bg-[#121212] hover:text-[#f8fafc] border border-transparent"
                }`}
            >
              <span className="font-medium block">Chat {i + 1}</span>
              <span className="text-[9px] opacity-50 truncate block mt-0.5">{sid.slice(0, 14)}…</span>
            </button>
          ))}
        </div>

        {/* New discussion */}
        <div className="px-3 py-3 border-t border-[#2d2d2d]/30 flex-shrink-0">
          <button
            onClick={() => onSelectSession(Date.now().toString())}
            className="w-full py-2 rounded-xl bg-[#e11d48] hover:bg-[#be123c]
                       text-white text-xs font-semibold transition-all active:scale-95
                       flex items-center justify-center gap-1.5 shadow-lg shadow-[#e11d48]/20"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Discussion
          </button>
        </div>
      </aside>

      {/* ══════════════ MAIN AREA ══════════════ */}
      <div className="flex flex-col flex-1 min-w-0 relative">

        {/* Top header bar */}
        <header className="flex items-center gap-3 px-4 py-3 bg-[#080808]/80 backdrop-blur-xl
                           border-b border-[#2d2d2d]/30 flex-shrink-0 z-10">
          {/* Hamburger toggle */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg text-[#71717a] hover:text-[#f8fafc] hover:bg-[#121212] transition"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          {/* Title */}
          <div className="flex items-center gap-2.5 flex-1 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-[#e11d48] flex items-center justify-center text-[10px] font-black text-white flex-shrink-0">
              GN
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold text-[#e11d48] truncate">GNDEC College Assistant</p>
              <p className="text-[10px] text-[#71717a] truncate hidden sm:block">
                Guru Nanak Dev Engineering College, Ludhiana
              </p>
            </div>
          </div>

          {/* Online indicator */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-green-900/20 border border-green-700/20 flex-shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <span className="text-[10px] text-green-400 font-medium">Online</span>
          </div>
        </header>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 py-4 bg-[#080808]">

          {/* Empty state */}
          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full gap-6 max-w-lg mx-auto">
              <div className="text-center">
                <div className="w-20 h-20 rounded-3xl bg-[#121212] border border-[#e11d48]/20
                                flex items-center justify-center mx-auto mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-9 h-9 text-[#e11d48]/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
                  </svg>
                </div>
                <h3 className="text-[#f8fafc] font-bold text-lg">How can I help you?</h3>
                <p className="text-[#71717a] text-sm mt-1.5">
                  Ask me anything about GNDEC — admissions, departments, facilities, and more.
                </p>
              </div>

              {/* Suggestion chips grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s.text}
                    onClick={() => { setQuery(s.text); inputRef.current?.focus(); }}
                    className="text-left px-3.5 py-2.5 rounded-xl bg-[#0e0e0f] border border-[#2d2d2d]/40
                               hover:border-[#e11d48]/30 hover:bg-[#121212] transition text-xs text-[#94a3b8]
                               hover:text-[#f8fafc] group flex items-start gap-2"
                  >
                    <span className="text-[#e11d48]/50 group-hover:text-[#e11d48]/80 mt-0.5 flex-shrink-0 transition">
                      {s.icon}
                    </span>
                    {s.text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} text={m.message} />
          ))}
          {/* TypingIndicator shows while waiting for first token */}
          {loading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>

        {/* Sources panel */}
        {sources.length > 0 && (
          <div className="px-4 py-2.5 border-t border-[#2d2d2d]/30 bg-[#080808]">
            <p className="text-[11px] text-[#e11d48] font-semibold mb-2 flex items-center gap-1.5">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              Knowledge Sources
            </p>
            <div className="flex flex-wrap gap-2">
              {sources.slice(0, 4).map((s, i) => (
                <SourceCard key={i} s={s} />
              ))}
            </div>
          </div>
        )}

        {/* Input bar */}
        <div className="px-4 py-3 flex-shrink-0 bg-gradient-to-t from-[#080808] via-[#080808]/90 to-transparent">
          <div className="flex gap-2 items-end max-w-4xl mx-auto">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                rows={1}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  // Auto-resize
                  e.target.style.height = "auto";
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
                }}
                onKeyDown={handleKeyDown}
                placeholder="Ask about GNDEC admissions, departments, facilities…"
                className="w-full bg-[#121212]/90 border border-[#2d2d2d]/40 text-[#f8fafc] text-sm
                           px-4 py-3 rounded-3xl resize-none outline-none leading-relaxed glass-effect
                           placeholder-[#52525b] focus:border-[#e11d48]/50 focus:ring-2 focus:ring-[#e11d48]/10"
                style={{ minHeight: "46px", maxHeight: "120px" }}
              />
            </div>

            <button
              onClick={sendMessage}
              disabled={loading || !query.trim()}
              className={`w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center transition-all active:scale-95
                ${loading || !query.trim()
                  ? "bg-[#1c1c1d] text-[#52525b] cursor-not-allowed"
                  : "bg-[#e11d48] hover:bg-[#be123c] text-white shadow-lg shadow-[#e11d48]/25"
                }`}
            >
              {loading ? (
                <svg className="w-4 h-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
          <p className="text-[10px] text-[#3f3f46] text-center mt-1.5">
            Press{" "}
            <kbd className="px-1 py-0.5 rounded bg-[#1c1c1d] border border-[#2d2d2d] text-[#71717a] font-mono text-[9px]">Enter</kbd>
            {" "}to send ·{" "}
            <kbd className="px-1 py-0.5 rounded bg-[#1c1c1d] border border-[#2d2d2d] text-[#71717a] font-mono text-[9px]">Shift+Enter</kbd>
            {" "}for new line
          </p>
        </div>
      </div>
    </div>
  );
}
