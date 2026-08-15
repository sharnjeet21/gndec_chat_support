import { useState } from "react";
import { ArrowRight, Phone } from "lucide-react";

export default function Login({ onLogin }) {
  const [phone, setPhone] = useState("");

  return (
    <div className="min-h-screen flex items-center justify-center p-4 font-sans text-white">
      <main className="w-full max-w-sm glass-panel rounded-[2.5rem] p-8 flex flex-col items-center relative overflow-hidden">
        
        {/* Top Status Bar (fake) */}
        <div className="w-full flex justify-between items-center text-xs font-semibold text-white/50 mb-8">
          <span>9:41</span>
          <div className="flex gap-1.5 items-center">
            <div className="w-4 h-3 bg-white/80 rounded-sm" />
            <div className="w-3 h-3 rounded-full bg-white/80" />
            <div className="w-6 h-3 border-2 border-white/60 rounded-sm relative">
               <div className="absolute left-0 top-0 bottom-0 w-3/4 bg-white/80" />
            </div>
          </div>
        </div>

        {/* Headings */}
        <h1 className="text-3xl font-extrabold tracking-tight text-center leading-tight mb-8">
          Your <span className="text-teal-400">Smart</span><br/>
          <span className="text-teal-400">Assistant</span> for<br/>
          Any Tasks
        </h1>

        {/* Hello badge */}
        <div className="relative w-full flex justify-center mb-2 z-10">
            <div className="bg-white/10 backdrop-blur-md shadow-[0_8px_30px_rgba(0,0,0,0.2)] border border-white/20 rounded-2xl px-4 py-2 text-sm font-bold text-white absolute -left-2 top-2 rotate-[-5deg]">
                Hello!
            </div>
        </div>

        {/* The Avatar Orb */}
        <div className="relative w-40 h-40 mb-10 shrink-0">
          <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-rose-400 via-fuchsia-500 to-indigo-500 blur-md opacity-90 scale-105" />
          <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-pink-400 via-purple-500 to-orange-400 shadow-[inset_0_-10px_20px_rgba(255,255,255,0.4)]" />
          {/* Eyes */}
          <div className="absolute top-[40%] left-1/2 -translate-x-1/2 flex gap-4">
             <svg width="14" height="20" viewBox="0 0 14 20" fill="none"><path d="M1.38531 16.903C0.0381373 14.1541 3.51347 10.6033 5.48536 8.35821L6.72145 6.95111C7.21855 6.38521 8.13283 6.4673 8.52046 7.11292L13.1362 14.8023C14.7335 17.4633 11.5173 19.8643 8.84714 18.0051L8.52628 17.7817C6.18244 16.149 3.1952 16.0354 1.38531 16.903Z" fill="white"/></svg>
             <svg width="14" height="20" viewBox="0 0 14 20" fill="none" style={{transform: 'scaleX(-1)'}}><path d="M1.38531 16.903C0.0381373 14.1541 3.51347 10.6033 5.48536 8.35821L6.72145 6.95111C7.21855 6.38521 8.13283 6.4673 8.52046 7.11292L13.1362 14.8023C14.7335 17.4633 11.5173 19.8643 8.84714 18.0051L8.52628 17.7817C6.18244 16.149 3.1952 16.0354 1.38531 16.903Z" fill="white"/></svg>
          </div>
        </div>

        <p className="text-[13px] text-white/70 text-center mb-8 px-4 leading-relaxed font-medium">
          Get instant help and support<br/>with any task or problem
        </p>

        {/* Input & CTA */}
        <div className="w-full flex flex-col gap-3">
          <div className="relative w-full">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                <Phone className="w-4 h-4 text-white/50" />
            </div>
            <input 
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && phone && onLogin(phone)}
              placeholder="Your Phone Number"
              className="w-full glass-input rounded-[1.2rem] pl-11 pr-4 py-4 text-sm font-semibold outline-none focus:ring-2 focus:ring-teal-400/50"
            />
          </div>
          <button 
            onClick={() => phone && onLogin(phone)}
            disabled={!phone}
            className={`w-full rounded-[1.2rem] py-4 text-sm font-bold flex items-center justify-center gap-2 transition-all ${
              phone ? "bg-white text-slate-900 shadow-[0_10px_20px_rgba(255,255,255,0.15)] hover:scale-[1.02]" : "bg-white/10 text-white/30 cursor-not-allowed"
            }`}
          >
            Get started <ArrowRight className="w-4 h-4" />
          </button>
        </div>

      </main>
    </div>
  );
}
