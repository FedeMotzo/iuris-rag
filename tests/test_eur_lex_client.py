"""Unit tests for `EurLexClient` (all HTTP mocked — no real network)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import requests_mock

from core.eur_lex_client import (
    EurLexClient,
    EurLexError,
    InvalidContentError,
    NotFoundError,
)

CELEX = "32016R0679"
URL_IT = f"https://eur-lex.europa.eu/legal-content/IT/TXT/HTML/?uri=CELEX:{CELEX}"
URL_EN = f"https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:{CELEX}"
# Body large enough to pass the MIN_HTML_SIZE guard on the client.
HTML_BYTES = b"<!DOCTYPE html><html><body>GDPR " + b"x" * 12_000 + b"</body></html>"


def _make_client(tmp_path: Path, **kwargs) -> EurLexClient:
    defaults = dict(cache_dir=tmp_path / "cache", rate_limit_s=0.0, max_retries=2)
    defaults.update(kwargs)
    return EurLexClient(**defaults)


def test_fetch_html_happy_path(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(URL_IT, content=HTML_BYTES, headers={"Content-Type": "text/html; charset=utf-8"})
        result = client.fetch_html(CELEX)

    assert result == HTML_BYTES
    cached = tmp_path / "cache" / "IT" / f"{CELEX}.html"
    assert cached.exists()
    assert cached.read_bytes() == HTML_BYTES


def test_not_found_404(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(URL_IT, status_code=404, text="not found")
        with pytest.raises(NotFoundError) as excinfo:
            client.fetch_html(CELEX)
    assert CELEX in str(excinfo.value)


def test_invalid_content_type(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(URL_IT, content=b"<xml/>", headers={"Content-Type": "application/xml"})
        with pytest.raises(InvalidContentError) as excinfo:
            client.fetch_html(CELEX)
    assert CELEX in str(excinfo.value)
    # Must not have written anything to cache.
    assert not (tmp_path / "cache" / "IT" / f"{CELEX}.html").exists()


def test_missing_content_type_is_tolerated(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        # requests_mock sends no Content-Type when headers dict omits it AND we use
        # an empty headers override; pass through `headers={}` with explicit removal.
        m.get(URL_IT, content=HTML_BYTES, headers={"Content-Type": ""})
        result = client.fetch_html(CELEX)
    assert result == HTML_BYTES


def test_retry_on_500(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with patch("core.eur_lex_client.client.time.sleep"):
        with requests_mock.Mocker() as m:
            m.get(
                URL_IT,
                [
                    {"status_code": 500, "text": "boom"},
                    {
                        "status_code": 200,
                        "content": HTML_BYTES,
                        "headers": {"Content-Type": "text/html"},
                    },
                ],
            )
            result = client.fetch_html(CELEX)
    assert result == HTML_BYTES


def test_retry_exhausted(tmp_path: Path) -> None:
    client = _make_client(tmp_path, max_retries=2)
    with patch("core.eur_lex_client.client.time.sleep"):
        with requests_mock.Mocker() as m:
            m.get(URL_IT, status_code=500, text="boom")
            with pytest.raises(EurLexError) as excinfo:
                client.fetch_html(CELEX)
    assert not isinstance(excinfo.value, (NotFoundError, InvalidContentError))
    assert CELEX in str(excinfo.value)


def test_no_retry_on_403(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(URL_IT, status_code=403, text="forbidden")
        with pytest.raises(EurLexError) as excinfo:
            client.fetch_html(CELEX)
        assert m.call_count == 1
    assert "403" in str(excinfo.value)


def test_rate_limiting(tmp_path: Path) -> None:
    client = _make_client(tmp_path, rate_limit_s=1.5)
    # Force a second HTTP call by clearing the cache between calls; easier:
    # use two distinct CELEX so both miss cache.
    celex_a = "32016R0679"
    celex_b = "32024R1689"
    url_b = f"https://eur-lex.europa.eu/legal-content/IT/TXT/HTML/?uri=CELEX:{celex_b}"

    with patch("core.eur_lex_client.client.time.sleep") as mock_sleep, patch(
        "core.eur_lex_client.client.time.monotonic",
        side_effect=[
            100.0,  # after first GET (celex_a)
            100.2,  # check before second GET
            100.3,  # after second GET
        ],
    ):
        with requests_mock.Mocker() as m:
            m.get(URL_IT, content=HTML_BYTES, headers={"Content-Type": "text/html"})
            m.get(url_b, content=HTML_BYTES, headers={"Content-Type": "text/html"})
            client.fetch_html(celex_a)
            client.fetch_html(celex_b)

    rate_sleeps = [c.args[0] for c in mock_sleep.call_args_list if c.args and c.args[0] > 0]
    # delta = 100.2 - 100.0 = 0.2; expected sleep = 1.5 - 0.2 = 1.3
    assert rate_sleeps == [pytest.approx(1.3, abs=1e-6)]


def test_cache_hit_skips_http(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(URL_IT, content=HTML_BYTES, headers={"Content-Type": "text/html"})
        first = client.fetch_html(CELEX)
        first_count = m.call_count

        second = client.fetch_html(CELEX)
        second_count = m.call_count

    assert first == second == HTML_BYTES
    assert first_count == 1
    assert second_count == 1


def test_cache_separated_by_language(tmp_path: Path) -> None:
    it_client = _make_client(tmp_path, language="IT")
    en_client = _make_client(tmp_path, language="EN")
    it_body = b"<!DOCTYPE html><html><body>IT " + b"i" * 12_000 + b"</body></html>"
    en_body = b"<!DOCTYPE html><html><body>EN " + b"e" * 12_000 + b"</body></html>"
    with requests_mock.Mocker() as m:
        m.get(URL_IT, content=it_body, headers={"Content-Type": "text/html"})
        m.get(URL_EN, content=en_body, headers={"Content-Type": "text/html"})
        it_bytes = it_client.fetch_html(CELEX)
        en_bytes = en_client.fetch_html(CELEX)
        assert m.call_count == 2

    it_path = tmp_path / "cache" / "IT" / f"{CELEX}.html"
    en_path = tmp_path / "cache" / "EN" / f"{CELEX}.html"
    assert it_path.exists() and en_path.exists()
    assert it_path.read_bytes() == it_bytes == it_body
    assert en_path.read_bytes() == en_bytes == en_body


def test_retry_on_connection_error(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with patch("core.eur_lex_client.client.time.sleep"):
        with requests_mock.Mocker() as m:
            m.get(
                URL_IT,
                [
                    {"exc": requests.ConnectionError("nope")},
                    {
                        "status_code": 200,
                        "content": HTML_BYTES,
                        "headers": {"Content-Type": "text/html"},
                    },
                ],
            )
            result = client.fetch_html(CELEX)
    assert result == HTML_BYTES


def test_rejects_empty_body(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(URL_IT, content=b"", headers={"Content-Type": "text/html"})
        with pytest.raises(InvalidContentError) as excinfo:
            client.fetch_html(CELEX)
    assert "too small" in str(excinfo.value).lower()
    assert not (tmp_path / "cache" / "IT" / f"{CELEX}.html").exists()


def test_rejects_too_small_body(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    small_body = b"<!DOCTYPE html><html><body>" + b"x" * 5_000 + b"</body></html>"
    assert len(small_body) < 10_000  # sanity-check the fixture itself
    with requests_mock.Mocker() as m:
        m.get(URL_IT, content=small_body, headers={"Content-Type": "text/html"})
        with pytest.raises(InvalidContentError) as excinfo:
            client.fetch_html(CELEX)
    assert "too small" in str(excinfo.value).lower()
    assert CELEX in str(excinfo.value)
    assert not (tmp_path / "cache" / "IT" / f"{CELEX}.html").exists()


def test_rejects_non_html_body(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    json_body = b'{"error":"some api error","detail":"' + b"x" * 20_000 + b'"}'
    assert len(json_body) >= 10_000
    with requests_mock.Mocker() as m:
        m.get(URL_IT, content=json_body, headers={"Content-Type": "text/html"})
        with pytest.raises(InvalidContentError) as excinfo:
            client.fetch_html(CELEX)
    assert "does not look like html" in str(excinfo.value).lower()
    assert not (tmp_path / "cache" / "IT" / f"{CELEX}.html").exists()


def test_accepts_html_with_leading_whitespace(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    body = b"\n  \n<!DOCTYPE html>\n<html><body>" + b"x" * 12_000 + b"</body></html>"
    with requests_mock.Mocker() as m:
        m.get(URL_IT, content=body, headers={"Content-Type": "text/html"})
        result = client.fetch_html(CELEX)
    assert result == body


def test_accepts_html_uppercase_doctype(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    body = b"<!DOCTYPE HTML><html><body>" + b"x" * 12_000 + b"</body></html>"
    with requests_mock.Mocker() as m:
        m.get(URL_IT, content=body, headers={"Content-Type": "text/html"})
        result = client.fetch_html(CELEX)
    assert result == body
