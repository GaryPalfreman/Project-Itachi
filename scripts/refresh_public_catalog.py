"""Build a public metadata snapshot; no personal files or repository code fetched."""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from backend.app.github_public import catalog_repos
from backend.app.public_sources import wikipedia

ROOT = Path(__file__).resolve().parents[1]


async def refresh() -> dict:
    source = json.loads((ROOT / 'sources/public_repos.json').read_text())
    names = source.get('repositories', [])
    repos = await catalog_repos(names, os.getenv('GITHUB_TOKEN', ''))
    if not repos:
        raise RuntimeError('No source repositories were reachable; previous snapshot was retained')
    topics = json.loads((ROOT / 'sources/public_topics.json').read_text()).get('topics', [])
    references = []
    for topic in topics[:4]:
        if not isinstance(topic, str) or len(topic) > 80:
            continue
        try:
            pages = await wikipedia(topic)
            references.extend({**page, 'excerpt':page['excerpt'][:250],
                               'license':'CC BY-SA (Wikipedia excerpt)', 'topic':topic}
                              for page in pages[:2])
        except Exception:
            continue
    return {'generated_at':datetime.now(timezone.utc).isoformat(),
            'origin':'Public GitHub metadata and attributed Wikipedia excerpts; untrusted until reviewed',
            'repositories':repos, 'references':references}


if __name__ == '__main__':
    result = asyncio.run(refresh())
    destination = ROOT / 'data/public_catalog.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Updated public catalog:', len(result['repositories']), 'repositories')
