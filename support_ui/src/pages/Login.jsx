import { useState } from "react";

export default function Login({ onLogin }) {
  const [phone, setPhone] = useState("");

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#080808] relative overflow-hidden">

      {/* Decorative blur blobs */}
      <div className="fixed top-0 right-0 w-[480px] h-[480px] bg-[#e11d48] opacity-[0.07] rounded-full blur-[120px] pointer-events-none" />
      <div className="fixed bottom-0 left-0 w-[360px] h-[360px] bg-[#9f1239] opacity-[0.05] rounded-full blur-[100px] pointer-events-none" />

      <div className="relative z-10 w-full max-w-sm mx-4">

        {/* Glass card */}
        <div className="backdrop-blur-xl bg-[#121212]/70 border border-[#e11d48]/10 rounded-3xl p-8 shadow-2xl">

          {/* GN Avatar */}
          <div className="flex flex-col items-center gap-4 mb-6">
            <div
              className="w-16 h-16 rounded-full bg-[#e11d48] flex items-center justify-center"
              style={{ boxShadow: "0 0 24px rgba(225,29,72,0.45), 0 0 48px rgba(225,29,72,0.15)" }}
            >
              <span className="text-white font-black text-xl tracking-tight">GN</span>
            </div>
            <div className="text-center">
              <h1 className="text-[#f8fafc] font-bold text-lg leading-tight">GNDEC Assistant</h1>
              <p className="text-[#94a3b8] text-xs mt-0.5">Guru Nanak Dev Engineering College</p>
              <p className="text-[#71717a] text-[11px]">Ludhiana, Punjab</p>
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-[#2d2d2d] mb-6" />

          {/* Form */}
          <div className="flex flex-col gap-4">
            <p className="text-[#94a3b8] text-sm text-center">
              Enter your phone number to start
            </p>

            <div>
              <label className="block text-xs text-[#71717a] mb-1.5 font-medium">
                Phone Number
              </label>
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && phone && onLogin(phone)}
                placeholder="e.g. 9876543210"
                className="w-full bg-[#0a0a0b] border border-[#3f3f46]/50 text-[#f8fafc] px-4 py-3
                           rounded-xl text-sm outline-none placeholder-[#52525b]
                           focus:border-[#e11d48]/60 focus:ring-2 focus:ring-[#e11d48]/10"
              />
            </div>

            <button
              onClick={() => phone && onLogin(phone)}
              disabled={!phone}
              className={`w-full py-3 rounded-xl text-sm font-semibold transition-all active:scale-95
                ${phone
                  ? "bg-[#e11d48] hover:bg-[#be123c] text-white shadow-lg shadow-[#e11d48]/20"
                  : "bg-[#1c1c1d] text-[#52525b] cursor-not-allowed"
                }`}
            >
              Continue →
            </button>

            {/* Topic chips */}
            <div className="border-t border-[#2d2d2d] pt-4">
              <p className="text-[11px] text-[#71717a] text-center mb-2.5">You can ask about</p>
              <div className="flex flex-wrap gap-1.5 justify-center">
                {["Admissions", "Departments", "Hostel", "Placements", "Fees", "Events"].map((t) => (
                  <span
                    key={t}
                    className="text-[10px] px-2.5 py-1 rounded-full bg-[#1a1a1c]/50 border border-[#3f3f46]/30
                               text-[#94a3b8] hover:border-[#e11d48]/50 hover:text-[#f8fafc] cursor-default transition"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        <p className="text-center text-[11px] text-[#3f3f46] mt-4">
          Powered by GNDEC AI · gndec.ac.in
        </p>
      </div>
    </div>
  );
}
