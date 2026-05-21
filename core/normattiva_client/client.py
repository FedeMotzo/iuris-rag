"""HTTP client for Normattiva's Akoma Ntoso XML download dance."""

from __future__ import annotations

import logging
import re
import time
from html import unescape
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class NormattivaError(Exception):
    """Base for all client errors."""


class SessionError(NormattivaError):
    """Session dance failed: HTML unparseable or caricaAKN href missing."""


class NotFoundError(NormattivaError):
    """URN not found: HTTP 404 from the norm page or the AKN endpoint."""


_NORMATTIVA_BASE = "https://www.normattiva.it"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_DEFAULT_CACHE_DIR = Path("data/cache/normattiva")
_CARICA_AKN_RE = re.compile(r'href="([^"]*caricaAKN[^"]*)"', re.IGNORECASE)
_XML_CONTENT_TYPES = ("text/xml", "application/xml")
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


class NormattivaClient:
    def __init__(
        self,
        cache_dir: Path | None = None,
        rate_limit_s: float = 1.0,
        timeout_s: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir is not None else _DEFAULT_CACHE_DIR
        self.rate_limit_s = rate_limit_s
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self._last_request_ts: float | None = None
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": _USER_AGENT,
                "Referer": f"{_NORMATTIVA_BASE}/",
            }
        )

    def fetch_akn(self, urn: str) -> bytes:
        cache_path = self.cache_dir / _cache_filename(urn)
        if cache_path.exists():
            logger.info("Cache hit for %s", urn)
            return cache_path.read_bytes()

        logger.info("Fetching %s from Normattiva", urn)
        html = self._get_norm_page(urn)
        akn_url = self._extract_akn_href(html, urn)
        xml_bytes = self._get_akn(akn_url, urn)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(xml_bytes)
        logger.info("Cached %s to %s", urn, cache_path)
        return xml_bytes

    def _get_norm_page(self, urn: str) -> str:
        url = f"{_NORMATTIVA_BASE}/uri-res/N2Ls?{urn}!vig="
        response = self._request_with_retry("GET", url, urn)
        return response.text

    def _extract_akn_href(self, html: str, urn: str) -> str:
        match = _CARICA_AKN_RE.search(html)
        if not match:
            raise SessionError(
                f"caricaAKN link not found in norm page HTML for URN {urn!r}"
            )
        href = unescape(match.group(1))
        if href.startswith("/"):
            href = _NORMATTIVA_BASE + href
        return href

    def _get_akn(self, url: str, urn: str) -> bytes:
        response = self._request_with_retry("GET", url, urn)
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type and not content_type.startswith(_XML_CONTENT_TYPES):
            raise SessionError(
                f"Unexpected Content-Type {content_type!r} for AKN response of URN {urn!r}"
            )
        return response.content

    def _request_with_retry(self, method: str, url: str, urn: str) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._respect_rate_limit()
            try:
                response = self._session.request(method, url, timeout=self.timeout_s)
                self._last_request_ts = time.monotonic()
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                self._last_request_ts = time.monotonic()
                if attempt >= self.max_retries:
                    break
                logger.warning(
                    "Retry %d/%d for %s after %s",
                    attempt + 1,
                    self.max_retries,
                    urn,
                    exc,
                )
                time.sleep(2 ** attempt)
                continue

            if response.status_code == 404:
                raise NotFoundError(
                    f"URN {urn!r} not found (HTTP 404 from {url})"
                )
            if response.status_code in _RETRYABLE_STATUSES:
                last_error = NormattivaError(
                    f"HTTP {response.status_code} from {url}"
                )
                if attempt >= self.max_retries:
                    break
                logger.warning(
                    "Retry %d/%d for %s after HTTP %d",
                    attempt + 1,
                    self.max_retries,
                    urn,
                    response.status_code,
                )
                time.sleep(2 ** attempt)
                continue
            if response.status_code >= 400:
                raise NormattivaError(
                    f"HTTP {response.status_code} from {url} for URN {urn!r}"
                )
            return response

        logger.error(
            "Fetch failed for %s after %d retries: %s", urn, self.max_retries, last_error
        )
        raise NormattivaError(
            f"Fetch failed for URN {urn!r} after {self.max_retries} retries: {last_error}"
        )

    def _respect_rate_limit(self) -> None:
        if self._last_request_ts is None:
            return
        elapsed = time.monotonic() - self._last_request_ts
        diff = self.rate_limit_s - elapsed
        if diff > 0:
            time.sleep(diff)


def _cache_filename(urn: str) -> str:
    safe = urn.replace(":", "_").replace(";", "_")
    return f"{safe}.xml"
