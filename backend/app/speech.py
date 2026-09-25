import asyncio
import os
import tempfile
from pathlib import Path
from .config import settings

_whisper = None

def transcribe_sync(data: bytes, suffix: str) -> str:
    global _whisper
    from faster_whisper import WhisperModel
    if _whisper is None:
        _whisper = WhisperModel(settings.whisper_model, device='cpu', compute_type='int8')
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        name = f.name
    try:
        segments, _ = _whisper.transcribe(name, vad_filter=True)
        return ' '.join(s.text.strip() for s in segments).strip()
    finally:
        Path(name).unlink(missing_ok=True)

async def transcribe(data: bytes, suffix: str = '.webm') -> str:
    return await asyncio.to_thread(transcribe_sync, data, suffix)

async def speak(text: str) -> bytes:
    if not settings.piper_voice:
        raise RuntimeError('Set ITACHI_PIPER_VOICE to an installed voice name')
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / 'speech.wav'
        proc = await asyncio.create_subprocess_exec('python', '-m', 'piper', '-m', settings.piper_voice,
            '-f', str(target), '--', text, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, stderr = await proc.communicate()
        if proc.returncode or not target.exists():
            raise RuntimeError('Piper failed: ' + stderr.decode(errors='replace')[-300:])
        return target.read_bytes()
