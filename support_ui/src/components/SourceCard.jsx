import { ExternalLink, FileText, Folder } from "lucide-react";

export default function SourceCard({ s }) {
  const link = s.doc_url || (s.source_file ? `https://${s.source_file}` : "https://gndec.ac.in");
  const isDoc = s.doc_url && (s.doc_url.endsWith(".pdf") || s.doc_url.endsWith(".docx") || s.doc_url.endsWith(".doc"));

  return (
    <div className="glass-card lift-hover min-w-[220px] max-w-[260px] rounded-2xl px-3.5 py-3 text-xs">
      <p className="truncate font-bold leading-snug text-white" title={s.question}>
        {s.question?.slice(0, 60)}{s.question?.length > 60 ? "…" : ""}
      </p>
      {s.section && (
        <p className="mt-2 flex items-center gap-1.5 truncate text-[10px] text-slate-400">
          <Folder className="h-3 w-3 text-teal-200/70" />
          {s.section}
        </p>
      )}
      <a
        href={link}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-2 flex items-center gap-1.5 truncate text-[10px] font-semibold text-rose-200 hover:text-white"
      >
        {isDoc ? <FileText className="h-3 w-3" /> : <ExternalLink className="h-3 w-3" />}
        {s.source_file || "gndec.ac.in"}
      </a>
    </div>
  );
}
