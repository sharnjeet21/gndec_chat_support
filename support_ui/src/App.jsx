import { useState } from "react";
import Login from "./pages/Login";
import Sessions from "./pages/Sessions";
import Chat from "./pages/Chat";

export default function App() {
  const [phone, setPhone] = useState("");
  const [sessionId, setSessionId] = useState("");

  function handleLogin(nextPhone) {
    setPhone(nextPhone.trim());
    setSessionId("");
  }

  if (!phone) return <Login onLogin={handleLogin} />;

  if (!sessionId)
    return (
      <Sessions
        phone={phone}
        onSelectSession={setSessionId}  
      />
    );

  return (
    <Chat
      phone={phone}
      sessionId={sessionId}
      onBack={() => setSessionId("")}
      onSelectSession={setSessionId} 
    />
  );
}
