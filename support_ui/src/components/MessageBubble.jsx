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
    .replace(/^[\*\-]\s+/gm, "- ")
    // Clean up extra blank lines
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export default function MessageBubble({ role, text }) {
  const isUser = role === "user";
  const cleanText = stripMarkdown(text);

  const isWarning =
    text?.includes("not related to GNDEC") ||
    text?.includes("cannot assist with that request") ||
    text?.includes("safety guidelines") ||
    text?.includes("unrelated to GNDEC");

  let bubbleClass = "";
  if (isUser) {
    bubbleClass = "bg-[#121212] border border-[#e11d48]/20 text-[#f8fafc] rounded-2xl rounded-tr-none";
  } else if (isWarning) {
    bubbleClass = "bg-yellow-900/20 border border-yellow-700/30 text-yellow-200 rounded-2xl rounded-tl-none";
  } else {
    bubbleClass = "bg-[#0e0e0f] border border-[#2d2d2d]/30 text-[#f8fafc] rounded-2xl rounded-tl-none";
  }

  return (
    <div className={`flex my-2 ${isUser ? "justify-end" : "justify-start"} items-end gap-2`}>

      {/* Assistant avatar */}
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-[#121212] border border-[#2d2d2d]
                        flex items-center justify-center text-[10px] font-black text-[#e11d48]
                        flex-shrink-0 mb-0.5">
          GN
        </div>
      )}

      <div className={`max-w-[78%] px-4 py-2.5 text-sm shadow-md leading-relaxed ${bubbleClass}`}>
        {cleanText?.split("\n").map((line, i) => (
          <span key={i}>
            {line}
            {i < cleanText.split("\n").length - 1 && <br />}
          </span>
        ))}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="w-7 h-7 rounded-full bg-[#e11d48]
                        flex items-center justify-center text-[10px] font-bold text-white
                        flex-shrink-0 mb-0.5">
          U
        </div>
      )}
    </div>
  );
}
