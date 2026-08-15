import { useState } from "react";
import { ArrowRight, Phone } from "lucide-react";

export default function Login({ onLogin }) {
  const [phone, setPhone] = useState("");

  return (
    <div className="min-h-screen flex items-center justify-center p-4 font-sans text-[#012529] bg-[#F8F8F8]">
      <main className="w-full max-w-sm bg-[#F3EBD7] border border-[#DCE5E4] shadow-md rounded-[2.5rem] p-8 flex flex-col items-center relative overflow-hidden">
        
        {/* Top Status Bar (fake) */}
        <div className="w-full flex justify-between items-center text-xs font-semibold text-[#BFBACE] mb-8">
          <span>9:41</span>
          <div className="flex gap-1.5 items-center">
            <div className="w-4 h-3 bg-[#BFBACE] rounded-sm" />
            <div className="w-3 h-3 rounded-full bg-[#BFBACE]" />
            <div className="w-6 h-3 border-2 border-[#BFBACE] rounded-sm relative">
               <div className="absolute left-0 top-0 bottom-0 w-3/4 bg-[#BFBACE]" />
            </div>
          </div>
        </div>

        {/* The GNDEC Logo */}
        <div className="relative mb-6 shrink-0 flex justify-center items-center">
          <img src="https://upload.wikimedia.org/wikipedia/en/3/30/Guru_Nanak_Dev_Engineering_College_logo.png" alt="GNDEC Logo" className="w-32 h-32" />
        </div>

        {/* Headings */}
        <h1 className="text-3xl font-extrabold tracking-tight text-center leading-tight mb-4 text-[#012529]">
          GNDEC <span className="text-[#F1845E]">Support</span>
        </h1>

        <p className="text-[13px] text-[#012529]/70 text-center mb-8 px-4 leading-relaxed font-medium">
          Get instant AI assistance regarding admissions, syllabus, and college details.
        </p>

        {/* Input & CTA */}
        <div className="w-full flex flex-col gap-3">
          <div className="relative w-full">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                <Phone className="w-4 h-4 text-[#C0C0C0]" />
            </div>
            <input 
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && phone && onLogin(phone)}
              placeholder="Your Phone Number"
              className="w-full bg-[#F8F8F8] border border-[#BFBACE] text-[#012529] rounded-[1.2rem] pl-11 pr-4 py-4 text-sm font-semibold outline-none focus:ring-2 focus:ring-[#8B7A30]/50 placeholder:text-[#C0C0C0] shadow-sm"
            />
          </div>
          <button 
            onClick={() => phone && onLogin(phone)}
            disabled={!phone}
            className={`w-full rounded-[1.2rem] py-4 text-sm font-bold flex items-center justify-center gap-2 transition-all ${
              phone ? "bg-[#012529] text-[#F8F8F8] shadow-md hover:bg-[#012529]/90 hover:scale-[1.02]" : "bg-[#DCE5E4] text-[#C0C0C0] cursor-not-allowed"
            }`}
          >
            Start Chat <ArrowRight className="w-4 h-4" />
          </button>
        </div>

      </main>
    </div>
  );
}
