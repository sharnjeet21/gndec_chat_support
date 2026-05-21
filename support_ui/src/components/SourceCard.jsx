export default function SourceCard({ s }) {
  const link = s.doc_url || (s.source_file ? `https://${s.source_file}` : "https://gndec.ac.in");
  const isDoc = s.doc_url && (s.doc_url.endsWith(".pdf") || s.doc_url.endsWith(".docx") || s.doc_url.endsWith(".doc"));

  return (
    <div className="px-3 py-2 bg-[#0e0e0f] border border-[#2d2d2d]/40 rounded-xl text-xs
                    hover:border-[#e11d48]/50 transition max-w-[220px]">
      <p className="text-[#e11d48] font-medium truncate leading-snug" title={s.question}>
        {s.question?.slice(0, 60)}{s.question?.length > 60 ? "…" : ""}
      </p>
      {s.section && (
        <p className="text-[#71717a] text-[10px] mt-0.5 truncate">📂 {s.section}</p>
      )}
      <a
        href={link}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[10px] text-[#e11d48]/70 hover:text-[#e11d48] transition mt-1 block truncate"
      >
        {isDoc ? "📄" : "🔗"} {s.source_file || "gndec.ac.in"}
      </a>
    </div>
  );
}
