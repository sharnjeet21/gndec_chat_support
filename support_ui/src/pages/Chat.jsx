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
        <span className="text-[10px] font-bold text-slate-400 mb-1">Ai-Assistant</span>
        <div className="flex gap-1.5 px-1 py-2">
          <span className="typing-dot block h-1.5 w-1.5 rounded-full bg-slate-400" />
          <span className="typing-dot block h-1.5 w-1.5 rounded-full bg-slate-400" />
          <span className="typing-dot block h-1.5 w-1.5 rounded-full bg-slate-400" />
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
    <div className="glass-panel min-w-[200px] max-w-[240px] rounded-xl px-3 py-2.5 text-xs flex-shrink-0">
      <p className="truncate font-bold text-white" title={s.question}>
        <span className="mr-1.5 inline-flex bg-white/10 px-1 py-0.5 text-[9px] text-teal-300 rounded">[{index}]</span>
        {s.question?.slice(0, 40)}{s.question?.length > 40 ? "…" : ""}
      </p>
      {s.section && <p className="mt-1 flex items-center gap-1.5 truncate text-[10px] text-white/50"><Folder className="h-3 w-3" />{s.section}</p>}
      <a href={link} target="_blank" rel="noopener noreferrer" className="mt-1.5 flex items-center gap-1.5 truncate text-[10px] font-semibold text-teal-400 hover:text-teal-300">
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
    <div className="flex h-screen font-sans md:p-3 md:gap-4 overflow-hidden text-white relative">
      {/* Sidebar */}
      <aside className="w-[280px] flex flex-col shrink-0 hidden md:flex pt-2 z-10">
        <div className="px-4 pb-4 flex items-center gap-3">
           <button onClick={onBack} className="p-2 hover:bg-white/10 rounded-xl text-white/70"><ChevronLeft className="w-5 h-5"/></button>
           <div>
             <p className="font-bold text-sm">GNDEC Chat</p>
             <p className="text-[10px] text-white/50">{phone}</p>
           </div>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-2 space-y-2">
          {sessions.map((sid, i) => (
            <button key={sid||i} onClick={() => onSelectSession(sid)} className={`w-full text-left px-4 py-3 rounded-2xl text-xs transition-colors ${sid === sessionId ? "bg-white/20 font-semibold shadow-sm backdrop-blur-md" : "text-white/70 hover:bg-white/10"}`}>
              Chat {i + 1}
            </button>
          ))}
        </div>
        <div className="p-4">
           <button onClick={() => onSelectSession(Date.now().toString())} className="w-full flex items-center justify-center gap-2 py-3.5 rounded-[1.25rem] bg-teal-500/80 text-white text-sm font-bold hover:bg-teal-500 hover:shadow-lg transition-all">
             <Plus className="w-4 h-4"/> New Chat
           </button>
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative overflow-hidden glass-panel md:rounded-[2.5rem] z-10">
        {/* Header */}
        <header className="flex justify-center items-center h-16 shrink-0 bg-transparent z-10 sticky top-0">
           <h2 className="font-bold text-white">Chat</h2>
           {/* Mobile back button */}
           <button onClick={onBack} className="absolute left-4 p-2 text-white/70 md:hidden"><ChevronLeft className="w-5 h-5"/></button>
        </header>

        {/* Messages */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 pb-4">
          <div className="max-w-2xl mx-auto flex flex-col justify-end min-h-full">
            {messages.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center py-10 space-y-6 mt-10">
                <div className="text-center text-white/50 text-sm">Start by asking a question about GNDEC!</div>
                <div className="flex flex-wrap justify-center gap-3 max-w-lg">
                  {SUGGESTED_QUESTIONS.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => submitQuery(q)}
                      className="px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-xs border border-white/10 transition-colors"
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
        <div className="shrink-0 p-4 sm:p-6 w-full z-20">
          <div className="max-w-3xl mx-auto flex flex-col gap-3">
            
            {/* Sources Row */}
            {sources.length > 0 && (
              <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                {sources.map((s, i) => <SourceCard key={i} s={s} index={i+1}/>)}
              </div>
            )}

            <div className="flex items-center gap-2 glass-input backdrop-blur-md shadow-[0_10px_40px_rgba(0,0,0,0.2)] rounded-[2rem] p-2 pl-6">
              <input 
                className="flex-1 bg-transparent border-none outline-none text-[15px] text-white placeholder:text-white/50"
                placeholder="Message"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendMessage()}
              />
              <select 
                value={speechLang} 
                onChange={(e) => setSpeechLang(e.target.value)}
                className="bg-transparent border-none outline-none text-[13px] text-white/50 cursor-pointer hover:text-white transition-colors"
                title="Select Speech Language"
              >
                <option value="en-IN" className="bg-slate-900 text-white">English</option>
                <option value="hi-IN" className="bg-slate-900 text-white">Hindi (हिंदी)</option>
                <option value="pa-IN" className="bg-slate-900 text-white">Punjabi (ਪੰਜਾਬੀ)</option>
              </select>
              <button 
                onClick={toggleSpeech}
                className={`p-3 rounded-full transition-colors ${isListening ? "bg-rose-500/80 text-white animate-pulse shadow-[0_0_15px_rgba(244,63,94,0.5)]" : "bg-white/10 text-white/70 hover:bg-white/20"}`}
              >
                <Mic className="w-4 h-4"/>
              </button>
              <button 
                onClick={sendMessage}
                disabled={loading || !query.trim()}
                className={`p-3 rounded-full transition-colors ${loading || !query.trim() ? "bg-white/5 text-white/20 cursor-not-allowed" : "bg-teal-500 text-white shadow-[0_4px_20px_rgba(20,184,166,0.4)] hover:bg-teal-400 hover:scale-105"}`}
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
