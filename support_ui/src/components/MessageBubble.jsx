import { AlertTriangle, Bot, UserRound } from "lucide-react";

// Strip markdown formatting from text so responses render as plain text
function stripMarkdown(text) {
  if (!text) return "";
  return text
    // Remove bold/italic: **text**, *text*, __text__, _text_
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/__(.+?)__/g, "$1")
    .replace(/_(.+?)_/g, "$1")
    // Remove headers: ## Heading
    .replace(/^#{1,6}\s+/gm, "")
    // Remove inline code: `code`
    .replace(/`(.+?)`/g, "$1")
    // Remove code blocks: ```...```
    .replace(/```[\s\S]*?```/g, "")
    // Remove horizontal rules
    .replace(/^[-*_]{3,}\s*$/gm, "")
    // Convert markdown bullet points (* item, - item) to plain dashes
    .replace(/^[-*]\s+/gm, "- ")
    // Clean up extra blank lines
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export default function MessageBubble({ role, text }) {
  const isUser = role === "user";
  const cleanText = stripMarkdown(text);
  const lines = cleanText?.split("\n") || [];

  const isWarning =
    text?.includes("not related to GNDEC") ||
    text?.includes("cannot assist with that request") ||
    text?.includes("safety guidelines") ||
    text?.includes("unrelated to GNDEC");

  let bubbleClass = "";
  if (isUser) {
    bubbleClass = "bg-rose-600 border border-rose-200/20 text-white rounded-[1.35rem] rounded-tr-md shadow-lg shadow-rose-950/20";
  } else if (isWarning) {
    bubbleClass = "bg-amber-500/12 border border-amber-300/25 text-amber-100 rounded-[1.35rem] rounded-tl-md";
  } else {
    bubbleClass = "glass-card text-slate-100 rounded-[1.35rem] rounded-tl-md";
  }

  return (
    <div className={`flex my-2.5 items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.06] text-rose-200">
          {isWarning ? <AlertTriangle className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </div>
      )}

      <div className={`max-w-[84%] px-4 py-3 text-sm leading-relaxed sm:max-w-[76%] ${bubbleClass}`}>
        {lines.map((line, i) => (
          <span key={i}>
            {line}
            {i < lines.length - 1 && <br />}
          </span>
        ))}
      </div>

      {isUser && (
        <div className="brand-mark mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl text-white">
          <UserRound className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}
