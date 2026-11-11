import hashlib
import re
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

from bs4 import BeautifulSoup


def clean_html(value):

    if not value:
        return ""

    soup = BeautifulSoup(value, "html.parser")

    return " ".join(soup.get_text(" ").split())


def normalize_url(url):

    if not url:
        return ""

    try:
        parts = urlsplit(url.strip())

        # Remove tracking parameters.
        query = [
            (key, value)
            for key, value in parse_qsl(parts.query)
            if not key.lower().startswith("utm_")
            and key.lower() not in {
                "fbclid",
                "gclid",
                "mc_cid",
                "mc_eid",
            }
        ]

        normalized = urlunsplit((
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(query),
            "",
        ))

        return normalized

    except Exception:
        return url.strip()


def generate_content_hash(title, url):

    normalized_title = " ".join(
        title.casefold().split()
    )

    normalized_url = normalize_url(url)

    raw = f"{normalized_title}|{normalized_url}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def normalize_text(value):

    return re.sub(
        r"\s+",
        " ",
        value.casefold()
    ).strip()