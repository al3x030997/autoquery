"""
Tests for page_classifier: page type classification (Ollama & Claude backends).
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autoquery.crawler.page_classifier import (
    PageType,
    _parse_page_type,
    classify_page,
)

SAMPLE_HTML = "<html><body><h1>Our Agents</h1><p>Some content here.</p></body></html>"
SAMPLE_URL = "https://example.com/agents"


# --- _parse_page_type unit tests ---


class TestParsePageType:
    def test_valid_index(self):
        assert _parse_page_type('{"page_type": "INDEX"}') == PageType.INDEX

    def test_valid_content(self):
        assert _parse_page_type('{"page_type": "CONTENT"}') == PageType.CONTENT

    def test_valid_multi_agent(self):
        assert _parse_page_type('{"page_type": "MULTI_AGENT"}') == PageType.MULTI_AGENT

    def test_valid_unknown(self):
        assert _parse_page_type('{"page_type": "UNKNOWN"}') == PageType.UNKNOWN

    def test_lowercase_normalised(self):
        assert _parse_page_type('{"page_type": "index"}') == PageType.INDEX

    def test_extra_text_around_json(self):
        assert _parse_page_type('Sure! Here is the answer: {"page_type": "CONTENT"} hope that helps') == PageType.CONTENT

    def test_missing_field_returns_unknown(self):
        assert _parse_page_type('{"other": "value"}') == PageType.UNKNOWN

    def test_no_json_returns_unknown(self):
        assert _parse_page_type("no json here") == PageType.UNKNOWN

    def test_invalid_value_returns_unknown(self):
        assert _parse_page_type('{"page_type": "BANANA"}') == PageType.UNKNOWN

    def test_client_bio_maps_to_unknown(self):
        assert _parse_page_type('{"page_type": "CLIENT_BIO"}') == PageType.UNKNOWN


# --- Claude backend tests ---


class TestClassifyClaude:
    @pytest.mark.asyncio
    async def test_classify_content(self):
        mock_client = AsyncMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"page_type": "CONTENT"}')]
        mock_client.messages.create = AsyncMock(return_value=mock_msg)

        with patch("autoquery.crawler.page_classifier._get_claude_client", return_value=mock_client):
            result = await classify_page(SAMPLE_HTML, SAMPLE_URL, "http://unused:11434", classifier_backend="claude")

        assert result == PageType.CONTENT

    @pytest.mark.asyncio
    async def test_classify_multi_agent(self):
        mock_client = AsyncMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"page_type": "MULTI_AGENT"}')]
        mock_client.messages.create = AsyncMock(return_value=mock_msg)

        with patch("autoquery.crawler.page_classifier._get_claude_client", return_value=mock_client):
            result = await classify_page(SAMPLE_HTML, SAMPLE_URL, "http://unused:11434", classifier_backend="claude")

        assert result == PageType.MULTI_AGENT

    @pytest.mark.asyncio
    async def test_classify_index(self):
        mock_client = AsyncMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"page_type": "INDEX"}')]
        mock_client.messages.create = AsyncMock(return_value=mock_msg)

        with patch("autoquery.crawler.page_classifier._get_claude_client", return_value=mock_client):
            result = await classify_page(SAMPLE_HTML, SAMPLE_URL, "http://unused:11434", classifier_backend="claude")

        assert result == PageType.INDEX

    @pytest.mark.asyncio
    async def test_claude_error_returns_unknown(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))

        with patch("autoquery.crawler.page_classifier._get_claude_client", return_value=mock_client):
            result = await classify_page(SAMPLE_HTML, SAMPLE_URL, "http://unused:11434", classifier_backend="claude")

        assert result == PageType.UNKNOWN

    @pytest.mark.asyncio
    async def test_claude_extra_text_around_json(self):
        mock_client = AsyncMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='Here is the classification: {"page_type": "MULTI_AGENT"} done.')]
        mock_client.messages.create = AsyncMock(return_value=mock_msg)

        with patch("autoquery.crawler.page_classifier._get_claude_client", return_value=mock_client):
            result = await classify_page(SAMPLE_HTML, SAMPLE_URL, "http://unused:11434", classifier_backend="claude")

        assert result == PageType.MULTI_AGENT


# --- Ollama backend tests ---


class TestClassifyOllama:
    @pytest.mark.asyncio
    async def test_classify_index(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"response": '{"page_type": "INDEX"}'}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("autoquery.crawler.page_classifier.httpx.AsyncClient", return_value=mock_client):
            result = await classify_page(SAMPLE_HTML, SAMPLE_URL, "http://ollama:11434", classifier_backend="ollama")

        assert result == PageType.INDEX

    @pytest.mark.asyncio
    async def test_ollama_error_returns_unknown(self):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("autoquery.crawler.page_classifier.httpx.AsyncClient", return_value=mock_client):
            result = await classify_page(SAMPLE_HTML, SAMPLE_URL, "http://ollama:11434", classifier_backend="ollama")

        assert result == PageType.UNKNOWN

    @pytest.mark.asyncio
    async def test_ollama_no_json_returns_unknown(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"response": "I cannot classify this page"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("autoquery.crawler.page_classifier.httpx.AsyncClient", return_value=mock_client):
            result = await classify_page(SAMPLE_HTML, SAMPLE_URL, "http://ollama:11434", classifier_backend="ollama")

        assert result == PageType.UNKNOWN


# --- Backend selection tests ---


class TestBackendSelection:
    @pytest.mark.asyncio
    async def test_env_var_selects_backend(self):
        """CLASSIFIER_BACKEND env var selects the backend when no kwarg given."""
        mock_client = AsyncMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text='{"page_type": "CONTENT"}')]
        mock_client.messages.create = AsyncMock(return_value=mock_msg)

        with (
            patch.dict("os.environ", {"CLASSIFIER_BACKEND": "claude"}),
            patch("autoquery.crawler.page_classifier._get_claude_client", return_value=mock_client),
        ):
            result = await classify_page(SAMPLE_HTML, SAMPLE_URL, "http://unused:11434")

        assert result == PageType.CONTENT
        mock_client.messages.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_kwarg_overrides_env(self):
        """classifier_backend kwarg overrides CLASSIFIER_BACKEND env var."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"response": '{"page_type": "INDEX"}'}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with (
            patch.dict("os.environ", {"CLASSIFIER_BACKEND": "claude"}),
            patch("autoquery.crawler.page_classifier.httpx.AsyncClient", return_value=mock_client),
        ):
            result = await classify_page(SAMPLE_HTML, SAMPLE_URL, "http://ollama:11434", classifier_backend="ollama")

        assert result == PageType.INDEX
