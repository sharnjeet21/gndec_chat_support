import { useState } from "react";
import Login from "./pages/Login";
import Chat from "./pages/Chat";

export default function App() {
  const [phone, setPhone] = useState("");
  const [sessionId, setSessionId] = useState("");

  function handleLogin(nextPhone) {
    setPhone(nextPhone.trim());
    setSessionId(Date.now().toString());
  }

  if (!phone) return <Login onLogin={handleLogin} />;


  return (
    <Chat
      phone={phone}
      sessionId={sessionId}
      onBack={() => setPhone("")}
      onSelectSession={setSessionId} 
    />
  );
}
