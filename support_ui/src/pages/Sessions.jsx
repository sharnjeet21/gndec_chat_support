import { useState, useEffect } from "react";
import { fetchSessions } from "../api";

export default function Sessions({ phone, onSelectSession }) {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    fetchSessions(phone).then((res) => setSessions(res.sessions || []));
  }, [phone]);

  const handleNewSession = () => onSelectSession(Date.now().toString());

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#080808] relative overflow-hidden">

      {/* Decorative blobs */}
      <div className="fixed top-0 right-0 w-[400px] h-[400px] bg-[#e11d48] opacity-[0.06] rounded-full blur-[120px] pointer-events-none" />
      <div className="fixed bottom-0 left-0 w-[300px] h-[300px] bg-[#9f1239] opacity-[0.04] rounded-full blur-[100px] pointer-events-none" />

      <div className="relative z-10 w-full max-w-[480px] mx-4">
        <div className="bg-[#18181b] border border-[#3f3f46]/20 rounded-3xl overflow-hidden shadow-2xl">

          {/* Header banner */}
          <div className="bg-gradient-to-r from-[#4c0519] to-[#881337] px-6 py-6 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/10 border border-white/20
                            flex items-center justify-center text-xs font-black text-white flex-shrink-0">
              GN
            </div>
            <div>
              <h2 className="text-white font-bold text-sm">GNDEC Assistant</h2>
              <p className="text-rose-200/80 text-[11px] mt-0.5">{phone}</p>
            </div>
          </div>

          {/* Session list */}
          <div className="p-4">
            <p className="text-[11px] text-[#71717a] uppercase tracking-widest font-medium mb-3 px-1">
              Your Conversations
            </p>

            <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
              {sessions.length === 0 ? (
                <div className="flex flex-col items-center gap-2 py-10 text-[#52525b]">
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-10 h-10 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                      d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.77 9.77 0 01-4-.84L3 20l1.09-3.27A7.96 7.96 0 013 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <p className="text-sm text-[#71717a]">No conversations yet</p>
                  <p className="text-xs text-[#52525b]">Start a new chat below</p>
                </div>
              ) : (
                sessions.map((sid, i) => (
                  <button
                    key={i}
                    onClick={() => onSelectSession(sid)}
                    className="w-full px-4 py-3 rounded-xl bg-[#1c1c1d] border border-[#3f3f46]/30
                               hover:border-[#e11d48] hover:bg-[#27272a]
                               transition text-left flex items-center gap-3 group"
                  >
                    {/* Numbered circle */}
                    <div className="w-8 h-8 rounded-full bg-rose-900/30 border border-rose-800/30
                                    flex items-center justify-center text-xs font-bold text-rose-400 flex-shrink-0">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-200 group-hover:text-[#f8fafc]">
                        Chat {i + 1}
                      </p>
                      <p className="text-[10px] text-[#71717a] font-mono truncate mt-0.5">{sid}</p>
                    </div>
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-[#52525b] group-hover:text-[#e11d48] flex-shrink-0 transition" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* New conversation */}
          <div className="px-4 pb-4 border-t border-[#2d2d2d]/60 pt-4">
            <button
              onClick={handleNewSession}
              className="w-full py-3 rounded-xl bg-[#e11d48] hover:bg-[#9f1239]
                         text-white text-sm font-semibold transition-all
                         shadow-lg shadow-[#e11d48]/20 active:scale-95
                         flex items-center justify-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Conversation
            </button>
            <p className="text-[11px] text-[#52525b] text-center mt-2">
              Ask about admissions, departments, facilities &amp; more
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
