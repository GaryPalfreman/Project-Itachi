import {setState} from './face.js';import {record,speak} from './audio.js';
const log=document.getElementById('log'),input=document.getElementById('prompt'),status=document.getElementById('status');
let socket,voice=false,pending=new Map();
function add(kind,text){const item=document.createElement('p');item.className=kind;item.textContent=text;log.append(item);log.scrollTop=log.scrollHeight}
function connect(){socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);
 socket.onopen=()=>{status.textContent='CONNECTED';setState('idle')};socket.onclose=()=>{status.textContent='DISCONNECTED';setState('error');setTimeout(connect,1800)};
 socket.onmessage=async event=>{let data=JSON.parse(event.data);if(data.type==='state')setState(data.state);if(data.type==='error')add('error',data.message);
 if(data.type==='answer'){add('assistant',data.text+(data.notes.length?'\nVault: '+data.notes.join(', '):''));if(voice)try{await speak(data.text)}catch(e){add('error',e.message)}}}}
connect();document.getElementById('form').onsubmit=e=>{e.preventDefault();const text=input.value.trim();if(!text)return;if(socket.readyState!==WebSocket.OPEN){add('error','Backend disconnected');return}
 add('user',text);socket.send(JSON.stringify({id:crypto.randomUUID(),route:document.getElementById('route').value,text}));input.value=''};
document.getElementById('mic').onclick=async()=>{try{await record(document.getElementById('mic'),(text,error)=>{if(error)add('error',error);else if(text){input.value=text;document.getElementById('form').requestSubmit()}})}catch(e){add('error',e.message);setState('error')}};
document.getElementById('voice').onclick=e=>{voice=!voice;e.target.textContent=voice?'VOICE ON':'VOICE OFF';e.target.setAttribute('aria-pressed',String(voice))};
