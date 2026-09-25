"""Read-only, in-memory import of a selected Obsidian Markdown ZIP."""
import io
import re
import zipfile
from pathlib import PurePosixPath

MAX_ARCHIVE = 30_000_000
MAX_UNCOMPRESSED = 50_000_000
MAX_NOTES = 2000
MAX_NOTE = 256_000

def load_markdown_zip(data: bytes) -> dict[str, str]:
    if len(data) > MAX_ARCHIVE:
        raise ValueError('ZIP exceeds 30 MB')
    notes: dict[str, str] = {}
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if (info.is_dir() or path.suffix.lower() != '.md'
                    or info.filename.startswith('/') or '\\' in info.filename
                    or any(part in {'..', '.'} or part.startswith('.') for part in path.parts)):
                continue
            if info.file_size > MAX_NOTE or len(notes) >= MAX_NOTES:
                raise ValueError('Vault export exceeds note limits')
            total += info.file_size
            if total > MAX_UNCOMPRESSED:
                raise ValueError('Vault export exceeds 50 MB uncompressed')
            notes[str(path)] = archive.read(info).decode('utf-8', errors='replace')
    if not notes:
        raise ValueError('No Markdown notes found in ZIP')
    return notes

def find(notes: dict[str, str], query: str, limit: int = 6) -> list[dict[str, str]]:
    terms = [term.lower() for term in re.findall(r'[\w-]{3,}', query)][:12]
    scored = []
    for name, body in notes.items():
        text = (name + '\n' + body).lower()
        score = sum(text.count(term) for term in terms)
        if score:
            position = next((body.lower().find(term) for term in terms if term in body.lower()), 0)
            start = max(0, position - 300)
            excerpt = body[start:start + 1500]
            scored.append((score, name, excerpt))
    return [{'path': name, 'excerpt': excerpt} for _, name, excerpt in
            sorted(scored, reverse=True)[:limit]]
