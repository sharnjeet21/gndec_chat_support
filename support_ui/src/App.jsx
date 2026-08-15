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
    // Generate initial session id
    setSessionId(Date.now().toString());
  }, []);

  if (!sessionId) return null;

  return (
    <Chat
      phone={guestId}
      sessionId={sessionId}
      onBack={() => {}}
      onSelectSession={setSessionId} 
    />
  );
}
