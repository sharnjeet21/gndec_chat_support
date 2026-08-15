import React, { useState } from "react";
import { Volume2, VolumeX } from "lucide-react";

// The Avatar Orb mini version
function OrbAvatar() {
  return (
    <div className="relative w-8 h-8 shrink-0 mr-3 mt-1">
      <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-rose-400 via-fuchsia-500 to-indigo-500 blur-sm opacity-90 scale-110" />
      <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-pink-400 via-purple-500 to-orange-400" />
      {/* Mini Eyes */}
      <div className="absolute top-[35%] left-1/2 -translate-x-1/2 flex gap-[2px]">
        <svg width="6" height="8" viewBox="0 0 14 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M1.38531 16.903C0.0381373 14.1541 3.51347 10.6033 5.48536 8.35821L6.72145 6.95111C7.21855 6.38521 8.13283 6.4673 8.52046 7.11292L13.1362 14.8023C14.7335 17.4633 11.5173 19.8643 8.84714 18.0051L8.52628 17.7817C6.18244 16.149 3.1952 16.0354 1.38531 16.903Z" fill="white"/>
        </svg>
        <svg width="6" height="8" viewBox="0 0 14 20" fill="none" xmlns="http://www.w3.org/2000/svg" style={{transform: 'scaleX(-1)'}}>
          <path d="M1.38531 16.903C0.0381373 14.1541 3.51347 10.6033 5.48536 8.35821L6.72145 6.95111C7.21855 6.38521 8.13283 6.4673 8.52046 7.11292L13.1362 14.8023C14.7335 17.4633 11.5173 19.8643 8.84714 18.0051L8.52628 17.7817C6.18244 16.149 3.1952 16.0354 1.38531 16.903Z" fill="white"/>
        </svg>
      </div>
    </div>
  );
}

export default function MessageBubble({ role, text }) {
  const isAssistant = role === "assistant";
  const [isSpeaking, setIsSpeaking] = useState(false);

  const handleSpeak = () => {
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Attempt to find a high-quality Indian accent voice (en-IN or hi-IN)
    const voices = window.speechSynthesis.getVoices();
    const indianVoice = voices.find(v => 
      v.lang === 'en-IN' || 
      v.lang === 'hi-IN' ||
      v.name.includes("Heera") || 
      v.name.includes("Ravi") || 
      v.name.includes("Veena") || 
      v.name.includes("Rishi") ||
      v.name.includes("Google हिन्दी") ||
      v.name.includes("India")
    ) || voices.find(v => v.name.includes("Google UK English Female")); // Fallback if no Indian voice
    
    if (indianVoice) {
      utterance.voice = indianVoice;
    }
    // Optimize speech rate and pitch for a more natural conversational tone
    utterance.rate = 1.0;
    utterance.pitch = 1.05;

    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  if (isAssistant) {
    return (
      <div className="flex items-start mb-6">
        <OrbAvatar />
        <div className="flex flex-col flex-1 group">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-bold text-[#666]">Ai-Assistant</span>
            <button 
              onClick={handleSpeak}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-[#ddd] text-[#999] hover:text-[#555]"
              title={isSpeaking ? "Stop speaking" : "Read aloud"}
            >
              {isSpeaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            </button>
          </div>
          <div className="bg-[#f1f5f7] border border-[#ddd] rounded-2xl rounded-tl-sm px-5 py-3.5 text-[#333] text-sm leading-relaxed bubble-text whitespace-pre-wrap shadow-sm">
            {text}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-end mb-6">
      <div className="bg-[#890000] rounded-2xl rounded-tr-sm px-5 py-3.5 max-w-[85%] text-[#fff] text-sm leading-relaxed whitespace-pre-wrap shadow-sm">
         {text}
      </div>
    </div>
  );
}
