import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings


@dataclass
class IngestedArticle:
    title: str
    content: str


def _assert_public_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only public HTTP(S) URLs are allowed")
    try:
        default_port = 443 if parsed.scheme == "https" else 80
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or default_port)}
    except socket.gaierror as exc:
        raise ValueError("URL host could not be resolved") from exc
    if any(ipaddress.ip_address(address).is_private or ipaddress.ip_address(address).is_loopback or ipaddress.ip_address(address).is_link_local for address in addresses):
        raise ValueError("Private or local URLs are not allowed")


def fetch_article(url: str) -> IngestedArticle:
    _assert_public_url(url)
    with httpx.Client(timeout=settings.url_fetch_timeout_seconds, follow_redirects=False) as client:
        response = client.get(url, headers={"User-Agent": "SocialStudio/1.0"})
        response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        raise ValueError("URL must return an HTML page")
    if len(response.content) > settings.url_fetch_max_bytes:
        raise ValueError("Article exceeds the maximum download size")
    soup = BeautifulSoup(response.text, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "aside"]):
        element.decompose()
    article = soup.find("article") or soup.find("main") or soup.body
    text = "\n".join(line.strip() for line in article.get_text("\n").splitlines() if line.strip()) if article else ""
    title = (soup.title.string.strip() if soup.title and soup.title.string else "Imported article")[:300]
    if len(text) < 20:
        raise ValueError("Could not extract enough article text")
    return IngestedArticle(title=title, content=text[:100_000])
