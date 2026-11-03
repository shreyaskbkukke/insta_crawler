import re
from urllib.parse import urlparse

USERNAME_RE = re.compile(r"^[a-z0-9._]{1,30}$")
RESERVED_PATHS = {"p", "reel", "reels", "tv", "stories", "explore", "accounts", "direct"}


def parse_username(raw: str) -> str | None:
    """Accept `name`, `@name`, or an instagram.com profile URL; return a normalized username."""
    value = raw.strip()
    if "instagram.com" in value.lower():
        if "://" not in value:
            value = "https://" + value
        parts = [p for p in urlparse(value).path.split("/") if p]
        if not parts or parts[0].lower() in RESERVED_PATHS:
            return None
        value = parts[0]
    value = value.removeprefix("@").lower()
    return value if USERNAME_RE.match(value) else None
