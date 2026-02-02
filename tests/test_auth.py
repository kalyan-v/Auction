"""
Tests for authentication functionality.

Tests login, logout, and admin_required decorator.
"""

import pytest
from flask import session


class TestLogin:
    """Tests for the login endpoint."""

    def test_login_page_renders(self, client):
        """Test that login page renders successfully."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data

    def test_login_with_valid_credentials(self, client, app):
        """Test successful login with correct credentials."""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'test-password'  # From TestingConfig
        }, follow_redirects=False)

        # Should redirect after successful login
        assert response.status_code == 302

        # Check session is set
        with client.session_transaction() as sess:
            assert sess.get('is_admin') is True

    def test_login_with_invalid_password(self, client):
        """Test login fails with wrong password."""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'wrongpassword'
        })

        assert response.status_code == 200
        assert b'Invalid' in response.data or b'invalid' in response.data

        # Session should not have admin flag
        with client.session_transaction() as sess:
            assert sess.get('is_admin') is not True

    def test_login_with_invalid_username(self, client):
        """Test login fails with wrong username."""
        response = client.post('/login', data={
            'username': 'wronguser',
            'password': 'test-password'
        })

        assert response.status_code == 200
        with client.session_transaction() as sess:
            assert sess.get('is_admin') is not True

    def test_login_redirect_to_next_url(self, client):
        """Test login redirects to next parameter if safe."""
        response = client.post('/login?next=/setup', data={
            'username': 'admin',
            'password': 'test-password'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/setup' in response.location

    def test_login_ignores_unsafe_next_url(self, client):
        """Test login ignores external redirect URLs."""
        response = client.post('/login?next=http://evil.com', data={
            'username': 'admin',
            'password': 'test-password'
        }, follow_redirects=False)

        assert response.status_code == 302
        # Should redirect to setup, not evil.com
        assert 'evil.com' not in response.location


class TestLogout:
    """Tests for the logout endpoint."""

    def test_logout_clears_session(self, auth_client):
        """Test logout clears admin session."""
        # Verify we're logged in
        with auth_client.session_transaction() as sess:
            assert sess.get('is_admin') is True

        # Logout
        response = auth_client.get('/logout', follow_redirects=False)
        assert response.status_code == 302

        # Verify session is cleared
        with auth_client.session_transaction() as sess:
            assert sess.get('is_admin') is None


class TestAdminRequired:
    """Tests for admin-protected endpoints."""

    def test_protected_endpoint_requires_auth(self, client, app, sample_league):
        """Test that protected endpoints return 403 without auth."""
        with app.app_context():
            # Try to create a team without auth
            response = client.post('/api/teams',
                json={'name': 'New Team'},
                content_type='application/json'
            )
            assert response.status_code == 403
            assert b'Admin' in response.data or b'admin' in response.data

    def test_protected_endpoint_works_with_auth(self, auth_client, app, sample_league):
        """Test that protected endpoints work with auth."""
        with app.app_context():
            # Set current league in session
            with auth_client.session_transaction() as sess:
                sess['current_league_id'] = sample_league.id

            response = auth_client.post('/api/teams',
                json={'name': 'New Team'},
                content_type='application/json'
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_healthy(self, client, app):
        """Test health check returns healthy status."""
        with app.app_context():
            response = client.get('/health')
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'healthy'
            assert data['database'] == 'connected'
