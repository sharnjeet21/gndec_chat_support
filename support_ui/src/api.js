const BASE_URL = import.meta.env.VITE_API_URL ?? "";
const API_KEY = import.meta.env.VITE_API_KEY || "naman@1234";

/**
 * Common headers for all API requests
 */
function authHeaders(extra = {}) {
  return {
    "X-API-KEY": API_KEY,
    "ngrok-skip-browser-warning": "true",
    ...extra,
  };
}

/* -------------------------
   SESSION
-------------------------- */
export async function startSession(phone, sessionId) {
  return fetch(
    `${BASE_URL}/api/start_session?phone=${encodeURIComponent(phone)}&session_id=${encodeURIComponent(sessionId)}`,
    {
      headers: authHeaders(),
    },
  );
}

/* -------------------------
   ASK (SYNC)
-------------------------- */
export async function askSync(phone, sessionId, q) {
  const res = await fetch(
    `${BASE_URL}/api/ask?phone=${encodeURIComponent(phone)}&session_id=${encodeURIComponent(sessionId)}&q=${encodeURIComponent(q)}`,
    {
      headers: authHeaders(),
    },
  );

  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }

  return res.json();
}

/* -------------------------
   ASK (STREAM)
-------------------------- */
export async function askStream(phone, sessionId, q, onChunk) {
  const res = await fetch(
    `${BASE_URL}/api/ask_stream?phone=${encodeURIComponent(phone)}&session_id=${encodeURIComponent(sessionId)}&q=${encodeURIComponent(q)}`,
    {
      headers: authHeaders(),
    },
  );

  if (!res.body) throw new Error("Stream error: no body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");

  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      if (buffer.trim()) {
        try {
          handleChunk(JSON.parse(buffer.trim()), onChunk);
        } catch {
          console.warn("Unparsed leftover:", buffer);
        }
      }
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n");
    buffer = parts.pop();

    for (const line of parts) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      try {
        handleChunk(JSON.parse(trimmed), onChunk);
      } catch {
        console.warn("Invalid JSON chunk:", trimmed);
      }
    }
  }
}

/* -------------------------
   HISTORY & SESSIONS
-------------------------- */
export async function fetchSessions(phone) {
  const res = await fetch(`${BASE_URL}/api/sessions?phone=${encodeURIComponent(phone)}`, {
    headers: authHeaders(),
  });
  return res.json();
}

export async function getHistory(phone, sessionId) {
  const res = await fetch(
    `${BASE_URL}/api/history?phone=${encodeURIComponent(phone)}&session_id=${encodeURIComponent(sessionId)}`,
    { headers: authHeaders() },
  );
  return res.json();
}

/* -------------------------
   STREAM HANDLER
-------------------------- */
function handleChunk(obj, onChunk) {
  if (!obj || typeof obj !== "object") return;

  switch (obj.type) {
    case "sources":
      onChunk({ type: "sources", data: obj.sources ?? [] });
      break;
    case "content":
      onChunk({ type: "content", data: obj.delta ?? "" });
      break;
    case "blocked":
      onChunk({
        type: "blocked",
        message: obj.message ?? "Request blocked.",
      });
      break;
    default:
      console.warn("Unknown chunk type:", obj);
  }
}
