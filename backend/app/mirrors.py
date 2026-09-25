"""Optional HTTPS mirrors for the public catalog; credentials come from CI secrets."""
import ipaddress
import json
import os
import re
from urllib.parse import urlsplit
import httpx

TOKEN_ENV = re.compile(r'^ITACHI_MIRROR_TOKEN_[1-3]$')


def parse(raw: str) -> list[dict[str, str]]:
    if not raw:
        return []
    value = json.loads(raw)
    if not isinstance(value, list) or len(value) > 3:
        raise ValueError('Configure at most three public-catalog mirrors')
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError('Invalid mirror')
        name, url, env = (item.get(k) for k in ('name', 'url', 'token_env'))
        if not isinstance(name, str) or not name.isidentifier() or len(name) > 30:
            raise ValueError('Invalid mirror name')
        if not isinstance(url, str) or len(url) > 500:
            raise ValueError('Invalid mirror URL')
        address = urlsplit(url)
        host = address.hostname or ''
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError('Mirror cannot use an IP address')
        if (address.scheme != 'https' or '.' not in host or host.endswith(('.local', '.internal'))
                or address.username or address.password or address.port or address.query or address.fragment):
            raise ValueError('Mirror requires a public HTTPS object URL without credentials')
        if not isinstance(env, str) or not TOKEN_ENV.fullmatch(env):
            raise ValueError('Mirror requires a dedicated secret environment variable')
        result.append({'name':name, 'url':url, 'token_env':env})
    if len({item['name'] for item in result}) != len(result):
        raise ValueError('Mirror names must be unique')
    return result


async def upload(payload: bytes, mirrors: list[dict], environ: dict | None = None) -> list[str]:
    """Writes only the already-public JSON snapshot; never follows redirects."""
    if len(payload) > 100_000:
        raise ValueError('Snapshot exceeds 100 KB')
    environ = environ if environ is not None else os.environ
    completed = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        for mirror in mirrors:
            token = environ.get(mirror['token_env'], '')
            if not token:
                raise RuntimeError(f"Mirror {mirror['name']} has no dedicated credential")
            response = await client.put(mirror['url'], content=payload,
                headers={'Authorization':'Bearer ' + token, 'Content-Type':'application/json'})
            response.raise_for_status()
            completed.append(mirror['name'])
    return completed
