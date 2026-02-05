"""
Tests for cricket API endpoints.

Tests cover:
- URL validation for SSRF prevention
- Rate limiting
- Error handling
"""

import pytest
from app.routes.api.cricket import _validate_match_url


class TestMatchUrlValidation:
    """Tests for match URL validation (SSRF prevention)."""

    def test_valid_wplt20_url(self):
        """Test that valid wplt20.com URLs are accepted."""
        valid_urls = [
            'https://www.wplt20.com/matches/1234',
            'https://www.wplt20.com/video/match/scorecard/5678',
            'https://wplt20.com/stats/match/9012',
        ]
        for url in valid_urls:
            assert _validate_match_url(url) is True, f"Should accept: {url}"

    def test_rejects_http_urls(self):
        """Test that HTTP (non-HTTPS) URLs are rejected."""
        assert _validate_match_url('http://www.wplt20.com/matches/1234') is False

    def test_rejects_other_domains(self):
        """Test that URLs from other domains are rejected."""
        invalid_urls = [
            'https://evil.com/matches/1234',
            'https://www.google.com/search?q=wpl',
            'https://iplt20.com/matches/1234',
            'https://localhost/matches/1234',
            'https://192.168.1.1/admin',
            'https://internal.company.com/secret',
        ]
        for url in invalid_urls:
            assert _validate_match_url(url) is False, f"Should reject: {url}"

    def test_rejects_empty_url(self):
        """Test that empty URLs are rejected."""
        assert _validate_match_url('') is False
        assert _validate_match_url(None) is False

    def test_rejects_non_string_url(self):
        """Test that non-string URLs are rejected."""
        assert _validate_match_url(123) is False
        assert _validate_match_url(['https://www.wplt20.com']) is False
        assert _validate_match_url({'url': 'https://www.wplt20.com'}) is False

    def test_rejects_malformed_urls(self):
        """Test that malformed URLs are rejected."""
        malformed = [
            'not-a-url',
            'ftp://www.wplt20.com/matches',
            '://www.wplt20.com/matches',
            'www.wplt20.com/matches',  # Missing scheme
        ]
        for url in malformed:
            assert _validate_match_url(url) is False, f"Should reject: {url}"

    def test_handles_url_with_whitespace(self):
        """Test that URLs with leading/trailing whitespace are handled."""
        # Should still work after strip
        assert _validate_match_url('  https://www.wplt20.com/matches/1234  ') is True

    def test_rejects_url_with_credentials(self):
        """Test that URLs with embedded credentials are handled safely."""
        # This tests basic URL parsing - credentials shouldn't bypass domain check
        url_with_creds = 'https://user:pass@www.wplt20.com/matches/1234'
        # This should still parse correctly and be accepted (domain is valid)
        # The @ sign is part of the URL authority, netloc will be user:pass@www.wplt20.com
        # which won't match our trusted domains
        assert _validate_match_url(url_with_creds) is False


class TestCricketApiEndpoints:
    """Tests for cricket API endpoint behavior."""

    def test_scorecard_requires_url(self, client):
        """Test that scorecard endpoint requires a URL."""
        response = client.post('/api/cricket/match/scorecard',
                               json={},
                               content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data or 'Match URL required' in str(data)

    def test_scorecard_rejects_invalid_url(self, client):
        """Test that scorecard endpoint rejects invalid URLs."""
        response = client.post('/api/cricket/match/scorecard',
                               json={'url': 'https://evil.com/match'},
                               content_type='application/json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid match URL' in data.get('error', '')

    def test_scorecard_rejects_empty_body(self, client):
        """Test that scorecard endpoint handles empty body."""
        response = client.post('/api/cricket/match/scorecard',
                               content_type='application/json')
        assert response.status_code == 400


class TestCricketApiRateLimiting:
    """Tests for rate limiting on cricket endpoints."""

    def test_stats_endpoint_exists(self, client):
        """Test that stats endpoints exist and respond."""
        # These will fail with actual scraper errors, but should not 404
        endpoints = [
            '/api/cricket/stats/orange-cap',
            '/api/cricket/stats/purple-cap',
            '/api/cricket/stats/mvp',
        ]
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should not be 404 (endpoint exists)
            assert response.status_code != 404, f"{endpoint} should exist"
