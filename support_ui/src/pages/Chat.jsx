import { createElement, useEffect, useState, useRef } from "react";
import { ChevronLeft, LoaderCircle, Mic, Plus, Send, ExternalLink, FileText, Folder } from "lucide-react";
import { startSession, askStream, getHistory, fetchSessions } from "../api";
import MessageBubble from "../components/MessageBubble";

function OrbAvatar() {
  return (
    <div className="relative w-8 h-8 shrink-0">
      <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-rose-400 via-fuchsia-500 to-indigo-500 blur-sm opacity-90 scale-110" />
      <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-pink-400 via-purple-500 to-orange-400" />
      <div className="absolute top-[35%] left-1/2 -translate-x-1/2 flex gap-[2px]">
        <svg width="6" height="8" viewBox="0 0 14 20" fill="none"><path d="M1.38531 16.903C0.0381373 14.1541 3.51347 10.6033 5.48536 8.35821L6.72145 6.95111C7.21855 6.38521 8.13283 6.4673 8.52046 7.11292L13.1362 14.8023C14.7335 17.4633 11.5173 19.8643 8.84714 18.0051L8.52628 17.7817C6.18244 16.149 3.1952 16.0354 1.38531 16.903Z" fill="white"/></svg>
        <svg width="6" height="8" viewBox="0 0 14 20" fill="none" style={{transform: 'scaleX(-1)'}}><path d="M1.38531 16.903C0.0381373 14.1541 3.51347 10.6033 5.48536 8.35821L6.72145 6.95111C7.21855 6.38521 8.13283 6.4673 8.52046 7.11292L13.1362 14.8023C14.7335 17.4633 11.5173 19.8643 8.84714 18.0051L8.52628 17.7817C6.18244 16.149 3.1952 16.0354 1.38531 16.903Z" fill="white"/></svg>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-start mb-6">
      <OrbAvatar />
      <div className="flex flex-col flex-1">
        <span className="text-[10px] font-bold text-[#666] mb-1">Ai-Assistant</span>
        <div className="flex gap-1.5 px-1 py-2">
          <span className="typing-dot block h-1.5 w-1.5 rounded-full bg-[#0066b3]" />
          <span className="typing-dot block h-1.5 w-1.5 rounded-full bg-[#0066b3]" />
          <span className="typing-dot block h-1.5 w-1.5 rounded-full bg-[#0066b3]" />
        </div>
      </div>
    </div>
  );
}

function SourceCard({ s, index }) {
  let link = "https://gndec.ac.in";
  if (s.doc_url && s.doc_url.startsWith("http")) {
    link = s.doc_url;
  } else if (s.source_file === "faculty.json" || s.section?.toLowerCase().includes("faculty")) {
    link = "https://gndec.ac.in/department";
  } else if (s.source_file === "tnp_data.json" || s.section?.toLowerCase().includes("placement")) {
    link = "https://tpo.gndec.ac.in";
  } else if (s.source_file === "syllabi.json") {
    link = "https://gndec.ac.in/syllabi";
  } else if (s.section?.toLowerCase().includes("admission")) {
    link = "https://admission.gndec.ac.in";
  } else if (s.section?.toLowerCase().includes("alumni")) {
    link = "https://alumni.gndec.ac.in";
  } else if (s.source_file && s.source_file !== "web_search") {
    link = s.source_file.startsWith("http") ? s.source_file : `https://${s.source_file}`;
  }

  const isDoc = s.doc_url && (s.doc_url.endsWith(".pdf") || s.doc_url.endsWith(".docx") || s.doc_url.endsWith(".doc"));
  return (
    <div className="bg-[#ebf3f9] border border-[#0066b3] min-w-[200px] max-w-[240px] rounded-xl px-3 py-2.5 text-xs flex-shrink-0 shadow-sm">
      <p className="truncate font-bold text-[#000]" title={s.question}>
        <span className="mr-1.5 inline-flex bg-[#0066b3] px-1 py-0.5 text-[9px] text-[#fff] rounded">[{index}]</span>
        {s.question?.slice(0, 40)}{s.question?.length > 40 ? "…" : ""}
      </p>
      {s.section && <p className="mt-1 flex items-center gap-1.5 truncate text-[10px] text-[#555]"><Folder className="h-3 w-3" />{s.section}</p>}
      <a href={link} target="_blank" rel="noopener noreferrer" className="mt-1.5 flex items-center gap-1.5 truncate text-[10px] font-semibold text-[#f00] hover:text-[#900]">
        {isDoc ? <FileText className="h-3 w-3" /> : <ExternalLink className="h-3 w-3" />}
        {link.replace("https://", "").replace("http://", "").split("/")[0]}
      </a>
    </div>
  );
}

const SUGGESTED_QUESTIONS = [
  "What B.Tech courses are offered?",
  "How can I apply for admission?",
  "What is the fee structure?",
  "Are there hostel facilities available?"
];

export default function Chat({ phone, sessionId, onBack, onSelectSession }) {
  const [sessions, setSessions] = useState([]);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const [messages, setMessages] = useState([]);
  const [sources, setSources] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  
  const recognitionRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchSessions(phone).then((d) => setSessions(d.sessions || []));
    startSession(phone, sessionId);
    getHistory(phone, sessionId).then((h) => setMessages(h || []));
  }, [phone, sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function submitQuery(text) {
    const q = text.trim();
    if (!q || loading) return;
    setQuery("");
    setMessages((m) => [...m, { role: "user", message: q }]);
    setSources([]);
    setLoading(true);

    let firstToken = true;
    try {
      await askStream(phone, sessionId, q, (chunk) => {
        if (chunk.type === "sources") { setSources(chunk.data || []); return; }
        if (chunk.type === "blocked") { setMessages((m) => [...m, { role: "assistant", message: chunk.message }]); setLoading(false); return; }
        if (chunk.type === "content") {
          if (firstToken) {
            firstToken = false;
            setMessages((m) => [...m, { role: "assistant", message: chunk.data || "" }]);
          } else {
            setMessages((m) => {
              const copy = [...m];
              copy[copy.length - 1] = { role: "assistant", message: (copy[copy.length - 1].message || "") + (chunk.data || "") };
              return copy;
            });
          }
        }
      });
    } catch {
      setMessages((m) => [...m, { role: "assistant", message: "Sorry, an error occurred." }]);
    } finally {
      setLoading(false);
    }
  }

  const [speechLang, setSpeechLang] = useState('en-IN');

  useEffect(() => {
    // Stop any ongoing speech when switching chats
    window.speechSynthesis.cancel();
  }, [sessionId]);

  async function sendMessage() {
    submitQuery(query);
  }

  function toggleSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return alert("Browser does not support Speech Recognition.");
    if (isListening) {
      if (recognitionRef.current) recognitionRef.current.stop();
      setIsListening(false);
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = speechLang;
    recognition.continuous = false;
    recognitionRef.current = recognition;
    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (e) => setQuery((p) => (p ? p + " " + e.results[0][0].transcript : e.results[0][0].transcript));
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognition.start();
  }

  return (
    <div className="flex h-screen font-sans md:p-3 md:gap-4 overflow-hidden text-[#000] relative bg-[#fff8c6]">
      {/* Sidebar */}
      <aside className="w-[280px] flex flex-col shrink-0 hidden md:flex pt-2 z-10">
        <div className="px-4 pb-4 flex items-center gap-2 border-b border-[#ccc]">
           <img src="https://erp.gndec.ac.in/files/gnelogo.png" alt="GNE Logo" className="w-10 h-10 ml-1 opacity-90" />
           <div className="pl-1">
             <p className="font-bold text-sm text-[#000]">GNDEC Chat</p>
             <p className="text-[10px] text-[#666]">Guest Mode</p>
           </div>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {sessions.map((s, i) => {
            const sid = s.id || s;
            const title = s.title || `Chat ${i + 1}`;
            return (
              <button key={sid||i} onClick={() => onSelectSession(sid)} className={`w-full text-left px-4 py-3 rounded-2xl text-xs transition-colors truncate ${sid === sessionId ? "bg-[#0066b3] text-[#fff] font-semibold shadow-md" : "text-[#555] hover:bg-[#eaefcb]"}`} title={title}>
                {title}
              </button>
            );
          })}
        </div>
        <div className="p-4 border-t border-[#ccc]">
           <button onClick={() => onSelectSession(Date.now().toString())} className="w-full flex items-center justify-center gap-2 py-3.5 rounded-[1.25rem] bg-[#008000] text-[#fff] text-sm font-bold hover:bg-[#00aa00] hover:shadow-lg transition-all">
             <Plus className="w-4 h-4"/> New Chat
           </button>
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative overflow-hidden bg-[#fffff0] md:border md:border-[#ccc] md:rounded-[2.5rem] md:shadow-sm z-10">
        {/* Header */}
        <header className="flex justify-center items-center h-16 shrink-0 bg-[#fffff0] border-b border-[#ccc] z-10 sticky top-0 shadow-sm">
           <h2 className="font-bold text-[#0066b3]">GNDEC Support</h2>
        </header>

        {/* Messages */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 pb-4">
          <div className="max-w-2xl mx-auto flex flex-col justify-end min-h-full">
            {messages.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center py-10 space-y-6 mt-10">
                <img src="https://erp.gndec.ac.in/files/gnelogo.png" alt="GNDEC Logo" className="w-24 h-24 mb-2 opacity-80" />
                <div className="text-center text-[#555] text-sm font-medium">How can I help you today?</div>
                <div className="flex flex-wrap justify-center gap-3 max-w-lg">
                  {SUGGESTED_QUESTIONS.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => submitQuery(q)}
                      className="px-4 py-2.5 rounded-xl bg-[#fff] hover:bg-[#ebf3f9] text-[#000] text-xs border border-[#0066b3] transition-colors shadow-sm"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => <MessageBubble key={i} role={m.role} text={m.message} />)}
            {loading && messages[messages.length - 1]?.role !== "assistant" && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        </main>

        {/* Input Bar */}
        <div className="shrink-0 p-4 sm:p-6 w-full z-20 bg-[#fffff0]">
          <div className="max-w-3xl mx-auto flex flex-col gap-3">
            
            {/* Sources Row */}
            {sources.length > 0 && (
              <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                {sources.map((s, i) => <SourceCard key={i} s={s} index={i+1}/>)}
              </div>
            )}

            <div className="flex items-center gap-2 bg-[#fff] border border-[#ccc] shadow-sm rounded-[2rem] p-2 pl-6">
              <input 
                className="flex-1 bg-transparent border-none outline-none text-[15px] text-[#000] placeholder:text-[#888]"
                placeholder="Message GNDEC Agent..."
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendMessage()}
              />
              <select 
                value={speechLang} 
                onChange={(e) => setSpeechLang(e.target.value)}
                className="bg-transparent border-none outline-none text-[13px] text-[#666] cursor-pointer hover:text-[#000] transition-colors"
                title="Select Speech Language"
              >
                <option value="en-IN">English</option>
                <option value="hi-IN">Hindi (हिंदी)</option>
                <option value="pa-IN">Punjabi (ਪੰਜਾਬੀ)</option>
              </select>
              <button 
                onClick={toggleSpeech}
                className={`p-3 rounded-full transition-colors ${isListening ? "bg-[#f00] text-[#fff] animate-pulse shadow-md" : "bg-[#ddd] text-[#555] hover:bg-[#ccc]"}`}
              >
                <Mic className="w-4 h-4"/>
              </button>
              <button 
                onClick={sendMessage}
                disabled={loading || !query.trim()}
                className={`p-3 rounded-full transition-colors ${loading || !query.trim() ? "bg-[#ddd] text-[#999] cursor-not-allowed" : "bg-[#0066b3] text-[#fff] shadow-md hover:bg-[#0072b9] hover:scale-105"}`}
              >
                {loading ? <LoaderCircle className="w-4 h-4 animate-spin"/> : <Send className="w-4 h-4 ml-[-2px]"/>}
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
