"""Prepare reviewable account-access proposals without registering accounts."""
import ipaddress
from urllib.parse import urlsplit


def prepare(url: str) -> str:
    """No network call, account creation or CAPTCHA interaction occurs here."""
    address = urlsplit(url.strip())
    host = (address.hostname or '').lower()
    if (address.scheme != 'https' or not host or '.' not in host
            or address.username or address.password or address.port
            or address.query or address.fragment or address.path not in ('', '/')
            or host.endswith(('.local', '.internal'))):
        raise ValueError('Provide the public HTTPS home URL without credentials or query parameters')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('IP address targets are not supported')
    if len(host) > 253 or any(not part or len(part) > 63 for part in host.split('.')):
        raise ValueError('Invalid host')
    return ('Proposed account access: https://' + host + '/. Website identity and terms have '
            'not been verified. Registration, creating an email address, accepting terms, '
            'payments and CAPTCHA or identity checks require a specific authorized workflow. '
            'No login was created and no website was contacted.')
