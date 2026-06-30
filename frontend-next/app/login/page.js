"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { saveAuth, getToken } from "../lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // camera
  const [cameraOn, setCameraOn] = useState(false);
  const [photo, setPhoto] = useState(null); // captured Blob
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  // if already logged in, skip to chat
  useEffect(() => {
    if (getToken()) router.replace("/");
  }, [router]);

  // clean up camera when leaving
  useEffect(() => {
    return () => stopCamera();
  }, []);

  async function startCamera() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setCameraOn(true);
      setPhoto(null);
    } catch (err) {
      setError("Could not access camera.");
    }
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCameraOn(false);
  }

  function capturePhoto() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        setPhoto(blob);
        stopCamera();
      },
      "image/jpeg",
      0.9
    );
  }

  // ---- EMAIL + PASSWORD LOGIN ----
  async function emailLogin() {
    setError("");
    setBusy(true);
    try {
      const form = new FormData();
      form.append("email", email);
      form.append("password", password);
      const res = await fetch(`${API_URL}/auth/login`, { method: "POST", body: form });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Login failed");
      }
      const data = await res.json();
      saveAuth(data.token, data.user);
      router.replace("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // ---- FACE LOGIN ----
  async function faceLogin() {
    if (!photo) {
      setError("Capture a photo first.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", photo, "face.jpg");
      const res = await fetch(`${API_URL}/auth/login`, { method: "POST", body: form });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Face not recognized");
      }
      const data = await res.json();
      saveAuth(data.token, data.user);
      router.replace("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // ---- SIGNUP (email + password + face) ----
  async function signup() {
    setError("");
    if (!email || !password) return setError("Email and password required.");
    if (!photo) return setError("Capture a face photo to register.");
    setBusy(true);
    try {
      const form = new FormData();
      form.append("email", email);
      form.append("password", password);
      form.append("file", photo, "face.jpg");
      const res = await fetch(`${API_URL}/auth/register`, { method: "POST", body: form });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Registration failed");
      }
      // registered — now log them in with email+password
      setMode("login");
      setError("");
      alert("Registered! You can now log in.");
      setPhoto(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#eef5fb] px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-8">
        {/* header */}
        <div className="text-center mb-6">
          <div
            className="w-12 h-12 rounded-full mx-auto flex items-center justify-center text-white text-xl font-bold mb-3"
            style={{ background: "var(--netsol-blue)" }}
          >
            AI
          </div>
          <h1 className="text-xl font-bold" style={{ color: "var(--netsol-blue)" }}>
            NetSol Assistant
          </h1>
          <p className="text-sm text-gray-500">
            {mode === "login" ? "Sign in to continue" : "Create your account"}
          </p>
        </div>

        {/* tab toggle */}
        <div className="flex mb-6 rounded-lg overflow-hidden border border-[var(--border)]">
          <button
            onClick={() => { setMode("login"); setError(""); }}
            className="flex-1 py-2 text-sm font-medium transition"
            style={mode === "login"
              ? { background: "var(--netsol-blue)", color: "white" }
              : { color: "var(--netsol-blue)" }}
          >
            Login
          </button>
          <button
            onClick={() => { setMode("signup"); setError(""); }}
            className="flex-1 py-2 text-sm font-medium transition"
            style={mode === "signup"
              ? { background: "var(--netsol-blue)", color: "white" }
              : { color: "var(--netsol-blue)" }}
          >
            Sign up
          </button>
        </div>

        {/* email + password */}
        <input
          className="w-full mb-3 rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm outline-none focus:border-[var(--netsol-blue)]"
          placeholder="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="w-full mb-4 rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm outline-none focus:border-[var(--netsol-blue)]"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {/* camera area */}
        <div className="mb-4">
          {cameraOn ? (
            <div className="flex flex-col items-center gap-2">
              <video ref={videoRef} autoPlay playsInline className="rounded-lg w-full max-h-56 object-cover bg-black" />
              <button
                onClick={capturePhoto}
                className="text-sm rounded-lg px-4 py-2 text-white"
                style={{ background: "var(--netsol-blue)" }}
              >
                📸 Capture
              </button>
            </div>
          ) : photo ? (
            <div className="flex flex-col items-center gap-2">
              <img
                src={URL.createObjectURL(photo)}
                alt="captured"
                className="rounded-lg w-full max-h-56 object-cover"
              />
              <button onClick={startCamera} className="text-xs text-gray-500 underline">
                Retake
              </button>
            </div>
          ) : (
            <button
              onClick={startCamera}
              className="w-full rounded-lg border border-dashed border-[var(--netsol-blue)] py-3 text-sm"
              style={{ color: "var(--netsol-blue)" }}
            >
              📷 {mode === "signup" ? "Capture face to register" : "Use Face ID (optional)"}
            </button>
          )}
        </div>

        <canvas ref={canvasRef} style={{ display: "none" }} />

        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

        {/* action buttons */}
        {mode === "login" ? (
          <div className="flex flex-col gap-2">
            <button
              onClick={emailLogin}
              disabled={busy}
              className="w-full rounded-lg py-2.5 text-sm text-white font-medium disabled:opacity-50"
              style={{ background: "var(--netsol-blue)" }}
            >
              {busy ? "..." : "Login with Email"}
            </button>
            <button
              onClick={faceLogin}
              disabled={busy || !photo}
              className="w-full rounded-lg py-2.5 text-sm font-medium border disabled:opacity-40"
              style={{ color: "var(--netsol-blue)", borderColor: "var(--netsol-blue)" }}
            >
              Login with Face ID
            </button>
          </div>
        ) : (
          <button
            onClick={signup}
            disabled={busy}
            className="w-full rounded-lg py-2.5 text-sm text-white font-medium disabled:opacity-50"
            style={{ background: "var(--netsol-blue)" }}
          >
            {busy ? "..." : "Create Account"}
          </button>
        )}
      </div>
    </div>
  );
}