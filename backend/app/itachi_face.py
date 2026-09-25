"""Reactive Itachi face and browser-native voice component."""

FACE_COMPONENT_HTML = """
<div id="itachi-node" class="itachi-node" data-mode="idle">
  <div class="field field-a"></div>
  <div class="field field-b"></div>
  <div class="orbit orbit-a"><span></span><span></span><span></span></div>
  <div class="orbit orbit-b"><span></span><span></span></div>
  <div class="mask">
    <div class="crown-glyph"></div>
    <div class="temple temple-l"></div>
    <div class="temple temple-r"></div>
    <div class="visor">
      <div class="eye eye-l"></div>
      <div class="eye eye-r"></div>
    </div>
    <div class="bridge"></div>
    <div class="cheek cheek-l"></div>
    <div class="cheek cheek-r"></div>
    <div class="voice-array"><i></i><i></i><i></i><i></i><i></i></div>
    <div class="core"></div>
  </div>
  <div class="node-name">ITACHI</div>
  <div id="node-state" class="node-state">NODE ONLINE</div>
</div>
"""

FACE_COMPONENT_CSS = """
.itachi-node {
  --cyan:#74f7f0; --ice:#d8ffff; --violet:#7884ff;
  position:relative; width:min(430px,92vw); height:332px; margin:0 auto;
  display:flex; align-items:center; justify-content:center; overflow:hidden;
  font-family:Inter,ui-sans-serif,system-ui,sans-serif;
  filter:drop-shadow(0 0 26px rgba(44,205,210,.17));
}
.field {position:absolute;border-radius:50%;pointer-events:none;}
.field-a {
  width:310px;height:310px;
  background:radial-gradient(circle,rgba(50,217,216,.085),transparent 63%);
  border:1px solid rgba(106,245,239,.08);
}
.field-b {
  width:248px;height:248px;border:1px dashed rgba(125,156,255,.15);
  box-shadow:inset 0 0 50px rgba(65,215,215,.035);
  animation:fieldDrift 14s linear infinite;
}
.orbit {position:absolute;border-radius:50%;pointer-events:none;}
.orbit-a {width:286px;height:286px;border:1px solid rgba(105,239,235,.18);animation:orbitSpin 16s linear infinite;}
.orbit-b {width:218px;height:218px;border:1px solid rgba(116,132,255,.13);animation:orbitBack 11s linear infinite;}
.orbit span {position:absolute;width:5px;height:5px;border-radius:50%;background:var(--cyan);box-shadow:0 0 12px var(--cyan);}
.orbit-a span:nth-child(1){left:20px;top:70px}
.orbit-a span:nth-child(2){right:12px;top:142px}
.orbit-a span:nth-child(3){left:145px;bottom:-2px}
.orbit-b span:nth-child(1){left:2px;top:112px;background:var(--violet)}
.orbit-b span:nth-child(2){right:37px;top:18px}
.mask {
  position:relative;width:168px;height:198px;z-index:5;
  clip-path:polygon(28% 0,72% 0,95% 18%,100% 55%,82% 84%,56% 100%,44% 100%,18% 84%,0 55%,5% 18%);
  background:linear-gradient(145deg,rgba(98,123,137,.18),transparent 34%),
             linear-gradient(215deg,rgba(49,63,78,.22),rgba(4,8,13,.98) 40%,rgba(2,5,9,.99) 75%,rgba(51,93,101,.14));
  border:1px solid rgba(118,238,235,.32);
  box-shadow:inset 0 0 40px rgba(49,209,209,.08),0 0 44px rgba(36,179,187,.10);
  transform-origin:50% 65%;
}
.mask:before {
  content:"";position:absolute;inset:11px;
  clip-path:polygon(30% 0,70% 0,91% 20%,94% 55%,76% 79%,55% 94%,45% 94%,24% 79%,6% 55%,9% 20%);
  background:linear-gradient(180deg,rgba(18,31,39,.35),rgba(2,6,10,.68));
  border:1px solid rgba(152,182,191,.12);
}
.crown-glyph {
  position:absolute;z-index:8;left:68px;top:18px;width:31px;height:22px;
  border-top:1px solid rgba(115,243,239,.38);
  border-left:1px solid rgba(115,243,239,.16);
  border-right:1px solid rgba(115,243,239,.16);
  clip-path:polygon(0 0,100% 0,76% 100%,24% 100%);
  box-shadow:0 -5px 14px rgba(70,226,222,.12);
}
.visor {
  position:absolute;z-index:9;left:19px;right:19px;top:66px;height:30px;
  border-top:1px solid rgba(130,255,249,.24);
  border-bottom:1px solid rgba(101,171,184,.12);
  background:linear-gradient(180deg,rgba(5,18,24,.2),rgba(6,13,18,.55));
  clip-path:polygon(0 28%,47% 0,53% 0,100% 28%,88% 84%,54% 68%,46% 68%,12% 84%);
}
.eye {
  position:absolute;top:9px;width:47px;height:7px;
  background:linear-gradient(90deg,transparent,var(--ice) 45%,var(--cyan) 68%,transparent);
  box-shadow:0 0 10px rgba(103,247,240,.76),0 0 22px rgba(59,214,213,.25);
  animation:idleBlink 5.5s ease-in-out infinite;
}
.eye-l{left:9px;transform:rotate(4deg)} .eye-r{right:9px;transform:rotate(-4deg)}
.bridge {
  position:absolute;z-index:8;left:79px;top:89px;width:9px;height:47px;
  border-left:1px solid rgba(121,229,226,.22);
  border-right:1px solid rgba(126,149,162,.09);
  transform:skew(-3deg);
}
.cheek {position:absolute;z-index:7;top:104px;width:52px;height:39px;border-top:1px solid rgba(105,220,219,.13);border-bottom:1px solid rgba(104,136,151,.08);}
.cheek-l{left:17px;transform:skewY(-17deg)} .cheek-r{right:17px;transform:skewY(17deg)}
.temple {position:absolute;z-index:10;top:69px;width:8px;height:43px;border:1px solid rgba(108,235,231,.22);background:rgba(17,64,70,.18);}
.temple-l{left:4px}.temple-r{right:4px}
.voice-array {position:absolute;z-index:10;left:52px;top:151px;width:64px;height:22px;display:flex;align-items:center;justify-content:center;gap:5px;}
.voice-array i {display:block;width:3px;height:4px;border-radius:4px;background:rgba(108,240,233,.44);box-shadow:0 0 5px rgba(75,224,220,.25);transform-origin:center;}
.core {
  position:absolute;z-index:11;left:79px;top:121px;width:10px;height:10px;border-radius:50%;
  background:var(--ice);box-shadow:0 0 11px var(--cyan),0 0 27px rgba(78,223,220,.46);
  animation:coreIdle 2.6s ease-in-out infinite;
}
.node-name {
  position:absolute;bottom:20px;left:0;right:0;text-align:center;
  color:#cce5e7;font-size:1.04rem;font-weight:650;letter-spacing:.52em;text-indent:.52em;
  text-shadow:0 0 15px rgba(77,224,220,.22);
}
.node-state {
  position:absolute;bottom:2px;left:0;right:0;text-align:center;
  color:rgba(127,222,219,.58);font-size:.59rem;letter-spacing:.18em;
}
.itachi-node[data-mode="thinking"] .mask {animation:thinkTilt 3.2s ease-in-out infinite;}
.itachi-node[data-mode="thinking"] .orbit-a {animation-duration:4s;}
.itachi-node[data-mode="thinking"] .orbit-b {animation-duration:3s;}
.itachi-node[data-mode="thinking"] .core {animation:thinkCore .78s ease-in-out infinite;box-shadow:0 0 14px var(--cyan),0 0 40px rgba(78,223,220,.72);}
.itachi-node[data-mode="thinking"] .eye {animation:thinkEyes 1.3s ease-in-out infinite;}
.itachi-node[data-mode="speaking"] .mask {animation:speakHead 2.4s ease-in-out infinite;}
.itachi-node[data-mode="speaking"] .eye {animation:speakEyes 1.8s ease-in-out infinite;}
.itachi-node[data-mode="speaking"] .core {animation:speakCore .9s ease-in-out infinite;}
.itachi-node[data-mode="speaking"] .voice-array i {animation:voiceBar .54s ease-in-out infinite alternate;}
.itachi-node[data-mode="speaking"] .voice-array i:nth-child(2){animation-delay:.10s}
.itachi-node[data-mode="speaking"] .voice-array i:nth-child(3){animation-delay:.22s}
.itachi-node[data-mode="speaking"] .voice-array i:nth-child(4){animation-delay:.06s}
.itachi-node[data-mode="speaking"] .voice-array i:nth-child(5){animation-delay:.18s}
@keyframes orbitSpin{to{transform:rotate(360deg)}}
@keyframes orbitBack{to{transform:rotate(-360deg)}}
@keyframes fieldDrift{50%{transform:rotate(18deg) scale(1.035)}}
@keyframes idleBlink{0%,45%,49%,100%{transform:scaleY(1)}47%{transform:scaleY(.08)}}
@keyframes coreIdle{50%{transform:scale(1.28);opacity:.76}}
@keyframes thinkTilt{0%,100%{transform:rotate(-.7deg) translateY(0)}50%{transform:rotate(.7deg) translateY(-3px)}}
@keyframes thinkCore{50%{transform:scale(1.7);opacity:.66}}
@keyframes thinkEyes{50%{filter:brightness(1.6);opacity:.73}}
@keyframes speakHead{0%,100%{transform:translateY(0) rotate(0)}35%{transform:translateY(-2px) rotate(.5deg)}70%{transform:translateY(1px) rotate(-.4deg)}}
@keyframes speakEyes{50%{filter:brightness(1.28);opacity:.84}}
@keyframes speakCore{50%{transform:scale(1.52);opacity:.70}}
@keyframes voiceBar{from{height:3px;opacity:.4}to{height:18px;opacity:1}}
"""

FACE_COMPONENT_JS = r"""
export default function(component) {
  const root = component.parentElement.querySelector("#itachi-node");
  const stateLabel = component.parentElement.querySelector("#node-state");
  const data = component.data || {};
  const requestedMode = data.mode || "idle";
  const voiceEnabled = data.voice_enabled !== false;
  const speechId = data.speech_id || "";
  const rawText = data.speak_text || "";

  function setMode(mode) {
    root.dataset.mode = mode;
    const labels = {
      idle: "NODE ONLINE",
      thinking: "COGNITION ACTIVE",
      speaking: "VOICE LINK ACTIVE",
      listening: "LISTENING"
    };
    stateLabel.textContent = labels[mode] || "NODE ONLINE";
  }

  function cleanSpeech(text) {
    return text
      .replace(/```[\s\S]*?```/g, " code block ")
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
      "Daniel", "Alex", "Arthur", "Reed", "Eddy", "Jamie",
      "Nathan", "Google UK English Male", "Microsoft Ryan", "Microsoft David"
    ];
    for (let i = 0; i < preferred.length; i++) {
      const found = pool.find(function(v) {
        return (v.name || "").toLowerCase().indexOf(preferred[i].toLowerCase()) >= 0;
      });
      if (found) return found;
    }
    return pool.length ? pool[0] : null;
  }

  function chunks(text) {
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
      setMode("speaking");
      window.setTimeout(function(){ setMode("idle"); }, 1400);
      return;
    }
    const cleaned = cleanSpeech(text);
    if (!cleaned) {
      setMode("idle");
      return;
    }
    window.speechSynthesis.cancel();
    const queue = chunks(cleaned);
    let index = 0;

    function next() {
      if (index >= queue.length) {
        setMode("idle");
        return;
      }
      const utterance = new SpeechSynthesisUtterance(queue[index++]);
      const voice = chooseVoice();
      if (voice) utterance.voice = voice;
      utterance.rate = 0.92;
      utterance.pitch = 0.86;
      utterance.volume = 0.92;
      utterance.onstart = function(){ setMode("speaking"); };
      utterance.onend = next;
      utterance.onerror = function(){ setMode("idle"); };
      window.speechSynthesis.speak(utterance);
    }
    next();
  }

  setMode(requestedMode);

  if (speechId && rawText) {
    const storageKey = "itachi-last-speech-id";
    const last = window.sessionStorage.getItem(storageKey);
    if (last !== speechId) {
      window.sessionStorage.setItem(storageKey, speechId);
      window.setTimeout(function(){ speak(rawText); }, 80);
    }
  }
}
"""
