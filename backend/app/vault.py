import re
from pathlib import Path
from .config import settings

MAX_NOTE = 256_000


def _vault_root() -> Path:
    return settings.vault.resolve()

def note_path(name: str) -> Path:
    if not name or '\\' in name or name.startswith('/') or '\x00' in name:
        raise ValueError('Invalid note path')
    vault_root = _vault_root()
    path = (vault_root / name).resolve()
    if not path.is_relative_to(vault_root) or path.suffix.lower() != '.md':
        raise ValueError('Only Markdown notes inside the vault are allowed')
    return path

def search(query: str, limit: int = 8) -> list[dict]:
    terms = [x.lower() for x in re.findall(r'[\w-]{3,}', query)][:12]
    vault_root = _vault_root()
    if not terms or not vault_root.is_dir():
        return []
    results = []
    for path in vault_root.rglob('*.md'):
        if any(part.startswith('.') for part in path.relative_to(vault_root).parts):
            continue
        if not path.resolve().is_relative_to(vault_root) or path.stat().st_size > MAX_NOTE:
            continue
        body = path.read_text(encoding='utf-8', errors='replace')
        haystack = (path.name + ' ' + body).lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            first = min((haystack.find(t) for t in terms if t in haystack), default=0)
            results.append({'path': str(path.relative_to(vault_root)), 'score': score, 'excerpt': body[max(0, first-80):first+320]})
    return sorted(results, key=lambda x: -x['score'])[:limit]

def read(name: str) -> str:
    path = note_path(name)
    if path.stat().st_size > MAX_NOTE:
        raise ValueError('Note too large')
    return path.read_text(encoding='utf-8')

def write(name: str, content: str) -> None:
    if len(content.encode('utf-8')) > MAX_NOTE:
        raise ValueError('Note too large')
    path = note_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8', errors='strict') as target:
            target.write(content)
    except FileExistsError:
        raise ValueError('Existing note: choose a new path to preserve the original')

def graph() -> dict:
    """Extract Obsidian wiki-links into a bounded, local Markdown graph."""
    vault_root = _vault_root()
    if not vault_root.is_dir():
        return {'nodes': [], 'edges': []}
    paths = []
    for path in vault_root.rglob('*.md'):
        relative = path.relative_to(vault_root)
        if (len(paths) >= 3000 or any(part.startswith('.') for part in relative.parts)
                or not path.resolve().is_relative_to(vault_root)
                or path.stat().st_size > MAX_NOTE):
            continue
        paths.append(path)
    known = {str(p.relative_to(vault_root).with_suffix('')): p for p in paths}
    by_stem: dict[str, list[str]] = {}
    for name in known:
        by_stem.setdefault(Path(name).name.casefold(), []).append(name)
    nodes = [{'id': name, 'label': Path(name).name, 'path': f'{name}.md'} for name in known]
    edges = set()
    for source, path in known.items():
        body = path.read_text(encoding='utf-8', errors='replace')
        for match in re.findall(r'\[\[([^\]]+)\]\]', body):
            target = match.split('|', 1)[0].split('#', 1)[0].removesuffix('.md').strip()
            if not target:
                continue
            candidate = str((Path(source).parent / target)).replace('\\', '/')
            if target in known:
                resolved = target
            elif candidate in known:
                resolved = candidate
            else:
                choices = by_stem.get(Path(target).name.casefold(), [])
                resolved = choices[0] if len(choices) == 1 else None
            if resolved and source != resolved:
                edges.add((source, resolved))
    return {'nodes': nodes, 'edges': [{'source': a, 'target': b} for a, b in sorted(edges)]}
