"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

declare global {
  interface Window {
    SpeechRecognition?: any;
    webkitSpeechRecognition?: any;
  }
}

type Mode = "idle" | "listening" | "thinking" | "speaking";
type Turn = { role: "user" | "assistant"; content: string };
type BrowserContext = {
  timezone: string;
  locale: string;
  latitude?: number;
  longitude?: number;
  accuracy?: number;
};

function ItachiFace({
  mode,
  onTap,
}: {
  mode: Mode;
  onTap: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pointer = useRef({ x: 0, y: 0, active: false });
  const points = useMemo(() => {
    const output: Array<{ x: number; y: number; z: number; kind: string }> = [];
    const depth = (x: number, y: number) =>
      Math.sqrt(Math.max(0, 1 - Math.min(0.96, x * x * 0.72 + y * y * 0.88))) * 0.32;

    for (let row = 0; row < 24; row++) {
      const y = -1.05 + (row / 23) * 2.12;
      const width = 0.78 * Math.sqrt(Math.max(0.12, 1 - Math.pow(y / 1.18, 2)));
      const count = 8 + Math.round(width * 18);
      for (let i = 0; i < count; i++) {
        const x = -width + (i / Math.max(1, count - 1)) * width * 2;
        output.push({ x, y, z: depth(x, y), kind: "face" });
      }
    }

    for (let i = 0; i < 72; i++) {
      const a = (i / 72) * Math.PI * 2;
      output.push({
        x: Math.cos(a) * 0.82,
        y: Math.sin(a) * 1.12,
        z: 0.03 + 0.08 * Math.sin(a * 3),
        kind: "edge",
      });
    }

    const eye = (cx: number) => {
      for (let i = 0; i < 28; i++) {
        const a = (i / 28) * Math.PI * 2;
        output.push({
          x: cx + Math.cos(a) * 0.20,
          y: -0.23 + Math.sin(a) * 0.075,
          z: 0.38,
          kind: "eye",
        });
      }
      output.push({ x: cx, y: -0.23, z: 0.43, kind: "eye-core" });
    };
    eye(-0.28);
    eye(0.28);

    for (let i = 0; i < 18; i++) {
      output.push({
        x: 0.015 * Math.sin(i * 1.4),
        y: -0.1 + i * 0.035,
        z: 0.40 - i * 0.006,
        kind: "nose",
      });
    }

    for (let i = 0; i < 34; i++) {
      const t = i / 33;
      const x = -0.30 + t * 0.60;
      output.push({
        x,
        y: 0.49 + Math.sin(t * Math.PI) * 0.05,
        z: 0.31,
        kind: "mouth",
      });
    }

    for (let i = 0; i < 90; i++) {
      const a = i * 2.399963;
      const r = 1.15 + (i % 9) * 0.035;
      output.push({
        x: Math.cos(a) * r,
        y: Math.sin(a) * r * 0.82,
        z: -0.28 + (i % 7) * 0.07,
        kind: "aura",
      });
    }

    return output;
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    let frame = 0;
    let yaw = 0;
    let pitch = 0;

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(window.innerWidth * ratio);
      canvas.height = Math.floor(window.innerHeight * ratio);
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };

    const render = (time: number) => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      context.clearRect(0, 0, width, height);

      const autonomousYaw =
        Math.sin(time * 0.00036) * 0.24 + Math.sin(time * 0.00013 + 1.4) * 0.11;
      const autonomousPitch = Math.cos(time * 0.00029) * 0.075;
      const targetYaw =
        autonomousYaw + (pointer.current.active ? pointer.current.x * 0.30 : 0);
      const targetPitch =
        autonomousPitch + (pointer.current.active ? pointer.current.y * 0.13 : 0);
      const speed = mode === "thinking" ? 0.09 : 0.045;
      yaw += (targetYaw - yaw) * speed;
      pitch += (targetPitch - pitch) * speed;

      const cx = width > 980 ? width * 0.34 : width * 0.5;
      const cy = height * 0.49;
      const scale = Math.min(width * (width > 980 ? 0.34 : 0.43), height * 0.42);
      const camera = 3.2;

      const projected = points.map((p, index) => {
        let x = p.x;
        let y = p.y;
        let z = p.z;

        const cyaw = Math.cos(yaw);
        const syaw = Math.sin(yaw);
        const x1 = x * cyaw - z * syaw;
        const z1 = x * syaw + z * cyaw;
        x = x1;
        z = z1;

        const cp = Math.cos(pitch);
        const sp = Math.sin(pitch);
        const y1 = y * cp - z * sp;
        const z2 = y * sp + z * cp;
        y = y1;
        z = z2;

        if (p.kind === "mouth" && mode === "speaking") {
          y += Math.sin(time * 0.016 + index) * 0.022;
        }
        if (p.kind === "eye-core") {
          x += Math.sin(time * 0.0008 + index) * 0.015;
          y += Math.cos(time * 0.00065 + index) * 0.009;
        }

        const perspective = camera / Math.max(1.3, camera - z);
        return {
          ...p,
          sx: cx + x * scale * perspective,
          sy: cy + y * scale * perspective,
          depth: z,
          perspective,
        };
      });

      context.save();
      context.globalCompositeOperation = "lighter";

      for (let i = 0; i < projected.length - 1; i++) {
        const a = projected[i];
        const b = projected[i + 1];
        if (a.kind === "aura" || b.kind === "aura") continue;
        const dx = a.sx - b.sx;
        const dy = a.sy - b.sy;
        if (dx * dx + dy * dy > 2100) continue;
        const alpha = mode === "thinking" ? 0.105 : 0.055;
        context.strokeStyle = `rgba(78,208,219,${alpha})`;
        context.lineWidth = 0.65;
        context.beginPath();
        context.moveTo(a.sx, a.sy);
        context.lineTo(b.sx, b.sy);
        context.stroke();
      }

      projected.sort((a, b) => a.depth - b.depth);
      for (const p of projected) {
        const thinkingPulse =
          mode === "thinking" ? 0.72 + Math.sin(time * 0.008 + p.sx * 0.01) * 0.22 : 0.72;
        const near = Math.max(0.25, Math.min(1, 0.58 + p.depth * 0.8));
        let alpha = near * thinkingPulse;
        let radius = 1.25 * p.perspective;
        if (p.kind === "eye" || p.kind === "eye-core") {
          alpha = 0.96;
          radius *= p.kind === "eye-core" ? 2.9 : 1.75;
        } else if (p.kind === "aura") {
          alpha *= 0.32;
          radius *= 0.75;
        } else if (p.kind === "edge") {
          alpha *= 0.75;
          radius *= 1.12;
        }

        context.fillStyle =
          p.kind === "eye-core"
            ? `rgba(183,248,255,${alpha})`
            : `rgba(90,226,231,${alpha})`;
        context.beginPath();
        context.arc(p.sx, p.sy, radius, 0, Math.PI * 2);
        context.fill();
      }

      if (mode === "thinking") {
        for (let ring = 0; ring < 3; ring++) {
          const phase = time * (0.0009 + ring * 0.00023);
          context.strokeStyle = `rgba(106,196,255,${0.13 - ring * 0.026})`;
          context.lineWidth = 0.9;
          context.beginPath();
          context.ellipse(
            cx,
            cy - scale * 0.17,
            scale * (0.39 + ring * 0.11),
            scale * (0.18 + ring * 0.06),
            phase * 0.18,
            phase,
            phase + 1.7
          );
          context.stroke();
        }
      }

      if (mode === "listening" || mode === "speaking") {
        const radius = scale * (0.52 + (Math.sin(time * 0.006) + 1) * 0.025);
        context.strokeStyle = "rgba(104,239,235,.12)";
        context.lineWidth = 1.1;
        context.beginPath();
        context.arc(cx, cy, radius, 0, Math.PI * 2);
        context.stroke();
      }

      context.restore();
      frame = requestAnimationFrame(render);
    };

    resize();
    window.addEventListener("resize", resize);
    frame = requestAnimationFrame(render);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, [mode, points]);

  return (
    <div
      className="face-stage"
      onPointerMove={(event) => {
        pointer.current.x = (event.clientX / window.innerWidth) * 2 - 1;
        pointer.current.y = (event.clientY / window.innerHeight) * 2 - 1;
        pointer.current.active = true;
      }}
      onPointerLeave={() => {
        pointer.current.active = false;
      }}
      onClick={onTap}
    >
      <canvas ref={canvasRef} className="face-canvas" />
      <div className="face-hud">
        <div className="brand">ITACHI</div>
        <div className={`mode mode-${mode}`}>
          {mode === "thinking"
            ? "THINKING // SYNTHESIZING"
            : mode === "listening"
              ? "LISTENING"
              : mode === "speaking"
                ? "SPEAKING"
                : "ONLINE"}
        </div>
        <div className="face-hint">
          {mode === "thinking" ? "Input locked while cognition is active" : "Tap the face to speak"}
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const [history, setHistory] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<Mode>("idle");
  const [thinking, setThinking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [accessRequired, setAccessRequired] = useState<boolean | null>(null);
  const [unlocked, setUnlocked] = useState(false);
  const [passcode, setPasscode] = useState("");
  const [unlockError, setUnlockError] = useState("");
  const [statusText, setStatusText] = useState("Connecting");
  const [browser, setBrowser] = useState<BrowserContext>({
    timezone: "UTC",
    locale: "",
  });
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const inFlightRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    const locale = navigator.language || "";
    setBrowser((current) => ({ ...current, timezone, locale }));

    fetch("/api/status", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("status unavailable");
        return response.json();
      })
      .then((data) => {
        const required = Boolean(data.accessRequired);
        setAccessRequired(required);
        setUnlocked(!required);
        setStatusText(data.routesConfigured ? "Cognitive engine online" : "Reference mode");
      })
      .catch(() => {
        // Fail closed when the API cannot confirm whether preview access is protected.
        setAccessRequired(true);
        setUnlocked(false);
        setStatusText("Cognitive API unavailable");
      });

    if (navigator.permissions && navigator.geolocation) {
      navigator.permissions
        .query({ name: "geolocation" as PermissionName })
        .then((permission) => {
          if (permission.state === "granted") {
            navigator.geolocation.getCurrentPosition((position) => {
              setBrowser((current) => ({
                ...current,
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                accuracy: position.coords.accuracy,
              }));
            });
          }
        })
        .catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [history, thinking]);

  const speak = useCallback(
    (text: string) => {
      if (!voiceEnabled || !("speechSynthesis" in window)) {
        setMode("idle");
        return;
      }
      window.speechSynthesis.cancel();
      const spokenText = text.split(/\n\nSources?:/i)[0];
      const clean = spokenText
        .replace(/https?:\/\/\S+/g, "")
        .replace(/[`*_#>|]/g, "")
        .replace(/\s{2,}/g, " ")
        .trim()
        .slice(0, 3200);
      const utterance = new SpeechSynthesisUtterance(clean);
      const voices = window.speechSynthesis.getVoices();
      const preferred = [
        "Daniel",
        "Arthur",
        "Alex",
        "Reed",
        "Jamie",
        "Ryan",
        "Google UK English Male",
        "Microsoft Ryan",
        "Microsoft David",
      ];
      utterance.voice =
        voices.find((voice) => preferred.some((name) => voice.name.includes(name))) ||
        voices.find((voice) => voice.lang.startsWith("en")) ||
        null;
      utterance.rate = 0.91;
      utterance.pitch = 0.84;
      utterance.volume = 0.94;
      utterance.onstart = () => setMode("speaking");
      utterance.onend = () => setMode("idle");
      utterance.onerror = () => setMode("idle");
      window.speechSynthesis.speak(utterance);
    },
    [voiceEnabled]
  );

  const requestLocation = () => {
    if (!navigator.geolocation || browser.latitude !== undefined) return;
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setBrowser((current) => ({
          ...current,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        }));
      },
      () => undefined,
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 }
    );
  };

  const startListening = () => {
    if (thinking || inFlightRef.current || mode === "listening" || recognitionRef.current) return;
    requestLocation();
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setStatusText("Speech recognition is not available in this browser");
      return;
    }
    const recognition = new Recognition();
    recognitionRef.current = recognition;
    recognition.lang = navigator.language || "en-AU";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onstart = () => setMode("listening");
    recognition.onerror = (event: any) => {
      recognitionRef.current = null;
      setMode("idle");
      if (event?.error === "not-allowed" || event?.error === "service-not-allowed") {
        setStatusText("Microphone permission was not granted");
      } else if (event?.error && event.error !== "aborted") {
        setStatusText("Speech recognition could not be completed");
      }
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      setMode((current) => (current === "listening" ? "idle" : current));
    };
    recognition.onresult = (event: any) => {
      const text = String(event.results?.[0]?.[0]?.transcript || "").trim();
      if (text) setInput(text);
      setMode("idle");
    };
    try {
      recognition.start();
    } catch {
      recognitionRef.current = null;
      setMode("idle");
      setStatusText("Speech recognition is already active");
    }
  };

  const unlock = async (event: FormEvent) => {
    event.preventDefault();
    setUnlockError("");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch("/api/unlock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ passcode }),
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("access denied");
      setUnlocked(true);
      setStatusText("Cognitive engine online");
    } catch {
      setUnlockError("Access denied");
    } finally {
      window.clearTimeout(timeout);
    }
  };

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    const prompt = input.trim();
    if (!prompt || thinking || inFlightRef.current || !unlocked) return;

    const priorHistory = history.slice(-8);
    inFlightRef.current = true;
    setHistory((current) => [...current, { role: "user" as const, content: prompt }].slice(-12));
    setInput("");
    setThinking(true);
    setMode("thinking");
    window.speechSynthesis?.cancel();

    const controller = new AbortController();
    abortRef.current = controller;
    const timeout = window.setTimeout(() => controller.abort(), 58000);
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          passcode,
          depth: "auto",
          history: priorHistory,
          browser,
        }),
        signal: controller.signal,
      });
      const payload = await response.json().catch(() => ({}));
      if (response.status === 401) {
        setUnlocked(false);
        setAccessRequired(true);
        throw new Error("Access required");
      }
      if (!response.ok) {
        throw new Error("Itachi could not complete the request. Please try again shortly.");
      }
      const answer = String(payload.answer || "").trim() || "I could not complete that request just now.";
      setHistory((current) => [...current, { role: "assistant" as const, content: answer }].slice(-12));
      speak(answer);
    } catch (error) {
      const message = error instanceof DOMException && error.name === "AbortError"
        ? "That request took too long. Please try again."
        : error instanceof Error ? error.message : "The request could not be completed.";
      setHistory((current) => [...current, { role: "assistant" as const, content: message }].slice(-12));
      setMode("idle");
    } finally {
      window.clearTimeout(timeout);
      if (abortRef.current === controller) abortRef.current = null;
      inFlightRef.current = false;
      setThinking(false);
    }
  };

  useEffect(() => () => {
    abortRef.current?.abort();
    try {
      recognitionRef.current?.abort?.();
    } catch {
      // Browser speech recognition cleanup is best-effort.
    }
    recognitionRef.current = null;
  }, []);

  if (accessRequired === null) {
    return (
      <main className="shell">
        <ItachiFace mode="thinking" onTap={() => undefined} />
      </main>
    );
  }

  return (
    <main className="shell">
      <ItachiFace mode={mode} onTap={startListening} />

      {accessRequired && !unlocked ? (
        <section className="unlock-panel">
          <div className="panel-kicker">ITACHI // SECURE PREVIEW</div>
          <h1>Access required</h1>
          <p>The Vercel preview is protected while the new interface is under development.</p>
          <form onSubmit={unlock}>
            <input
              type="password"
              value={passcode}
              onChange={(event) => setPasscode(event.target.value)}
              placeholder="Access passcode"
              autoFocus
            />
            <button type="submit">Unlock</button>
          </form>
          {unlockError && <div className="error-text">{unlockError}</div>}
        </section>
      ) : (
        <aside className="chat-rail">
          <header className="rail-header">
            <div>
              <div className="panel-kicker">ITACHI // CONVERSATION</div>
              <div className="status-line">{statusText}</div>
            </div>
            <button
              className={`voice-toggle ${voiceEnabled ? "active" : ""}`}
              onClick={() => setVoiceEnabled((value) => !value)}
              aria-label="Toggle voice"
            >
              VOICE
            </button>
          </header>

          <div className="transcript" ref={transcriptRef}>
            {history.length === 0 && (
              <div className="welcome">
                <div className="itachi-label">ITACHI</div>
                <p>Cognitive interface ready. Ask a question or tap the face to speak.</p>
              </div>
            )}

            {history.map((turn, index) => (
              <article key={index} className={`message message-${turn.role}`}>
                <div className="message-label">{turn.role === "assistant" ? "ITACHI" : "YOU"}</div>
                <div className="message-body">{turn.content}</div>
              </article>
            ))}

            {thinking && (
              <div className="thinking-card">
                <span />
                THINKING // SYNTHESIZING EVIDENCE
              </div>
            )}
          </div>

          <form className="composer" onSubmit={submit}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit();
                }
              }}
              disabled={thinking || mode === "listening"}
              placeholder={thinking ? "Itachi is thinking…" : mode === "listening" ? "Listening…" : "Ask Itachi…"}
              rows={2}
            />
            <button type="submit" disabled={thinking || mode === "listening" || !input.trim()}>
              SEND
            </button>
          </form>
        </aside>
      )}
    </main>
  );
}
