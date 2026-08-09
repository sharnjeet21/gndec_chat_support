import { useState, useEffect } from "react";
import { ChevronRight, MessageCircle, Plus, Sparkles, UserRound } from "lucide-react";
import { fetchSessions } from "../api";

export default function Sessions({ phone, onSelectSession }) {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    fetchSessions(phone).then((res) => setSessions(res.sessions || []));
  }, [phone]);

  const handleNewSession = () => onSelectSession(Date.now().toString());

  return (
    <div className="screen-bg flex min-h-screen items-center justify-center px-4 py-8 text-slate-100">
      <div className="relative z-10 w-full max-w-[560px]">
        <div className="glass-panel overflow-hidden rounded-[2rem]">
          <div className="border-b border-white/10 bg-white/[0.04] px-5 py-5 sm:px-6">
            <div className="flex items-center gap-3">
              <div className="brand-mark flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-sm font-black text-white">
              GN
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-teal-200/80">
                  GNDEC Assistant
                </p>
                <h1 className="mt-1 truncate text-xl font-black tracking-tight text-white">
                  Conversations
                </h1>
              </div>
              <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-3 py-2 text-xs text-slate-300 sm:flex">
                <UserRound className="h-3.5 w-3.5 text-rose-200" />
                <span className="max-w-[120px] truncate">{phone}</span>
              </div>
            </div>
          </div>

          <div className="p-4 sm:p-5">
            <div className="mb-3 flex items-center justify-between gap-3 px-1">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">
                Previous Chats
              </p>
              <span className="rounded-full border border-white/10 bg-white/[0.05] px-2.5 py-1 text-[10px] font-semibold text-slate-400">
                {sessions.length}
              </span>
            </div>

            <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
              {sessions.length === 0 ? (
                <div className="glass-card flex flex-col items-center gap-3 rounded-[1.75rem] px-6 py-12 text-center">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-500/15 text-rose-200 ring-1 ring-rose-300/20">
                    <MessageCircle className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-white">No conversations yet</p>
                    <p className="mt-1 text-xs text-slate-400">Start a new chat below</p>
                  </div>
                </div>
              ) : (
                sessions.map((sid, i) => (
                  <button
                    key={i}
                    onClick={() => onSelectSession(sid)}
                    className="glass-card lift-hover group flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-rose-500/15 text-xs font-black text-rose-100 ring-1 ring-rose-300/20">
                      {i + 1}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-bold text-white">
                        Chat {i + 1}
                      </p>
                      <p className="mt-0.5 truncate font-mono text-[10px] text-slate-500">{sid}</p>
                    </div>
                    <ChevronRight className="h-4 w-4 shrink-0 text-slate-500 group-hover:text-rose-200" />
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="border-t border-white/10 bg-white/[0.03] px-4 py-4 sm:px-5">
            <button
              onClick={handleNewSession}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-rose-600 px-4 py-3.5 text-sm font-bold text-white shadow-lg shadow-rose-500/25 hover:bg-rose-500 active:scale-[0.98]"
            >
              <Plus className="h-4 w-4" />
              New Conversation
            </button>
            <p className="mt-3 flex items-center justify-center gap-1.5 text-[11px] text-slate-500">
              <Sparkles className="h-3 w-3 text-teal-300/70" />
              Admissions, departments, facilities, and more
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
