import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .config import settings
from . import vault, speech
from .public_catalog import load as load_public_catalog
from .orchestration import answer

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title='Itachi local assistant')
app.mount('/assets', StaticFiles(directory=ROOT / 'frontend'), name='assets')

class Note(BaseModel):
    path: str = Field(min_length=4, max_length=200)
    content: str = Field(min_length=1, max_length=256000)

class Utterance(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

@app.get('/')
async def index():
    return FileResponse(ROOT / 'frontend' / 'index.html')

@app.get('/api/health')
async def health():
    return {'status':'ready', 'knowledge_enabled':settings.knowledge_enabled, 'voice':bool(settings.piper_voice),
            'openclaw':bool(settings.openclaw_url), 'jev':bool(settings.jev_url)}

@app.get('/api/public-catalog')
async def public_catalog():
    return load_public_catalog()

@app.get('/api/notes')
async def notes(q: str = ''):
    if not settings.knowledge_enabled:
        raise HTTPException(403, 'Knowledge access is disabled')
    return vault.search(q[:200])

@app.get('/api/graph')
async def graph():
    if not settings.knowledge_enabled:
        raise HTTPException(403, 'Knowledge access is disabled')
    return vault.graph()

@app.get('/api/note')
async def note(path: str):
    if not settings.knowledge_enabled:
        raise HTTPException(403, 'Knowledge access is disabled')
    try:
        return {'path':path, 'content':vault.read(path)}
    except (ValueError, OSError) as e:
        raise HTTPException(400, str(e))

@app.post('/api/note', status_code=201)
async def create_note(note: Note):
    if not settings.knowledge_enabled:
        raise HTTPException(403, 'Knowledge access is disabled')
    try:
        vault.write(note.path, note.content)
        return {'path':note.path}
    except (ValueError, OSError) as e:
        raise HTTPException(400, str(e))

@app.post('/api/stt')
async def stt(file: UploadFile = File(...)):
    data = await file.read(10_000_001)
    if len(data) > 10_000_000:
        raise HTTPException(413, 'Recording exceeds 10 MB')
    media_type = file.content_type or ''
    suffix = '.webm' if 'webm' in media_type else '.mp4' if 'mp4' in media_type else '.ogg'
    try:
        return {'text':await speech.transcribe(data, suffix)}
    except (ImportError, RuntimeError) as e:
        raise HTTPException(503, str(e))

@app.post('/api/tts')
async def tts(utterance: Utterance):
    try:
        return Response(await speech.speak(utterance.text), media_type='audio/wav')
    except (OSError, RuntimeError) as e:
        raise HTTPException(503, str(e))

@app.websocket('/ws')
async def ws(socket: WebSocket):
    await socket.accept()
    try:
        while True:
            incoming = json.loads(await socket.receive_text())
            request_id = str(incoming.get('id', ''))[:80]
            prompt = str(incoming.get('text', '')).strip()[:8000]
            route = str(incoming.get('route', 'reasoning'))
            if not prompt or route not in {'auto','reasoning','code','openclaw','research'}:
                await socket.send_json({'type':'error','id':request_id,'message':'Invalid prompt or route'})
                continue
            await socket.send_json({'type':'state','id':request_id,'state':'thinking'})
            try:
                result, notes = await answer(prompt, route, incoming.get('web') is True)
                await socket.send_json({'type':'answer','id':request_id,'text':result,
                                        'notes':[n['path'] for n in notes]})
                await socket.send_json({'type':'state','id':request_id,'state':'idle'})
            except Exception as e:
                await socket.send_json({'type':'error','id':request_id,'message':str(e)[:400]})
                await socket.send_json({'type':'state','id':request_id,'state':'error'})
    except (WebSocketDisconnect, json.JSONDecodeError):
        pass
