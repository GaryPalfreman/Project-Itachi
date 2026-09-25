"""Server-side provider routing without exporting account credentials to clients."""
import json
from dataclasses import dataclass
from urllib.parse import urlsplit

@dataclass(frozen=True)
class ModelRoute:
    name: str
    url: str
    model: str
    key: str = ''

def parse(raw: str) -> list[ModelRoute]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError('Invalid model routes JSON') from error
    if not isinstance(value, list) or not 1 <= len(value) <= 5:
        raise ValueError('Model routes must contain 1–5 entries')
    routes = []
    for entry in value:
        if not isinstance(entry, dict):
            raise ValueError('Invalid model route')
        name, url, model = (entry.get(k) for k in ('name', 'url', 'model'))
        if not all(isinstance(x, str) and x.strip() for x in (name, url, model)):
            raise ValueError('Each model route needs name, url and model')
        address = urlsplit(url)
        if (not address.netloc or address.path.endswith('/chat/completions') or
            (address.scheme != 'https' and
            not (address.scheme == 'http' and address.hostname in {'127.0.0.1', 'localhost'}))):
            raise ValueError('Model route must use HTTPS or local loopback HTTP')
        if address.username or address.password or address.query or address.fragment:
            raise ValueError('Model URL must not contain credentials or a query')
        routes.append(ModelRoute(name[:60], url.rstrip('/'), model[:100], str(entry.get('key', ''))))
    if len({r.name for r in routes}) != len(routes):
        raise ValueError('Model route names must be unique')
    return routes
