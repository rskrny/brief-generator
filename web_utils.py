"""Utility functions for web interactions."""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup


def fetch_product_page_text(url: str) -> str:
    """Fetch a URL and return visible text content.

    The HTML is fetched via ``requests`` and parsed with ``BeautifulSoup``.
    Script and style tags are removed before extracting text. Whitespace is
    normalized and empty lines are stripped.
    """

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
