"""HTTP client for EUR-Lex HTML rendering downloads."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class EurLexError(Exception):
    """Base for all EUR-Lex client errors."""


class NotFoundError(EurLexError):
    """CELEX not found (HTTP 404)."""


class InvalidContentError(EurLexError):
    """Server returned an unexpected Content-Type (e.g. XML when HTML was expected)."""


_EURLEX_BASE = "https://eur-lex.europa.eu"
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_DEFAULT_CACHE_DIR = Path("data/cache/eurlex")
_HTML_CONTENT_TYPES = ("text/html",)
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

# EUR-Lex documents in our v1 corpus are all > 500 KB. Anything smaller than this
# threshold is almost certainly a WAF challenge page, an error placeholder, or a
# redirect stub — never a real consolidated regulation. We refuse to cache such
# responses (rather than poisoning the cache for the next run).
MIN_HTML_SIZE = 10_000
_HTML_START_MARKERS = (b"<!doctype", b"<html")


class EurLexClient:
    def __init__(
        self,
        cache_dir: Path | None = None,
        rate_limit_s: float = 1.0,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        language: str = "IT",
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir is not None else _DEFAULT_CACHE_DIR
        self.rate_limit_s = rate_limit_s
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.language = language
        self._last_request_ts: float | None = None
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": _USER_AGENT})

    def fetch_html(self, celex: str) -> bytes:
        cache_path = self._cache_path(celex)
        if cache_path.exists():
            logger.info("Cache hit for %s (%s)", celex, self.language)
            return cache_path.read_bytes()

        logger.info("Fetching %s from EUR-Lex (%s)", celex, self.language)
        url = (
            f"{_EURLEX_BASE}/legal-content/{self.language}/TXT/HTML/"
            f"?uri=CELEX:{celex}"
        )
        response = self._request_with_retry(url, celex)

        content_type = response.headers.get("Content-Type")
        if content_type:
            primary = content_type.split(";", 1)[0].strip().lower()
            if primary and not primary.startswith(_HTML_CONTENT_TYPES):
                raise InvalidContentError(
                    f"Unexpected Content-Type {primary!r} for CELEX {celex!r}"
                )

        content = response.content
        if len(content) < MIN_HTML_SIZE:
            msg = (
                f"Response body too small ({len(content)} bytes) for {celex}, "
                f"likely a WAF challenge or error page. Expected at least "
                f"{MIN_HTML_SIZE} bytes."
            )
            logger.error(msg)
            raise InvalidContentError(msg)

        head = content.lstrip()[:200]
        head_lower = head.lower()
        if not any(head_lower.startswith(m) for m in _HTML_START_MARKERS):
            msg = (
                f"Response body does not look like HTML for {celex}, first 200 "
                f"bytes: {content[:200].decode('utf-8', errors='replace')!r}"
            )
            logger.error(msg)
            raise InvalidContentError(msg)

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(content)
        logger.info("Cached %s to %s", celex, cache_path)
        return content

    def _cache_path(self, celex: str) -> Path:
        safe = celex.replace("/", "_").replace(":", "_")
        return self.cache_dir / self.language / f"{safe}.html"

    def _request_with_retry(self, url: str, celex: str) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._respect_rate_limit()
            try:
                response = self._session.get(url, timeout=self.timeout_s)
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
                    celex,
                    exc,
                )
                time.sleep(2 ** attempt)
                continue

            if response.status_code == 404:
                raise NotFoundError(
                    f"CELEX {celex!r} not found (HTTP 404 from {url})"
                )
            if response.status_code in _RETRYABLE_STATUSES:
                last_error = EurLexError(
                    f"HTTP {response.status_code} from {url}"
                )
                if attempt >= self.max_retries:
                    break
                logger.warning(
                    "Retry %d/%d for %s after HTTP %d",
                    attempt + 1,
                    self.max_retries,
                    celex,
                    response.status_code,
                )
                time.sleep(2 ** attempt)
                continue
            if response.status_code >= 400:
                raise EurLexError(
                    f"HTTP {response.status_code} from {url} for CELEX {celex!r}"
                )
            return response

        logger.error(
            "Fetch failed for %s after %d retries: %s",
            celex,
            self.max_retries,
            last_error,
        )
        raise EurLexError(
            f"Fetch failed for CELEX {celex!r} after {self.max_retries} retries: {last_error}"
        )

    def _respect_rate_limit(self) -> None:
        if self._last_request_ts is None:
            return
        elapsed = time.monotonic() - self._last_request_ts
        diff = self.rate_limit_s - elapsed
        if diff > 0:
            time.sleep(diff)
