import { Bot } from "lucide-react";

export default function TypingIndicator() {
  return (
    <div className="my-2.5 flex items-end justify-start gap-2">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.06] text-rose-200">
        <Bot className="h-4 w-4" />
      </div>
      <div className="glass-card flex items-center gap-1.5 rounded-[1.35rem] rounded-tl-md px-4 py-3">
        <span className="typing-dot block h-2 w-2 rounded-full bg-rose-300" />
        <span className="typing-dot block h-2 w-2 rounded-full bg-teal-300" />
        <span className="typing-dot block h-2 w-2 rounded-full bg-amber-300" />
      </div>
    </div>
  );
}
