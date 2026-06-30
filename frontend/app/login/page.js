"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { saveAuth, getToken } from "../lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

// line-style eye icon; shows a slashed eye when the password is visible
function EyeIcon({ open }) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
      {open && <line x1="3" y1="3" x2="21" y2="21" />}
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState("login");        // "login" | "signup"
  const [loginMethod, setLoginMethod] = useState("email"); // "email" | "face"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // camera
  const [cameraOn, setCameraOn] = useState(false);
  const [photo, setPhoto] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const uploadInputRef = useRef(null);
  // already logged in -> chat
  useEffect(() => {
    if (getToken()) router.replace("/");
  }, [router]);

  // cleanup camera on unmount
  useEffect(() => {
    return () => stopCamera();
  }, []);

  // attach stream AFTER <video> renders
  useEffect(() => {
    if (cameraOn && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {});
    }
  }, [cameraOn]);

  async function startCamera() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      setPhoto(null);
      setCameraOn(true);
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
    canvas.toBlob((blob) => { setPhoto(blob); stopCamera(); }, "image/jpeg", 0.9);
  }

  // switch login method, reset camera/photo state
  function switchMethod(method) {
    setError("");
    stopCamera();
    setPhoto(null);
    setLoginMethod(method);
  }

  function switchMode(newMode) {
    setMode(newMode);
    setError("");
    stopCamera();
    setPhoto(null);
    setLoginMethod("email");
  }

  // ---- EMAIL LOGIN ----
  async function emailLogin() {
    setError("");
    if (!email || !password) return setError("Email and password required.");
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
    if (!photo) return setError("Capture a photo first.");
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

  // ---- SIGNUP ----
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
      alert("Registered! You can now log in.");
      switchMode("login");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // reusable camera block
  function CameraBlock({ label }) {
    return (
      <div className="mb-4">
        {cameraOn ? (
          <div className="flex flex-col items-center gap-2">
            <video ref={videoRef} autoPlay playsInline
              className="rounded-lg w-full max-h-56 object-cover bg-black" />
            <button onClick={capturePhoto}
              className="text-sm rounded-lg px-4 py-2 text-white"
              style={{ background: "var(--netsol-blue)" }}>
              📸 Capture
            </button>
          </div>
        ) : photo ? (
          <div className="flex flex-col items-center gap-2">
            <img src={URL.createObjectURL(photo)} alt="captured"
              className="rounded-lg w-full max-h-56 object-cover" />
            <button onClick={startCamera} className="text-xs text-gray-500 underline">
              Retake
            </button>
          </div>
        ) : (
          <button onClick={startCamera}
            className="w-full rounded-lg border border-dashed border-[var(--netsol-blue)] py-3 text-sm"
            style={{ color: "var(--netsol-blue)" }}>
            📷 {label}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#eef5fb] px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-8">
        {/* header */}
        <div className="text-center mb-6">
          <img
            src="/netsol-logo.png"
            alt="NetSol"
            className="h-12 w-auto mx-auto mb-3"
          />
          <h1 className="text-xl font-bold" style={{ color: "var(--netsol-blue)" }}>
            NetSol Assistant
          </h1>
          <p className="text-sm text-gray-500">
            {mode === "login" ? "Sign in to continue" : "Create your account"}
          </p>
        </div>

        {/* mode tabs */}
        <div className="flex mb-6 rounded-lg overflow-hidden border border-[var(--border)]">
          <button onClick={() => switchMode("login")}
            className="flex-1 py-2 text-sm font-medium transition"
            style={mode === "login"
              ? { background: "var(--netsol-blue)", color: "white" }
              : { color: "var(--netsol-blue)" }}>Login</button>
          <button onClick={() => switchMode("signup")}
            className="flex-1 py-2 text-sm font-medium transition"
            style={mode === "signup"
              ? { background: "var(--netsol-blue)", color: "white" }
              : { color: "var(--netsol-blue)" }}>Sign up</button>
        </div>

        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

        {/* ---------------- LOGIN ---------------- */}
        {mode === "login" ? (
          <>
            {loginMethod === "email" ? (
              <>
                <input className="w-full mb-3 rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm outline-none focus:border-[var(--netsol-blue)]"
                  placeholder="Email" type="email" value={email}
                  onChange={(e) => setEmail(e.target.value)} />
                <div className="relative mb-4">
                  <input className="w-full rounded-lg border border-[var(--border)] px-4 py-2.5 pr-10 text-sm outline-none focus:border-[var(--netsol-blue)]"
                    placeholder="Password" type={showPassword ? "text" : "password"} value={password}
                    onChange={(e) => setPassword(e.target.value)} />
                  <button type="button" onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    title={showPassword ? "Hide password" : "Show password"}>
                    <EyeIcon open={showPassword} />
                  </button>
                </div>

                <button onClick={emailLogin} disabled={busy}
                  className="w-full rounded-lg py-2.5 text-sm text-white font-medium disabled:opacity-50 mb-2"
                  style={{ background: "var(--netsol-blue)" }}>
                  {busy ? "..." : "Login"}
                </button>
                <button onClick={() => switchMethod("face")}
                  className="w-full rounded-lg py-2.5 text-sm font-medium border"
                  style={{ color: "var(--netsol-blue)", borderColor: "var(--netsol-blue)" }}>
                  Use Face ID
                </button>
              </>
            ) : (
              <>
                <CameraBlock label="Capture your face to log in" />
                <button onClick={faceLogin} disabled={busy || !photo}
                  className="w-full rounded-lg py-2.5 text-sm text-white font-medium disabled:opacity-40 mb-2"
                  style={{ background: "var(--netsol-blue)" }}>
                  {busy ? "..." : "Login"}
                </button>
                <button onClick={() => switchMethod("email")}
                  className="w-full rounded-lg py-2.5 text-sm font-medium border"
                  style={{ color: "var(--netsol-blue)", borderColor: "var(--netsol-blue)" }}>
                  Login with Email
                </button>
              </>
            )}
          </>
        ) : (
          /* ---------------- SIGN UP ---------------- */
          <>
            <input className="w-full mb-3 rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm outline-none focus:border-[var(--netsol-blue)]"
              placeholder="Email" type="email" value={email}
              onChange={(e) => setEmail(e.target.value)} />
            <div className="relative mb-4">
              <input className="w-full rounded-lg border border-[var(--border)] px-4 py-2.5 pr-10 text-sm outline-none focus:border-[var(--netsol-blue)]"
                placeholder="Password" type={showPassword ? "text" : "password"} value={password}
                onChange={(e) => setPassword(e.target.value)} />
              <button type="button" onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                title={showPassword ? "Hide password" : "Show password"}>
                <EyeIcon open={showPassword} />
              </button>
            </div>
            <CameraBlock label="Capture face to register" />

            {/* OR upload a photo (signup only) */}
            <div className="flex items-center gap-2 mb-4">
              <div className="flex-1 h-px bg-[var(--border)]" />
              <span className="text-xs text-gray-400">or</span>
              <div className="flex-1 h-px bg-[var(--border)]" />
            </div>
            <input
              ref={uploadInputRef}
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={(e) => {
                const f = e.target.files[0];
                if (f) {
                  stopCamera();
                  setPhoto(f); // a File is also a Blob — works directly
                }
              }}
            />
            <button
              onClick={() => uploadInputRef.current?.click()}
              className="w-full rounded-lg border border-dashed border-[var(--netsol-blue)] py-3 text-sm mb-4"
              style={{ color: "var(--netsol-blue)" }}
            >
              ⬆️ Upload a photo instead
            </button>

            <button onClick={signup} disabled={busy}
              className="w-full rounded-lg py-2.5 text-sm text-white font-medium disabled:opacity-50"
              style={{ background: "var(--netsol-blue)" }}>
              {busy ? "..." : "Create Account"}
            </button>
          </>
        )}

        <canvas ref={canvasRef} style={{ display: "none" }} />
      </div>
    </div>
  );
}