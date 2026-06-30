"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getToken, getEmail, clearAuth } from "./lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

function CloudIcon() {
  return (
    <div className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center"
      style={{ background: "var(--netsol-blue)" }}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
        <path d="M19 18H6a4 4 0 01-.6-7.95 5.5 5.5 0 0110.9-1.4A4.5 4.5 0 0119 18z" />
      </svg>
    </div>
  );
}

export default function ChatPage() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const [userEmail, setUserEmail] = useState("");

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState("");
  const [file, setFile] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [playingIndex, setPlayingIndex] = useState(null);
  const [ttsLoading, setTtsLoading] = useState(null);

  // chat history
  const [sessions, setSessions] = useState([]);

  const sessionId = useRef(crypto.randomUUID());
  const bottomRef = useRef(null);
  const abortRef = useRef(null);
  const fileInputRef = useRef(null);
  const audioRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunks = useRef([]);

  // ---- AUTH GUARD: verify token on load ----
  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    fetch(`${API_URL}/auth/verify?token=${encodeURIComponent(token)}`)
      .then((res) => {
        if (!res.ok) throw new Error("invalid");
        return res.json();
      })
      .then((data) => {
        setUserEmail(data.user);
        setAuthChecked(true);
        loadSessions(data.user);
      })
      .catch(() => {
        clearAuth();
        router.replace("/login");
      });
  }, [router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  // ---- chat history ----
  async function loadSessions(emailArg) {
    const email = emailArg || userEmail;
    if (!email) return;
    try {
      const res = await fetch(`${API_URL}/sessions/${encodeURIComponent(email)}`);
      const data = await res.json();
      setSessions(data || []);
    } catch (err) {
      console.error("Could not load sessions", err);
    }
  }

  async function openSession(sid) {
    if (isStreaming) stopStreaming();
    stopAudio();
    sessionId.current = sid;
    setMessages([]);
    try {
      const res = await fetch(`${API_URL}/history/${sid}`);
      const data = await res.json();
      setMessages(data || []);
    } catch (err) {
      console.error("Could not load history", err);
    }
  }

  function logout() {
    clearAuth();
    router.replace("/login");
  }

  function newChat() {
    if (isStreaming) stopStreaming();
    stopAudio();
    setMessages([]);
    setInput("");
    setStatus("");
    setFile(null);
    sessionId.current = crypto.randomUUID();
  }

  function stopStreaming() {
    abortRef.current?.abort();
  }

  function stopAudio() {
    const el = audioRef.current;
    if (el) { el.pause(); el.removeAttribute("src"); }
    setPlayingIndex(null);
  }

  async function toggleSpeak(index, text) {
    if (playingIndex === index) { stopAudio(); return; }
    stopAudio();
    setTtsLoading(index);
    try {
      const res = await fetch(`${API_URL}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error("TTS failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const el = audioRef.current;
      el.src = url;
      el.onended = () => { URL.revokeObjectURL(url); setPlayingIndex(null); };
      await el.play();
      setPlayingIndex(index);
    } catch (err) {
      console.error("TTS error:", err);
    } finally {
      setTtsLoading(null);
    }
  }

  async function sendMessage() {
    const text = input.trim();
    if ((!text && !file) || isStreaming) return;

    const isFirstMessage = messages.length === 0;
    const shownText = text || (file ? `📎 ${file.name}` : "");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: shownText },
      { role: "assistant", content: "" },
    ]);
    setInput("");
    setIsStreaming(true);
    setStatus("Thinking...");

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const form = new FormData();
      form.append("message", text || "Please look at the attached file.");
      form.append("session_id", sessionId.current);
      form.append("user_email", userEmail);
      form.append("want_voice_reply", "false");
      if (file) form.append("file", file);

      const res = await fetch(`${API_URL}/chat`, {
        method: "POST", body: form, signal: controller.signal,
      });
      setFile(null);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop();
        for (const evt of events) handleEvent(evt);
      }
      // refresh sidebar after the first message of a new chat
      if (isFirstMessage) loadSessions();
    } catch (err) {
      if (err.name === "AbortError") appendToLastBot(" _(stopped)_");
      else { console.error(err); appendToLastBot("\n[Connection error]"); }
    } finally {
      setIsStreaming(false);
      setStatus("");
      abortRef.current = null;
    }
  }

  function handleEvent(evt) {
    const lines = evt.split("\n");
    let eventType = "message";
    let data = "";
    for (const line of lines) {
      if (line.startsWith("event:")) eventType = line.slice(6).trim();
      else if (line.startsWith("data:")) {
        let part = line.slice(5);
        if (part.startsWith(" ")) part = part.slice(1);
        data += part;
      }
    }
    if (eventType === "status") setStatus(data);
    else if (eventType === "message") {
      setStatus("");
      appendToLastBot(data.replace(/\\n/g, "\n"));
    }
  }

  function appendToLastBot(token) {
    setMessages((prev) => {
      const copy = [...prev];
      const last = copy[copy.length - 1];
      copy[copy.length - 1] = { ...last, content: last.content + token };
      return copy;
    });
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  async function toggleRecording() {
    if (isRecording) { mediaRecorderRef.current?.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      recordedChunks.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.current.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(recordedChunks.current, { type: "audio/webm" });
        await transcribe(blob);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) { console.error("Mic error:", err); alert("Could not access microphone."); }
  }

  async function transcribe(blob) {
    setIsRecording(false);
    setStatus("Transcribing...");
    try {
      const form = new FormData();
      form.append("audio_file", blob, "recording.webm");
      const res = await fetch(`${API_URL}/stt`, { method: "POST", body: form });
      const data = await res.json();
      if (data.text) setInput((prev) => (prev ? prev + " " : "") + data.text);
    } catch (err) { console.error("STT error:", err); }
    finally { setStatus(""); }
  }

  // while verifying token, show nothing (avoids flicker)
  if (!authChecked) {
    return (
      <div className="h-screen flex items-center justify-center text-gray-400 text-sm">
        Loading…
      </div>
    );
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="flex h-screen bg-white">
      <audio ref={audioRef} style={{ display: "none" }} />

      {/* SIDEBAR */}
      <aside className="w-64 shrink-0 border-r border-[var(--border)] flex flex-col bg-[#eef5fb]">
        <div className="p-4 border-b border-[var(--border)]">
          <div className="text-lg font-bold" style={{ color: "var(--netsol-blue)" }}>
            AI Chatbot
          </div>
          <div className="text-xs text-gray-500">Powered by NetSol Assistant</div>
        </div>
        <div className="p-3">
          <button
            onClick={newChat}
            className="w-full rounded-lg px-3 py-2 text-sm text-white font-medium transition hover:opacity-90"
            style={{ background: "var(--netsol-blue)" }}
          >
            + New chat
          </button>
        </div>

        <div className="px-4 mt-2 text-xs text-gray-400 uppercase tracking-wide">History</div>
        <div className="flex-1 overflow-y-auto px-2 mt-1">
          {sessions.length === 0 ? (
            <div className="px-2 text-xs text-gray-400">No saved chats yet</div>
          ) : (
            sessions.map((s) => (
              <button
                key={s.session_id}
                onClick={() => openSession(s.session_id)}
                className={`w-full text-left rounded-lg px-3 py-2 text-sm truncate transition hover:bg-white ${
                  s.session_id === sessionId.current ? "bg-white font-medium" : ""
                }`}
              >
                {s.title || "Untitled chat"}
              </button>
            ))
          )}
        </div>

        {/* user + logout */}
        <div className="border-t border-[var(--border)] p-3">
          <div className="text-xs text-gray-500 truncate mb-2">{userEmail}</div>
          <button
            onClick={logout}
            className="w-full rounded-lg px-3 py-2 text-sm border transition hover:bg-white"
            style={{ color: "#dc2626", borderColor: "#dc2626" }}
          >
            Logout
          </button>
        </div>
      </aside>

      {/* MAIN */}
      <main className="flex flex-1 flex-col">
        <header className="h-14 border-b border-[var(--border)] flex items-center px-6">
          <span className="text-sm font-medium text-gray-700">Assistant</span>
          {isStreaming && (
            <span className="ml-3 text-xs text-gray-400">{status || "typing…"}</span>
          )}
        </header>

        <div className="flex-1 overflow-y-auto">
          {isEmpty ? (
            <div className="h-full flex flex-col items-center justify-center text-center px-6">
              <div className="mb-4"><CloudIcon /></div>
              <h2 className="text-2xl font-semibold text-gray-800">Hi there! Let&apos;s talk</h2>
              <p className="text-sm text-gray-500 mt-2">
                Ask me anything about NetSol — careers, internships, or company info.
              </p>
            </div>
          ) : (
            <div className="mx-auto max-w-4xl flex flex-col gap-5 px-8 py-6">
              {messages.map((m, i) => (
                <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  {m.role === "assistant" && <CloudIcon />}
                  <div className="max-w-[75%]">
                    <div className="rounded-2xl px-4 py-2.5 text-sm leading-relaxed"
                      style={m.role === "user"
                        ? { background: "var(--netsol-blue)", color: "white" }
                        : { background: "var(--bot-bubble)", color: "var(--text)" }}>
                      {m.role === "assistant" ? (
                        m.content ? (
                          <div className="markdown">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                          </div>
                        ) : (
                          <span className="text-gray-400">{status || "…"}</span>
                        )
                      ) : (m.content)}
                    </div>
                    {m.role === "assistant" && m.content && (
                      <div className="flex justify-end mt-1">
                        <button
                          onClick={() => toggleSpeak(i, m.content)}
                          disabled={ttsLoading === i}
                          className="text-xs flex items-center gap-1 rounded-full px-2 py-1 hover:bg-gray-100 transition"
                          style={{ color: "var(--netsol-blue)" }}
                        >
                          {ttsLoading === i ? "⏳" : playingIndex === i ? "⏸ Stop" : "🔊 Listen"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="border-t border-[var(--border)] p-4">
          {file && (
            <div className="mx-auto max-w-4xl mb-2">
              <span className="inline-flex items-center gap-2 text-xs rounded-full px-3 py-1"
                style={{ background: "#eef5fb", color: "var(--netsol-blue)" }}>
                📎 {file.name}
                <button onClick={() => setFile(null)} className="font-bold">✕</button>
              </span>
            </div>
          )}
          <div className="mx-auto flex max-w-4xl gap-2 items-end">
            <input ref={fileInputRef} type="file" accept=".pdf,.docx,.csv,.txt,.pptx"
              style={{ display: "none" }} onChange={(e) => setFile(e.target.files[0] || null)} />
            <button onClick={() => fileInputRef.current?.click()} disabled={isStreaming}
              className="rounded-xl px-3 py-3 text-lg border border-[var(--border)] hover:bg-gray-50 disabled:opacity-40">📎</button>
            <input
              className="flex-1 rounded-xl border border-[var(--border)] px-4 py-3 text-sm outline-none focus:border-[var(--netsol-blue)] focus:ring-1 focus:ring-[var(--netsol-blue)]"
              placeholder={isRecording ? "Listening..." : "Type a message..."}
              value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown} disabled={isStreaming} />
            <button onClick={toggleRecording} disabled={isStreaming}
              className="rounded-xl px-3 py-3 text-lg border disabled:opacity-40"
              style={isRecording
                ? { background: "#dc2626", color: "white", borderColor: "#dc2626" }
                : { borderColor: "var(--border)" }}>
              {isRecording ? "⏺" : "🎤"}
            </button>
            {isStreaming ? (
              <button onClick={stopStreaming}
                className="rounded-xl px-5 py-3 text-sm text-white font-medium transition hover:opacity-90"
                style={{ background: "#dc2626" }}>⏹ Stop</button>
            ) : (
              <button onClick={sendMessage} disabled={!input.trim() && !file}
                className="rounded-xl px-5 py-3 text-sm text-white font-medium transition hover:opacity-90 disabled:opacity-40"
                style={{ background: "var(--netsol-blue)" }}>Send</button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}