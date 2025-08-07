#!/usr/bin/env python3
"""Tests for wildcard redirect URI matching in OAuthServer."""

import json
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_core.auth.oauth_server import OAuthServer


@contextmanager
def setup_server(allowed_uris):
    """Create OAuthServer with temporary database populated with allowed URIs."""
    with patch.object(OAuthServer, "init_database"), patch.object(
        OAuthServer, "_load_tokens_from_db"
    ):
        server = OAuthServer(use_postgresql=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        server.db_path = Path(tmpdir) / "oauth.db"
        server.init_database()
        client_id = "test_client"
        with sqlite3.connect(server.db_path) as conn:
            conn.execute(
                "INSERT INTO oauth_clients (client_id, client_secret, redirect_uris, client_name) VALUES (?, ?, ?, ?)",
                (client_id, "secret", json.dumps(allowed_uris), "Test"),
            )
        yield server, client_id


def test_query_param_wildcard():
    allowed = ["https://example.com/callback?param=*"]
    with setup_server(allowed) as (server, client_id):
        assert server.validate_redirect_uri(
            client_id, "https://example.com/callback?param=value"
        )


def test_filename_extension_wildcard():
    allowed = ["https://example.com/file-*.txt"]
    with setup_server(allowed) as (server, client_id):
        assert server.validate_redirect_uri(
            client_id, "https://example.com/file-test.txt"
        )


def test_plus_character_wildcard():
    allowed = ["https://example.com/query+value*"]
    with setup_server(allowed) as (server, client_id):
        assert server.validate_redirect_uri(
            client_id, "https://example.com/query+value123"
        )


def test_fullmatch_enforced():
    allowed = ["https://example.com/callback*end"]
    with setup_server(allowed) as (server, client_id):
        assert not server.validate_redirect_uri(
            client_id, "https://example.com/callbackmiddleendextra"
        )
        assert server.validate_redirect_uri(
            client_id, "https://example.com/callbackmiddleend"
        )
