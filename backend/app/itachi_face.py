"""Fullscreen reactive 3D particle-node Itachi face with voice and microphone input."""

FACE_COMPONENT_HTML = """
<div id="itachi-node" class="itachi-node" data-mode="idle">
  <canvas id="node-canvas" aria-label="Itachi three-dimensional cognitive node face"></canvas>
  <div class="node-hud">
    <div class="node-name">ITACHI</div>
    <div id="node-state" class="node-state">NODE ONLINE</div>
    <div id="node-hint" class="node-hint">Tap the face to speak</div>
  </div>
</div>
"""

FACE_COMPONENT_CSS = """
.itachi-node {
  position:fixed;
  inset:0;
  width:100vw;
  height:100vh;
  margin:0;
  overflow:hidden;
  border-radius:0;
  cursor:pointer;
  user-select:none;
  z-index:0;
  background:
    radial-gradient(circle at 50% 40%,rgba(32,184,196,.12),transparent 24%),
    radial-gradient(circle at 50% 52%,rgba(37,96,151,.10),transparent 46%),
    linear-gradient(180deg,#010407 0%,#020a11 48%,#03101a 100%);
  box-shadow:inset 0 0 180px rgba(0,0,0,.82);
  font-family:Inter,ui-sans-serif,system-ui,sans-serif;
}
#node-canvas {
  position:absolute;
  inset:0;
  width:100%;
  height:100%;
  display:block;
}
.node-hud {
  position:absolute;
  left:0;
  right:0;
  top:5vh;
  text-align:center;
  pointer-events:none;
}
.node-name {
  color:rgba(221,251,250,.92);
  font-size:clamp(.95rem,1.5vw,1.35rem);
  font-weight:650;
  letter-spacing:.72em;
  text-indent:.72em;
  text-shadow:0 0 18px rgba(93,240,235,.24);
}
.node-state {
  margin-top:8px;
  color:rgba(126,232,227,.66);
  font-size:clamp(.58rem,.8vw,.72rem);
  letter-spacing:.22em;
}
.node-hint {
  margin-top:5px;
  color:rgba(161,204,208,.34);
  font-size:clamp(.52rem,.7vw,.62rem);
  letter-spacing:.10em;
}
.itachi-node[data-mode="listening"] .node-state {color:#c7fffb;}
.itachi-node[data-mode="thinking"] .node-state {color:#abdff8;}
.itachi-node[data-mode="speaking"] .node-state {color:#e4ffff;}
"""

FACE_COMPONENT_JS = r"""
export default function(component) {
  const root = component.parentElement.querySelector("#itachi-node");
  const canvas = component.parentElement.querySelector("#node-canvas");
  const stateLabel = component.parentElement.querySelector("#node-state");
  const hint = component.parentElement.querySelector("#node-hint");
  const setStateValue = component.setStateValue;
  const data = component.data || {};
  const requestedMode = data.mode || "idle";
  const voiceEnabled = data.voice_enabled !== false;
  const micEnabled = data.mic_enabled !== false;
  const speechId = data.speech_id || "";
  const rawText = data.speak_text || "";

  const ctx = canvas.getContext("2d");
  let width = 0;
  let height = 0;
  const dpr = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
  let animationId = null;
  let mode = requestedMode;
  let recognition = null;
  let micReady = false;
  let pointerX = 0;
  let pointerY = 0;
  let pointerActive = false;
  let smoothYaw = 0;
  let smoothPitch = 0;
  let smoothGazeX = 0;
  let smoothGazeY = 0;

  function setMode(next) {
    mode = next || "idle";
    root.dataset.mode = mode;
    const labels = {
      idle: "NODE ONLINE",
      listening: "LISTENING",
      thinking: "COGNITION ACTIVE",
      speaking: "VOICE LINK ACTIVE"
    };
    stateLabel.textContent = labels[mode] || "NODE ONLINE";
  }

  function resize() {
    const rect = root.getBoundingClientRect();
    width = Math.max(320, rect.width);
    height = Math.max(420, rect.height);
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function rng(seed) {
    return function() {
      let t = seed += 0x6D2B79F5;
      t = Math.imul(t ^ t >>> 15, t | 1);
      t ^= t + Math.imul(t ^ t >>> 7, t | 61);
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  const random = rng(917331);
  const points = [];

  function addPoint(x, y, z, group, weight) {
    points.push({
      x: x,
      y: y,
      z: z,
      group: group,
      phase: random() * Math.PI * 2,
      phase2: random() * Math.PI * 2,
      amp: 0.25 + random() * 1.15,
      size: (weight || 1) * (0.70 + random() * 1.10)
    });
  }

  function faceDepth(x, y) {
    const nx = x / 0.72;
    const ny = y / 1.00;
    const inside = Math.max(0.02, 1 - nx * nx - ny * ny);
    return Math.sqrt(inside) * 0.56;
  }

  // Dense curved facial shell.
  for (let iy = 0; iy < 22; iy++) {
    const y = -0.88 + (iy / 21) * 1.72;
    const taper = Math.max(0.18, Math.sqrt(Math.max(0.02, 1 - Math.pow(y / 1.02, 2))));
    const cols = 12 + Math.floor(taper * 14);
    for (let ix = 0; ix < cols; ix++) {
      const u = cols === 1 ? 0 : ix / (cols - 1);
      const x = (u * 2 - 1) * 0.69 * taper;
      if (y > 0.48 && Math.abs(x) > 0.42 - (y - 0.48) * 0.28) continue;
      if (Math.abs(x) < 0.055 && y > -0.30 && y < 0.28 && random() < 0.52) continue;
      const z = faceDepth(x, y) - 0.04 + (random() - 0.5) * 0.035;
      addPoint(x, y, z, "shell", 0.72);
    }
  }

  // Silhouette / jaw perimeter in three dimensions.
  for (let i = 0; i < 118; i++) {
    const a = (Math.PI * 2 * i) / 118;
    let x = Math.cos(a) * 0.72;
    let y = Math.sin(a) * 0.96 - 0.035;
    if (y > 0.38) x *= 0.84 - Math.min(0.22, (y - 0.38) * 0.30);
    if (y < -0.64) x *= 0.92;
    addPoint(x, y, 0.06, "outline", 1.0);
  }

  // Eyes and brows sit forward on the face.
  [-1, 1].forEach(function(side) {
    for (let i = 0; i < 32; i++) {
      const t = i / 31;
      const x = side * (0.18 + t * 0.245);
      const curve = Math.sin(t * Math.PI);
      const y = -0.20 - curve * 0.045;
      addPoint(x, y, faceDepth(x, y) + 0.055, "eye", 1.38);
      if (i % 2 === 0) {
        const by = -0.34 - curve * 0.055;
        addPoint(x, by, faceDepth(x, by) + 0.025, "brow", 0.92);
      }
    }
  });

  // Nose bridge and nose tip.
  for (let i = 0; i < 38; i++) {
    const t = i / 37;
    const y = -0.18 + t * 0.43;
    const x = (random() - 0.5) * (0.035 + t * 0.035);
    addPoint(x, y, faceDepth(x, y) + 0.085 + t * 0.05, "nose", 0.82);
  }
  for (let i = 0; i < 18; i++) {
    const a = Math.PI * 2 * i / 18;
    addPoint(Math.cos(a) * 0.075, 0.25 + Math.sin(a) * 0.042, 0.63, "nose", 0.86);
  }

  // Mouth and lips.
  for (let i = 0; i < 52; i++) {
    const t = i / 51;
    const x = -0.24 + t * 0.48;
    const y = 0.47 + Math.sin(t * Math.PI) * 0.028;
    addPoint(x, y, faceDepth(x, y) + 0.055, "mouth", 1.0);
  }

  // Cheekbone topology.
  [-1, 1].forEach(function(side) {
    for (let i = 0; i < 38; i++) {
      const t = i / 37;
      const x = side * (0.27 + t * 0.24);
      const y = 0.02 + t * 0.34;
      addPoint(x, y, faceDepth(x, y) + 0.01, "cheek", 0.72);
    }
  });

  // Forehead cognitive core.
  for (let i = 0; i < 24; i++) {
    const a = Math.PI * 2 * i / 24;
    const radius = 0.045 + (i % 3) * 0.012;
    const x = Math.cos(a) * radius;
    const y = -0.47 + Math.sin(a) * radius;
    addPoint(x, y, faceDepth(x, y) + 0.09, "core", 1.22);
  }

  // Sparse peripheral particles around the head for depth.
  for (let i = 0; i < 90; i++) {
    const a = random() * Math.PI * 2;
    const r = 0.78 + random() * 0.24;
    addPoint(
      Math.cos(a) * r,
      Math.sin(a) * (0.92 + random() * 0.20) - 0.03,
      (random() - 0.5) * 0.65,
      "aura",
      0.55
    );
  }

  function rotatePoint(p, yaw, pitch, roll) {
    const cosy = Math.cos(yaw);
    const siny = Math.sin(yaw);
    let x1 = p.x * cosy - p.z * siny;
    let z1 = p.x * siny + p.z * cosy;

    const cosp = Math.cos(pitch);
    const sinp = Math.sin(pitch);
    let y1 = p.y * cosp - z1 * sinp;
    let z2 = p.y * sinp + z1 * cosp;

    const cosr = Math.cos(roll);
    const sinr = Math.sin(roll);
    const x2 = x1 * cosr - y1 * sinr;
    const y2 = x1 * sinr + y1 * cosr;

    return {x: x2, y: y2, z: z2};
  }

  function currentPose(now) {
    const autonomousYaw = Math.sin(now * 0.00022) * 0.30 + Math.sin(now * 0.000071) * 0.12;
    const autonomousPitch = Math.cos(now * 0.00017) * 0.085;
    const pointerYaw = pointerActive ? pointerX * 0.34 : 0;
    const pointerPitch = pointerActive ? pointerY * 0.16 : 0;

    let targetYaw = autonomousYaw + pointerYaw;
    let targetPitch = autonomousPitch + pointerPitch;

    if (mode === "listening") {
      targetYaw *= 0.55;
      targetPitch *= 0.55;
    } else if (mode === "thinking") {
      targetYaw += Math.sin(now * 0.00105) * 0.065;
      targetPitch += Math.cos(now * 0.00128) * 0.035;
    } else if (mode === "speaking") {
      targetYaw *= 0.72;
      targetPitch += Math.sin(now * 0.004) * 0.018;
    }

    smoothYaw += (targetYaw - smoothYaw) * 0.035;
    smoothPitch += (targetPitch - smoothPitch) * 0.035;

    const autonomousGazeX = Math.sin(now * 0.00031) * 0.85;
    const autonomousGazeY = Math.cos(now * 0.00023) * 0.38;
    const targetGazeX = pointerActive ? pointerX : autonomousGazeX;
    const targetGazeY = pointerActive ? pointerY : autonomousGazeY;
    smoothGazeX += (targetGazeX - smoothGazeX) * 0.045;
    smoothGazeY += (targetGazeY - smoothGazeY) * 0.045;

    return {
      yaw: smoothYaw,
      pitch: smoothPitch,
      roll: Math.sin(now * 0.00014) * 0.025,
      gazeX: smoothGazeX,
      gazeY: smoothGazeY
    };
  }

  function projectPoint(p, pose, now) {
    let local = {x: p.x, y: p.y, z: p.z};

    if (p.group === "eye") {
      local.x += pose.gazeX * 0.026;
      local.y += pose.gazeY * 0.012;
      local.z += 0.012;
    }

    if (p.group === "mouth" && mode === "speaking") {
      local.y += Math.sin(now * 0.017 + p.phase) * 0.018;
      local.z += Math.cos(now * 0.015 + p.phase2) * 0.018;
    }

    if (p.group === "core" && mode === "thinking") {
      const pulse = 1 + Math.sin(now * 0.008 + p.phase) * 0.08;
      local.x *= pulse;
      local.y = -0.47 + (local.y + 0.47) * pulse;
      local.z += 0.04 * Math.sin(now * 0.008);
    }

    const r = rotatePoint(local, pose.yaw, pose.pitch, pose.roll);
    const camera = 3.15;
    const perspective = camera / (camera - r.z);
    const faceScale = Math.min(width * 0.43, height * 0.44);
    const cx = width * 0.5;
    const cy = height * 0.49;

    let drift = 1.0;
    if (mode === "listening") drift = 1.45;
    if (mode === "thinking") drift = 2.30;
    if (mode === "speaking") drift = 1.75;

    const dx = Math.sin(now * 0.00072 * drift + p.phase) * p.amp;
    const dy = Math.cos(now * 0.00061 * drift + p.phase2) * p.amp;

    return {
      x: cx + r.x * faceScale * perspective + dx,
      y: cy + r.y * faceScale * perspective + dy,
      z: r.z,
      perspective: perspective
    };
  }

  function draw(now) {
    ctx.clearRect(0, 0, width, height);
    const pose = currentPose(now);
    const cx = width * 0.5;
    const cy = height * 0.49;

    const halo = ctx.createRadialGradient(
      cx, cy, 28,
      cx, cy, Math.min(width, height) * 0.48
    );
    halo.addColorStop(0, mode === "thinking" ? "rgba(80,176,255,.11)" : "rgba(80,246,237,.085)");
    halo.addColorStop(0.55, "rgba(26,123,145,.025)");
    halo.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = halo;
    ctx.fillRect(0, 0, width, height);

    const projected = points.map(function(p) {
      return projectPoint(p, pose, now);
    });

    // Depth-sorted neural connections.
    ctx.lineWidth = 0.6;
    for (let i = 0; i < points.length; i += 4) {
      for (let j = i + 1; j < Math.min(points.length, i + 24); j += 3) {
        if (points[i].group === "aura" && points[j].group !== "aura") continue;
        const dx = projected[i].x - projected[j].x;
        const dy = projected[i].y - projected[j].y;
        const d2 = dx * dx + dy * dy;
        if (d2 < 1550) {
          const depth = (projected[i].z + projected[j].z) * 0.5;
          const depthBoost = Math.max(0.25, Math.min(1.2, 0.72 + depth * 0.35));
          const alpha = Math.max(0, (0.09 - d2 / 19000) * depthBoost);
          ctx.strokeStyle = mode === "thinking"
            ? "rgba(104,177,255," + alpha + ")"
            : "rgba(103,239,232," + alpha + ")";
          ctx.beginPath();
          ctx.moveTo(projected[i].x, projected[i].y);
          ctx.lineTo(projected[j].x, projected[j].y);
          ctx.stroke();
        }
      }
    }

    // Draw far nodes first so nearer nodes visually sit in front.
    const order = points.map(function(_, i) { return i; });
    order.sort(function(a, b) { return projected[a].z - projected[b].z; });

    for (let oi = 0; oi < order.length; oi++) {
      const i = order[oi];
      const p = points[i];
      const q = projected[i];

      let alpha = 0.38;
      let radius = p.size * q.perspective;
      let color = "103,226,221";

      if (p.group === "outline") alpha = 0.58;
      if (p.group === "shell") alpha = 0.32;
      if (p.group === "aura") alpha = 0.16;
      if (p.group === "eye") {
        alpha = 0.98;
        radius *= 1.65;
        color = "218,255,252";
      }
      if (p.group === "core") {
        alpha = 0.94;
        radius *= 1.50;
        color = "107,224,255";
      }
      if (p.group === "mouth" && mode === "speaking") {
        alpha = 0.90;
        radius *= 1.38;
      }
      if (mode === "thinking" && (p.group === "core" || p.group === "brow")) {
        alpha = 1.0;
      }
      if (mode === "listening" && (p.group === "eye" || p.group === "cheek")) {
        alpha = Math.min(1, alpha + 0.20);
      }

      const depthLight = Math.max(0.28, Math.min(1.35, 0.68 + q.z * 0.48));
      const flicker = 0.84 + 0.16 * Math.sin(now * 0.003 + p.phase);
      alpha *= depthLight * flicker;
      radius *= Math.max(0.72, depthLight);

      ctx.fillStyle = "rgba(" + color + "," + Math.min(1, alpha) + ")";
      ctx.shadowColor = "rgba(" + color + ",.42)";
      ctx.shadowBlur = (p.group === "eye" || p.group === "core") ? 11 : 3.5;
      ctx.beginPath();
      ctx.arc(q.x, q.y, Math.max(0.55, radius), 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.shadowBlur = 0;

    // Scanning arcs reinforce volumetric motion.
    const arcAlpha = mode === "thinking" ? 0.12 : 0.055;
    ctx.strokeStyle = "rgba(92,239,233," + arcAlpha + ")";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.ellipse(cx, cy, Math.min(width, height) * 0.31, Math.min(width, height) * 0.40,
      pose.yaw * 0.20, -1.2, 1.2);
    ctx.stroke();

    if (mode === "listening" || mode === "speaking") {
      const age = (now % 1800) / 1800;
      const radius = 75 + age * Math.min(width, height) * 0.19;
      ctx.strokeStyle = "rgba(100,242,236," + (0.15 * (1 - age)) + ")";
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.stroke();
    }

    animationId = requestAnimationFrame(draw);
  }

  function cleanSpeech(text) {
    const codePattern = new RegExp("\\x60\\x60\\x60[\\\\s\\\\S]*?\\x60\\x60\\x60", "g");
    return text
      .replace(codePattern, " code block ")
      .replace(/\[([^\]]+)\]\([^\)]+\)/g, "$1")
      .replace(/https?:\/\/\S+/g, "")
      .replace(/[*_>#~]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function chooseVoice() {
    const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
    const english = voices.filter(function(v) { return /^en/i.test(v.lang || ""); });
    const pool = english.length ? english : voices;
    const preferred = [
      "Daniel", "Arthur", "Alex", "Reed", "Eddy", "Jamie", "Nathan", "Ryan",
      "Google UK English Male", "Microsoft Ryan", "Microsoft David"
    ];
    for (let i = 0; i < preferred.length; i++) {
      const found = pool.find(function(v) {
        return (v.name || "").toLowerCase().indexOf(preferred[i].toLowerCase()) >= 0;
      });
      if (found) return found;
    }
    return pool.length ? pool[0] : null;
  }

  function speechChunks(text) {
    const sentences = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [text];
    const out = [];
    sentences.forEach(function(sentence) {
      let part = sentence.trim();
      while (part.length > 240) {
        let cut = part.lastIndexOf(" ", 240);
        if (cut < 80) cut = 240;
        out.push(part.slice(0, cut).trim());
        part = part.slice(cut).trim();
      }
      if (part) out.push(part);
    });
    return out;
  }

  function speak(text) {
    if (!window.speechSynthesis || !voiceEnabled) {
      setMode("idle");
      return;
    }
    const cleaned = cleanSpeech(text);
    if (!cleaned) {
      setMode("idle");
      return;
    }

    window.speechSynthesis.cancel();
    const queue = speechChunks(cleaned);
    let index = 0;

    function next() {
      if (index >= queue.length) {
        setMode("idle");
        hint.textContent = "Tap the face to speak";
        return;
      }
      const utterance = new SpeechSynthesisUtterance(queue[index++]);
      const voice = chooseVoice();
      if (voice) utterance.voice = voice;
      utterance.rate = 0.91;
      utterance.pitch = 0.84;
      utterance.volume = 0.94;
      utterance.onstart = function() {
        setMode("speaking");
        hint.textContent = "Responding…";
      };
      utterance.onend = next;
      utterance.onerror = function() {
        setMode("idle");
        hint.textContent = "Tap the face to speak";
      };
      window.speechSynthesis.speak(utterance);
    }
    next();
  }

  function emitMicStatus(status) {
    setStateValue("mic_status", {status: status, timestamp: Date.now()});
  }

  async function requestMicPermission() {
    if (!micEnabled || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: true});
      stream.getTracks().forEach(function(track) { track.stop(); });
      micReady = true;
      emitMicStatus("granted");
      return true;
    } catch (error) {
      emitMicStatus("blocked");
      return false;
    }
  }

  function recognitionClass() {
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }

  async function startListening() {
    if (!micEnabled) return;
    if (!micReady) {
      const ok = await requestMicPermission();
      if (!ok) {
        hint.textContent = "Microphone blocked — type below instead";
        return;
      }
    }

    const SR = recognitionClass();
    if (!SR) {
      emitMicStatus("unsupported");
      hint.textContent = "Speech input unsupported in this browser";
      return;
    }

    if (recognition) {
      try { recognition.abort(); } catch (_) {}
    }

    recognition = new SR();
    recognition.lang = navigator.language || "en-AU";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    setMode("listening");
    hint.textContent = "Listening…";

    recognition.onresult = function(event) {
      let finalText = "";
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const text = event.results[i][0].transcript || "";
        if (event.results[i].isFinal) finalText += text;
        else interim += text;
      }
      if (interim) hint.textContent = interim;
      if (finalText.trim()) {
        setStateValue("transcript", {
          id: String(Date.now()) + "-" + Math.random().toString(16).slice(2),
          text: finalText.trim()
        });
        setMode("thinking");
        hint.textContent = "Processing…";
      }
    };

    recognition.onerror = function() {
      setMode("idle");
      hint.textContent = "Tap the face to speak";
    };
    recognition.onend = function() {
      if (mode === "listening") {
        setMode("idle");
        hint.textContent = "Tap the face to speak";
      }
    };
    recognition.start();
  }

  function publishLocation(position) {
    const value = {
      status: "granted",
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy: position.coords.accuracy,
      timestamp: Date.now()
    };
    try { window.sessionStorage.setItem("itachi-location", JSON.stringify(value)); } catch (_) {}
    setStateValue("location", value);
  }

  function requestLocation() {
    if (!navigator.geolocation) {
      setStateValue("location", {status: "unavailable"});
      return;
    }
    try {
      const cached = JSON.parse(window.sessionStorage.getItem("itachi-location") || "null");
      if (cached && cached.status === "granted") {
        setStateValue("location", cached);
        return;
      }
    } catch (_) {}

    navigator.geolocation.getCurrentPosition(
      publishLocation,
      function(error) {
        setStateValue("location", {
          status: error.code === 1 ? "denied" : "unavailable",
          code: error.code
        });
      },
      {enableHighAccuracy: true, timeout: 12000, maximumAge: 300000}
    );
  }

  root.onpointermove = function(event) {
    const rect = root.getBoundingClientRect();
    pointerX = Math.max(-1, Math.min(1, ((event.clientX - rect.left) / rect.width) * 2 - 1));
    pointerY = Math.max(-1, Math.min(1, ((event.clientY - rect.top) / rect.height) * 2 - 1));
    pointerActive = true;
  };
  root.onpointerleave = function() {
    pointerActive = false;
  };

  setMode(requestedMode);
  resize();
  window.addEventListener("resize", resize);
  animationId = requestAnimationFrame(draw);

  root.onclick = function(event) {
    const tag = (event.target && event.target.tagName || "").toLowerCase();
    if (tag !== "input" && tag !== "button" && tag !== "textarea") startListening();
  };
  root.onkeydown = function(event) {
    if (event.key === "Enter" || event.key === " ") startListening();
  };
  root.tabIndex = 0;

  if (micEnabled) {
    requestMicPermission().then(function(ok) {
      hint.textContent = ok ? "Tap the face to speak" : "Tap the face to enable microphone";
    });
  } else {
    hint.textContent = "";
  }

  requestLocation();

  if (speechId && rawText) {
    const storageKey = "itachi-last-speech-id";
    const last = window.sessionStorage.getItem(storageKey);
    if (last !== speechId) {
      window.sessionStorage.setItem(storageKey, speechId);
      window.setTimeout(function() { speak(rawText); }, 90);
    } else if (requestedMode === "speaking") {
      setMode("idle");
    }
  }

  return function() {
    if (animationId) cancelAnimationFrame(animationId);
    if (recognition) {
      try { recognition.abort(); } catch (_) {}
    }
    window.removeEventListener("resize", resize);
  };
}
"""
