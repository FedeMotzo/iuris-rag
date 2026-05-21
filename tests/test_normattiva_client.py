"""Unit tests for `NormattivaClient` (all HTTP mocked — no real network)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import requests
import requests_mock

from core.normattiva_client import (
    NormattivaClient,
    NormattivaError,
    NotFoundError,
    SessionError,
)
from core.normattiva_client.client import _cache_filename

URN = "urn:nir:stato:decreto.legislativo:2003-06-30;196"
NORM_PAGE_URL = f"https://www.normattiva.it/uri-res/N2Ls?{URN}!vig="
AKN_HREF_REL = "/atto/caricaAKN?id=12345&amp;art=1"
AKN_HREF_ABS = "https://www.normattiva.it/atto/caricaAKN?id=12345&art=1"
AKN_BYTES = b"<?xml version=\"1.0\"?><akomaNtoso/>"
NORM_PAGE_HTML = f'<html><body><a href="{AKN_HREF_REL}">XML</a></body></html>'


def _make_client(tmp_path: Path, **kwargs) -> NormattivaClient:
    defaults = dict(cache_dir=tmp_path / "cache", rate_limit_s=0.0, max_retries=2)
    defaults.update(kwargs)
    return NormattivaClient(**defaults)


def test_fetch_akn_happy_path(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(NORM_PAGE_URL, text=NORM_PAGE_HTML)
        m.get(AKN_HREF_ABS, content=AKN_BYTES, headers={"Content-Type": "text/xml"})

        result = client.fetch_akn(URN)

    assert result == AKN_BYTES
    cache_path = client.cache_dir / _cache_filename(URN)
    assert cache_path.exists()
    assert cache_path.read_bytes() == AKN_BYTES


def test_session_error_no_caricaAKN(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(NORM_PAGE_URL, text="<html><body>Nessun link qui</body></html>")
        with pytest.raises(SessionError) as excinfo:
            client.fetch_akn(URN)
    assert URN in str(excinfo.value)


def test_not_found_404(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(NORM_PAGE_URL, status_code=404, text="not found")
        with pytest.raises(NotFoundError) as excinfo:
            client.fetch_akn(URN)
    assert URN in str(excinfo.value)


def test_retry_on_500(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with patch("core.normattiva_client.client.time.sleep"):
        with requests_mock.Mocker() as m:
            m.get(
                NORM_PAGE_URL,
                [
                    {"status_code": 500, "text": "boom"},
                    {"status_code": 200, "text": NORM_PAGE_HTML},
                ],
            )
            m.get(AKN_HREF_ABS, content=AKN_BYTES, headers={"Content-Type": "text/xml"})
            result = client.fetch_akn(URN)
    assert result == AKN_BYTES


def test_retry_exhausted(tmp_path: Path) -> None:
    client = _make_client(tmp_path, max_retries=2)
    with patch("core.normattiva_client.client.time.sleep"):
        with requests_mock.Mocker() as m:
            m.get(NORM_PAGE_URL, status_code=500, text="boom")
            with pytest.raises(NormattivaError) as excinfo:
                client.fetch_akn(URN)
    # Generic base error, but not the more specific subclasses.
    assert not isinstance(excinfo.value, (SessionError, NotFoundError))
    assert URN in str(excinfo.value)


def test_no_retry_on_403(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(NORM_PAGE_URL, status_code=403, text="forbidden")
        with pytest.raises(NormattivaError) as excinfo:
            client.fetch_akn(URN)
        assert m.call_count == 1  # one shot, no retries
    assert "403" in str(excinfo.value)


def test_rate_limiting(tmp_path: Path) -> None:
    client = _make_client(tmp_path, rate_limit_s=1.5)
    with patch("core.normattiva_client.client.time.sleep") as mock_sleep, \
         patch("core.normattiva_client.client.time.monotonic", side_effect=[
             100.0,  # 1st call: after first HTTP request (norm page)
             100.1,  # 2nd call: when checking rate limit before AKN fetch
             100.2,  # 3rd call: after AKN HTTP request
         ]):
        with requests_mock.Mocker() as m:
            m.get(NORM_PAGE_URL, text=NORM_PAGE_HTML)
            m.get(AKN_HREF_ABS, content=AKN_BYTES, headers={"Content-Type": "text/xml"})
            client.fetch_akn(URN)

    # Exactly one rate-limit sleep between the two HTTP requests; delta was
    # 100.1 - 100.0 = 0.1s, so it should sleep 1.5 - 0.1 = 1.4s.
    rate_sleeps = [c.args[0] for c in mock_sleep.call_args_list if c.args and c.args[0] > 0]
    assert rate_sleeps == [pytest.approx(1.4, abs=1e-6)]


def test_cache_hit_skips_http(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with requests_mock.Mocker() as m:
        m.get(NORM_PAGE_URL, text=NORM_PAGE_HTML)
        m.get(AKN_HREF_ABS, content=AKN_BYTES, headers={"Content-Type": "text/xml"})
        first = client.fetch_akn(URN)
        first_call_count = m.call_count

        # Second call: cache hit, no new HTTP traffic.
        second = client.fetch_akn(URN)
        second_call_count = m.call_count

    assert first == second == AKN_BYTES
    assert first_call_count == 2  # norm page + AKN
    assert second_call_count == 2  # unchanged


def test_cache_key_sanitization(tmp_path: Path) -> None:
    filename = _cache_filename(URN)
    assert filename == "urn_nir_stato_decreto.legislativo_2003-06-30_196.xml"
    # Must be a usable filename on disk.
    target = tmp_path / filename
    target.write_bytes(b"ok")
    assert target.read_bytes() == b"ok"


def test_retry_on_connection_error(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    with patch("core.normattiva_client.client.time.sleep"):
        with requests_mock.Mocker() as m:
            m.get(
                NORM_PAGE_URL,
                [
                    {"exc": requests.ConnectionError("nope")},
                    {"status_code": 200, "text": NORM_PAGE_HTML},
                ],
            )
            m.get(AKN_HREF_ABS, content=AKN_BYTES, headers={"Content-Type": "text/xml"})
            result = client.fetch_akn(URN)
    assert result == AKN_BYTES
