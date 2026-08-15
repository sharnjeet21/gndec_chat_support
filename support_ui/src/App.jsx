import { useState, useEffect } from "react";
import Chat from "./pages/Chat";

function getGuestId() {
  let guestId = localStorage.getItem("gndec_guest_id");
  if (!guestId) {
    guestId = "guest_" + Math.random().toString(36).substring(2, 10);
    localStorage.setItem("gndec_guest_id", guestId);
  }
  return guestId;
}

export default function App() {
  const [sessionId, setSessionId] = useState("");
  const guestId = getGuestId();

  useEffect(() => {
    // Generate initial session id or load from sessionStorage
    const stored = sessionStorage.getItem("gndec_session_id");
    if (stored) {
      setSessionId(stored);
    } else {
      const newSession = Date.now().toString();
      sessionStorage.setItem("gndec_session_id", newSession);
      setSessionId(newSession);
    }
  }, []);

  const handleSelectSession = (id) => {
    sessionStorage.setItem("gndec_session_id", id);
    setSessionId(id);
  };

  if (!sessionId) return null;

  return (
    <Chat
      phone={guestId}
      sessionId={sessionId}
      onBack={() => {}}
      onSelectSession={handleSelectSession} 
    />
  );
}
