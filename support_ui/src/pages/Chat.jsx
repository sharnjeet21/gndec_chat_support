import { createElement, useEffect, useState, useRef } from "react";
import {
  BookOpen,
  Bot,
  Briefcase,
  Building2,
  ChevronLeft,
  CircleDollarSign,
  FileText,
  GraduationCap,
  Home,
  LoaderCircle,
  Menu,
  MessageCircle,
  Plus,
  Send,
  Sparkles,
} from "lucide-react";
import { startSession, askStream, getHistory, fetchSessions } from "../api";
import MessageBubble from "../components/MessageBubble";
import SourceCard from "../components/SourceCard";
import TypingIndicator from "../components/TypingIndicator";

const SUGGESTIONS = [
  { icon: GraduationCap, text: "What B.Tech programs does GNDEC offer?" },
  { icon: FileText, text: "How do I apply for admission?" },
  { icon: Building2, text: "Tell me about the CSE department" },
  { icon: Home, text: "What are the hostel facilities?" },
  { icon: CircleDollarSign, text: "What is the fee structure?" },
  { icon: Briefcase, text: "Tell me about placements at GNDEC" },
];

export default function Chat({ phone, sessionId, onBack, onSelectSession }) {
  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [sources, setSources] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

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
    if (inputRef.current) inputRef.current.style.height = "48px";
    setMessages((m) => [...m, { role: "user", message: q }]);
    setSources([]);
    setLoading(true);

    let firstToken = true;

    try {
      await askStream(phone, sessionId, q, (chunk) => {
        if (chunk.type === "sources") {
          setSources(chunk.data || []);
          return;
        }

        if (chunk.type === "blocked") {
          setMessages((m) => [...m, { role: "assistant", message: chunk.message }]);
          setLoading(false);
          return;
        }

        if (chunk.type === "content") {
          if (firstToken) {
            firstToken = false;
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
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", message: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function switchSession(sid) {
    onSelectSession(sid);
    setSidebarOpen(false);
  }

  function startNewSession() {
    onSelectSession(Date.now().toString());
    setSidebarOpen(false);
  }

  return (
    <div className="screen-bg flex h-screen overflow-hidden text-slate-100">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close conversations"
          className="fixed inset-0 z-20 bg-black/55 backdrop-blur-sm md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`
          ${sidebarOpen ? "translate-x-0 md:w-[300px]" : "-translate-x-full md:translate-x-0 md:w-0"}
          fixed inset-y-0 left-0 z-30 flex h-full w-[300px] shrink-0 flex-col overflow-hidden
          border-r border-white/10 bg-black/25 backdrop-blur-2xl transition-all duration-300
          md:relative md:z-auto
        `}
      >
        <div className="border-b border-white/10 px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="brand-mark flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-xs font-black text-white">
              GN
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-black text-white">GNDEC AI</p>
              <p className="truncate text-[11px] text-slate-400">{phone}</p>
            </div>
          </div>
        </div>

        <div className="border-b border-white/10 px-3 py-3">
          <button
            onClick={onBack}
            className="flex w-full items-center gap-2 rounded-2xl px-3 py-2.5 text-xs font-semibold text-slate-300 hover:bg-white/[0.06] hover:text-white"
          >
            <ChevronLeft className="h-4 w-4" />
            All Conversations
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-4">
          <div className="mb-3 flex items-center justify-between px-1">
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">
              Sessions
            </p>
            <span className="rounded-full border border-white/10 bg-white/[0.05] px-2 py-0.5 text-[10px] text-slate-400">
              {sessions.length}
            </span>
          </div>

          <div className="space-y-2">
            {sessions.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-5 text-center">
                <MessageCircle className="mx-auto h-5 w-5 text-slate-500" />
                <p className="mt-2 text-xs text-slate-500">No saved chats</p>
              </div>
            ) : (
              sessions.map((sid, i) => (
                <button
                  key={sid || i}
                  onClick={() => switchSession(sid)}
                  className={`w-full rounded-2xl border px-3 py-3 text-left text-xs transition group
                    ${sid === sessionId
                      ? "border-rose-300/25 bg-rose-500/[0.12] text-rose-100 soft-ring"
                      : "border-white/[0.08] bg-white/[0.035] text-slate-300 hover:border-white/15 hover:bg-white/[0.07] hover:text-white"
                    }`}
                >
                  <span className="block font-bold">Chat {i + 1}</span>
                  <span className="mt-1 block truncate font-mono text-[10px] opacity-50">
                    {sid.slice(0, 18)}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="border-t border-white/10 p-3">
          <button
            onClick={startNewSession}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-rose-600 px-4 py-3 text-xs font-bold text-white shadow-lg shadow-rose-500/25 hover:bg-rose-500 active:scale-[0.98]"
          >
            <Plus className="h-4 w-4" />
            New Discussion
          </button>
        </div>
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col">
        <header className="z-10 flex shrink-0 items-center gap-3 border-b border-white/10 bg-black/20 px-3 py-3 backdrop-blur-2xl sm:px-5">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle conversations"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-slate-300 hover:bg-white/[0.09] hover:text-white"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="brand-mark flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl text-xs font-black text-white">
              GN
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-black text-white sm:text-base">
                GNDEC College Assistant
              </p>
              <p className="hidden truncate text-[11px] text-slate-400 sm:block">
                Guru Nanak Dev Engineering College, Ludhiana
              </p>
            </div>
          </div>

          <div className="hidden items-center gap-2 rounded-full border border-emerald-300/15 bg-emerald-400/10 px-3 py-2 sm:flex">
            <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(110,231,183,0.8)]" />
            <span className="text-[11px] font-bold text-emerald-200">Online</span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-3 py-5 sm:px-6">
          <div className="mx-auto flex min-h-full w-full max-w-5xl flex-col">
            {messages.length === 0 && !loading && (
              <div className="flex flex-1 items-center justify-center py-8">
                <div className="w-full max-w-3xl">
                  <div className="glass-panel rounded-[2rem] p-6 text-center sm:p-8">
                    <div className="brand-mark mx-auto flex h-16 w-16 items-center justify-center rounded-[1.4rem] text-sm font-black text-white">
                      <Bot className="h-8 w-8" />
                    </div>
                    <p className="mt-5 text-xs font-semibold uppercase tracking-[0.24em] text-teal-200/75">
                      Campus Knowledge Desk
                    </p>
                    <h2 className="mt-2 text-2xl font-black tracking-tight text-white sm:text-3xl">
                      How can I help you?
                    </h2>
                    <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-400">
                      Ask about GNDEC admissions, departments, hostel, placements, fees, events, or campus services.
                    </p>

                    <div className="mt-7 grid gap-2 sm:grid-cols-2">
                      {SUGGESTIONS.map((suggestion) => (
                        <button
                          key={suggestion.text}
                          onClick={() => {
                            setQuery(suggestion.text);
                            inputRef.current?.focus();
                          }}
                          className="glass-card lift-hover flex items-start gap-3 rounded-2xl px-4 py-3 text-left text-xs font-semibold text-slate-200"
                        >
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-rose-500/15 text-rose-200 ring-1 ring-rose-300/20">
                            {createElement(suggestion.icon, { className: "h-4 w-4" })}
                          </span>
                          <span className="pt-1 leading-5">{suggestion.text}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-3">
              {messages.map((m, i) => (
                <MessageBubble key={i} role={m.role} text={m.message} />
              ))}
              {loading && messages[messages.length - 1]?.role !== "assistant" && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </main>

        {sources.length > 0 && (
          <section className="shrink-0 border-t border-white/10 bg-black/20 px-3 py-3 backdrop-blur-2xl sm:px-5">
            <div className="mx-auto max-w-5xl">
              <p className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.18em] text-teal-200/80">
                <BookOpen className="h-3.5 w-3.5" />
                Knowledge Sources
              </p>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {sources.slice(0, 4).map((s, i) => (
                  <SourceCard key={i} s={s} />
                ))}
              </div>
            </div>
          </section>
        )}

        <div className="shrink-0 px-3 pb-4 pt-2 sm:px-5">
          <div className="mx-auto flex max-w-5xl items-end gap-2 rounded-[1.6rem] border border-white/10 bg-black/25 p-2 shadow-2xl shadow-black/30 backdrop-blur-2xl">
            <textarea
              ref={inputRef}
              rows={1}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 130) + "px";
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ask about GNDEC admissions, departments, facilities..."
              className="min-h-12 flex-1 resize-none rounded-[1.25rem] border border-transparent bg-transparent px-4 py-3 text-sm leading-relaxed text-white outline-none placeholder:text-slate-500 focus:border-white/10 focus:bg-white/[0.04]"
              style={{ maxHeight: "130px" }}
            />

            <button
              onClick={sendMessage}
              disabled={loading || !query.trim()}
              aria-label="Send message"
              className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-[1.25rem] active:scale-[0.96]
                ${loading || !query.trim()
                  ? "cursor-not-allowed bg-white/[0.06] text-slate-600"
                  : "bg-rose-600 text-white shadow-lg shadow-rose-500/25 hover:bg-rose-500"
                }`}
            >
              {loading ? (
                <LoaderCircle className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </div>
          <div className="mt-2 flex items-center justify-center gap-1.5 text-[10px] font-medium text-slate-600">
            <Sparkles className="h-3 w-3 text-teal-300/60" />
            GNDEC AI
          </div>
        </div>
      </div>
    </div>
  );
}
