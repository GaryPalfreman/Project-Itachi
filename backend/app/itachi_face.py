"""Reactive particle-node Itachi face with browser voice and microphone input."""

FACE_COMPONENT_HTML = """
<div id="itachi-node" class="itachi-node" data-mode="idle">
  <canvas id="node-canvas" aria-label="Itachi cognitive node face"></canvas>
  <div class="node-name">ITACHI</div>
  <div id="node-state" class="node-state">NODE ONLINE</div>
  <div id="node-hint" class="node-hint">Tap the face to speak</div>
</div>
"""

FACE_COMPONENT_CSS = """
.itachi-node {
  position:relative; width:min(520px,94vw); height:410px; margin:0 auto;
  overflow:hidden; border-radius:28px; cursor:pointer; user-select:none;
  background:radial-gradient(circle at 50% 42%,rgba(42,174,184,.10),transparent 38%),
             radial-gradient(circle at 50% 52%,rgba(70,91,170,.05),transparent 56%);
  box-shadow:inset 0 0 90px rgba(3,9,14,.92),0 0 60px rgba(46,205,207,.05);
  font-family:Inter,ui-sans-serif,system-ui,sans-serif;
}
#node-canvas {position:absolute;inset:0;width:100%;height:100%;display:block;}
.node-name {position:absolute;left:0;right:0;bottom:36px;text-align:center;color:#d4eeee;
  font-size:1rem;font-weight:650;letter-spacing:.58em;text-indent:.58em;text-shadow:0 0 16px rgba(93,240,235,.28);}
.node-state {position:absolute;left:0;right:0;bottom:19px;text-align:center;color:rgba(130,229,224,.72);
  font-size:.61rem;letter-spacing:.20em;}
.node-hint {position:absolute;left:0;right:0;bottom:4px;text-align:center;color:rgba(159,196,201,.38);
  font-size:.54rem;letter-spacing:.11em;}
.itachi-node[data-mode="listening"] .node-state {color:#b9fff9;}
.itachi-node[data-mode="thinking"] .node-state {color:#9cdcf8;}
.itachi-node[data-mode="speaking"] .node-state {color:#d8ffff;}
@media (max-width:620px){.itachi-node{height:350px}.node-name{font-size:.88rem;bottom:32px}}
"""

FACE_COMPONENT_JS = r"""
export default function(component) {
  const root=component.parentElement.querySelector("#itachi-node");
  const canvas=component.parentElement.querySelector("#node-canvas");
  const stateLabel=component.parentElement.querySelector("#node-state");
  const hint=component.parentElement.querySelector("#node-hint");
  const setStateValue=component.setStateValue;
  const data=component.data||{};
  const requestedMode=data.mode||"idle";
  const voiceEnabled=data.voice_enabled!==false;
  const micEnabled=data.mic_enabled!==false;
  const speechId=data.speech_id||"";
  const rawText=data.speak_text||"";
  const ctx=canvas.getContext("2d");
  let width=0,height=0;
  const dpr=Math.max(1,Math.min(window.devicePixelRatio||1,2));
  let animationId=null,mode=requestedMode,recognition=null,micReady=false;

  function setMode(next){
    mode=next||"idle";root.dataset.mode=mode;
    const labels={idle:"NODE ONLINE",listening:"LISTENING",thinking:"COGNITION ACTIVE",speaking:"VOICE LINK ACTIVE"};
    stateLabel.textContent=labels[mode]||"NODE ONLINE";
  }
  function resize(){
    const rect=root.getBoundingClientRect();width=Math.max(320,rect.width);height=Math.max(300,rect.height);
    canvas.width=Math.floor(width*dpr);canvas.height=Math.floor(height*dpr);
    canvas.style.width=width+"px";canvas.style.height=height+"px";ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  function rng(seed){return function(){let t=seed+=0x6D2B79F5;t=Math.imul(t^t>>>15,t|1);
    t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;};}
  const random=rng(917331),points=[];
  function add(nx,ny,group,weight){points.push({nx:nx,ny:ny,group:group,phase:random()*Math.PI*2,
    phase2:random()*Math.PI*2,amp:.35+random()*1.65,size:(weight||1)*(.75+random()*1.15)});}

  for(let i=0;i<92;i++){const a=Math.PI*2*i/92;let x=Math.cos(a)*.305,y=Math.sin(a)*.405-.015;
    if(y>.18)x*=.78-Math.min(.20,(y-.18)*.65);if(y<-.28)x*=.86;add(x,y,"outline",1);}
  for(let i=0;i<150;i++){const y=-.31+random()*.62,half=.255*Math.sqrt(Math.max(.08,1-Math.pow(y/.37,2)));
    const x=(random()*2-1)*half;if(Math.abs(x)<.045&&y>-.17&&y<.17&&random()<.55)continue;add(x,y,"cloud",.78);}
  [-1,1].forEach(function(side){for(let i=0;i<24;i++){const t=i/23,x=side*(.085+t*.125),arch=Math.sin(t*Math.PI);
    add(x,-.095-arch*.018,"eye",1.45);if(i%2===0)add(x,-.145-arch*.022,"brow",.95);}});
  for(let i=0;i<30;i++){const t=i/29;add((random()-.5)*.025,-.075+t*.205,"nose",.78);}
  for(let i=0;i<42;i++){const t=i/41;add(-.105+t*.21,.215+Math.sin(t*Math.PI)*.014,"mouth",1.05);}
  [-1,1].forEach(function(side){for(let i=0;i<28;i++){const t=i/27;add(side*(.115+t*.115),.02+t*.22,"cheek",.72);}});
  for(let i=0;i<16;i++){const a=Math.PI*2*i/16;add(Math.cos(a)*.028,.055+Math.sin(a)*.028,"core",1.15);}

  function projected(p,now){
    const cx=width*.5,cy=height*.43,scale=Math.min(width,height)*.82;
    let drift=1;if(mode==="thinking")drift=2.6;if(mode==="listening")drift=1.7;if(mode==="speaking")drift=2;
    let dx=Math.sin(now*.00075*drift+p.phase)*p.amp,dy=Math.cos(now*.00061*drift+p.phase2)*p.amp;
    if(p.group==="mouth"&&mode==="speaking")dy+=Math.sin(now*.018+p.phase)*3.5;
    if(p.group==="eye"&&mode==="listening")dx+=Math.sin(now*.004+p.phase)*1.6;
    if(p.group==="core"&&mode==="thinking"){const pulse=1+.16*Math.sin(now*.008);
      return{x:cx+p.nx*scale*pulse+dx,y:cy+p.ny*scale*pulse+dy};}
    return{x:cx+p.nx*scale+dx,y:cy+p.ny*scale+dy};
  }

  function draw(now){
    ctx.clearRect(0,0,width,height);
    const cx=width*.5,cy=height*.43;
    const halo=ctx.createRadialGradient(cx,cy,20,cx,cy,Math.min(width,height)*.42);
    halo.addColorStop(0,mode==="thinking"?"rgba(88,197,255,.10)":"rgba(90,245,237,.08)");
    halo.addColorStop(1,"rgba(0,0,0,0)");ctx.fillStyle=halo;ctx.fillRect(0,0,width,height);
    const pos=points.map(function(p){return projected(p,now);});
    ctx.lineWidth=.55;
    for(let i=0;i<points.length;i+=3){for(let j=i+1;j<Math.min(points.length,i+18);j+=2){
      const dx=pos[i].x-pos[j].x,dy=pos[i].y-pos[j].y,d2=dx*dx+dy*dy;
      if(d2<1050){const alpha=Math.max(0,.105-d2/12000);
        ctx.strokeStyle=mode==="thinking"?"rgba(104,177,255,"+alpha+")":"rgba(103,239,232,"+alpha+")";
        ctx.beginPath();ctx.moveTo(pos[i].x,pos[i].y);ctx.lineTo(pos[j].x,pos[j].y);ctx.stroke();}}}
    for(let i=0;i<points.length;i++){
      const p=points[i],q=pos[i];let alpha=.42,radius=p.size,color="111,226,221";
      if(p.group==="eye"){alpha=.95;radius*=1.55;color="210,255,252";}
      if(p.group==="core"){alpha=.88;radius*=1.35;color="112,231,255";}
      if(p.group==="outline")alpha=.62;
      if(p.group==="mouth"&&mode==="speaking"){alpha=.88;radius*=1.35;}
      if(mode==="thinking"&&(p.group==="core"||p.group==="brow"))alpha=1;
      if(mode==="listening"&&(p.group==="eye"||p.group==="cheek"))alpha=Math.min(1,alpha+.18);
      const flicker=.82+.18*Math.sin(now*.003+p.phase);
      ctx.fillStyle="rgba("+color+","+(alpha*flicker)+")";ctx.shadowColor="rgba("+color+",.45)";
      ctx.shadowBlur=(p.group==="eye"||p.group==="core")?9:3;ctx.beginPath();
      ctx.arc(q.x,q.y,Math.max(.55,radius),0,Math.PI*2);ctx.fill();
    }
    ctx.shadowBlur=0;
    if(mode==="listening"||mode==="speaking"){const age=(now%1800)/1800,radius=65+age*115;
      ctx.strokeStyle="rgba(100,242,236,"+(.16*(1-age))+")";ctx.lineWidth=1;ctx.beginPath();
      ctx.arc(cx,cy,radius,0,Math.PI*2);ctx.stroke();}
    animationId=requestAnimationFrame(draw);
  }

  function cleanSpeech(text){
    const codePattern=new RegExp("\\x60\\x60\\x60[\\\\s\\\\S]*?\\x60\\x60\\x60","g");
    return text.replace(codePattern," code block ").replace(/\[([^\]]+)\]\([^\)]+\)/g,"$1")
      .replace(/https?:\/\/\S+/g,"").replace(/[*_>#~]/g," ").replace(/\s+/g," ").trim();
  }
  function chooseVoice(){
    const voices=window.speechSynthesis?window.speechSynthesis.getVoices():[];
    const english=voices.filter(function(v){return /^en/i.test(v.lang||"");}),pool=english.length?english:voices;
    const preferred=["Daniel","Arthur","Alex","Reed","Eddy","Jamie","Nathan","Ryan","Google UK English Male","Microsoft Ryan","Microsoft David"];
    for(let i=0;i<preferred.length;i++){const found=pool.find(function(v){
      return(v.name||"").toLowerCase().indexOf(preferred[i].toLowerCase())>=0;});if(found)return found;}
    return pool.length?pool[0]:null;
  }
  function chunks(text){
    const sentences=text.match(/[^.!?]+[.!?]+|[^.!?]+$/g)||[text],out=[];
    sentences.forEach(function(sentence){let part=sentence.trim();while(part.length>240){
      let cut=part.lastIndexOf(" ",240);if(cut<80)cut=240;out.push(part.slice(0,cut).trim());part=part.slice(cut).trim();}
      if(part)out.push(part);});return out;
  }
  function speak(text){
    if(!window.speechSynthesis||!voiceEnabled){setMode("idle");return;}
    const cleaned=cleanSpeech(text);if(!cleaned){setMode("idle");return;}
    window.speechSynthesis.cancel();const queue=chunks(cleaned);let index=0;
    function next(){if(index>=queue.length){setMode("idle");return;}
      const utterance=new SpeechSynthesisUtterance(queue[index++]),voice=chooseVoice();if(voice)utterance.voice=voice;
      utterance.rate=.91;utterance.pitch=.84;utterance.volume=.94;utterance.onstart=function(){setMode("speaking");};
      utterance.onend=next;utterance.onerror=function(){setMode("idle");};window.speechSynthesis.speak(utterance);}
    next();
  }

  function emitMicStatus(status){setStateValue("mic_status",{status:status,timestamp:Date.now()});}
  async function requestMicPermission(){
    if(!micEnabled||!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)return false;
    try{const stream=await navigator.mediaDevices.getUserMedia({audio:true});stream.getTracks().forEach(function(track){track.stop();});
      micReady=true;emitMicStatus("granted");return true;}catch(error){emitMicStatus("blocked");return false;}
  }
  function recognitionClass(){return window.SpeechRecognition||window.webkitSpeechRecognition||null;}
  async function startListening(){
    if(!micEnabled)return;
    if(!micReady){const ok=await requestMicPermission();if(!ok){hint.textContent="Microphone blocked — type below instead";return;}}
    const SR=recognitionClass();if(!SR){emitMicStatus("unsupported");hint.textContent="Speech input unsupported in this browser";return;}
    if(recognition){try{recognition.abort();}catch(_){}}
    recognition=new SR();recognition.lang=navigator.language||"en-AU";recognition.interimResults=true;
    recognition.continuous=false;recognition.maxAlternatives=1;setMode("listening");hint.textContent="Listening…";
    recognition.onresult=function(event){let finalText="",interim="";
      for(let i=event.resultIndex;i<event.results.length;i++){const text=event.results[i][0].transcript||"";
        if(event.results[i].isFinal)finalText+=text;else interim+=text;}
      if(interim)hint.textContent=interim;
      if(finalText.trim()){setStateValue("transcript",{id:String(Date.now())+"-"+Math.random().toString(16).slice(2),
        text:finalText.trim()});setMode("thinking");hint.textContent="Processing…";}};
    recognition.onerror=function(){setMode("idle");hint.textContent="Tap the face to speak";};
    recognition.onend=function(){if(mode==="listening"){setMode("idle");hint.textContent="Tap the face to speak";}};
    recognition.start();
  }

  function publishLocation(position){
    const value={status:"granted",latitude:position.coords.latitude,longitude:position.coords.longitude,
      accuracy:position.coords.accuracy,timestamp:Date.now()};
    try{window.sessionStorage.setItem("itachi-location",JSON.stringify(value));}catch(_){}
    setStateValue("location",value);
  }
  function requestLocation(){
    if(!navigator.geolocation){setStateValue("location",{status:"unavailable"});return;}
    try{const cached=JSON.parse(window.sessionStorage.getItem("itachi-location")||"null");
      if(cached&&cached.status==="granted"){setStateValue("location",cached);return;}}catch(_){}
    navigator.geolocation.getCurrentPosition(publishLocation,function(error){
      setStateValue("location",{status:error.code===1?"denied":"unavailable",code:error.code});},
      {enableHighAccuracy:true,timeout:12000,maximumAge:300000});
  }

  setMode(requestedMode);resize();window.addEventListener("resize",resize);animationId=requestAnimationFrame(draw);
  root.onclick=function(){startListening();};root.onkeydown=function(event){if(event.key==="Enter"||event.key===" ")startListening();};
  root.tabIndex=0;
  if(micEnabled){requestMicPermission().then(function(ok){hint.textContent=ok?"Tap the face to speak":"Tap the face to enable microphone";});}
  else{hint.textContent="";}
  requestLocation();

  if(speechId&&rawText){const storageKey="itachi-last-speech-id",last=window.sessionStorage.getItem(storageKey);
    if(last!==speechId){window.sessionStorage.setItem(storageKey,speechId);window.setTimeout(function(){speak(rawText);},80);}}
  return function(){if(animationId)cancelAnimationFrame(animationId);if(recognition){try{recognition.abort();}catch(_){}}
    window.removeEventListener("resize",resize);};
}
"""
