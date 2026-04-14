"""
Tests for crawler_engine: URL normalization and utility functions.
"""
from autoquery.crawler.crawler_engine import normalize_url


class TestNormalizeUrl:
    def test_strips_fragment(self):
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_lowercases_scheme_and_host(self):
        assert normalize_url("HTTPS://Example.COM/Page") == "https://example.com/Page"

    def test_normalize_url_strips_www(self):
        assert normalize_url("https://www.example.com/about") == "https://example.com/about"

    def test_www_and_non_www_same(self):
        assert normalize_url("https://www.ldlainc.com/about") == normalize_url("https://ldlainc.com/about")

    def test_root_path_preserved(self):
        assert normalize_url("https://example.com") == "https://example.com/"
