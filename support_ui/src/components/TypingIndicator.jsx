export default function TypingIndicator() {
  return (
    <div className="flex justify-start my-2 items-end gap-2">
      <div className="w-7 h-7 rounded-full bg-[#121212] border border-[#2d2d2d]
                      flex items-center justify-center text-[10px] font-black text-[#e11d48] flex-shrink-0">
        GN
      </div>
      <div className="px-4 py-3 bg-[#0e0e0f] border border-[#2d2d2d]/30 rounded-2xl rounded-tl-none flex items-center gap-1.5">
        <span className="typing-dot w-2 h-2 bg-[#e11d48] rounded-full block" />
        <span className="typing-dot w-2 h-2 bg-[#e11d48] rounded-full block" />
        <span className="typing-dot w-2 h-2 bg-[#e11d48] rounded-full block" />
      </div>
    </div>
  );
}
