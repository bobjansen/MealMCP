"""CSRF protection on the Flask web interface."""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import app_flask


class TestCSRF(unittest.TestCase):
    def setUp(self):
        app_flask.app.config["TESTING"] = True
        app_flask.app.config["WTF_CSRF_ENABLED"] = True
        self.client = app_flask.app.test_client()

    def tearDown(self):
        app_flask.app.config["WTF_CSRF_ENABLED"] = False

    def test_post_without_token_is_rejected(self):
        resp = self.client.post(
            "/preferences/add",
            data={"category": "like", "item": "x", "level": "preferred"},
        )
        # form endpoints get a friendly redirect, not a bare 400
        self.assertEqual(resp.status_code, 302)

    def test_post_with_token_passes_csrf(self):
        page = self.client.get("/preferences").data.decode()
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        resp = self.client.post(
            "/preferences/add",
            data={
                "csrf_token": token,
                "category": "like",
                "item": "x",
                "level": "preferred",
            },
        )
        self.assertNotEqual(resp.status_code, 400)

    def test_json_api_requires_csrf_header(self):
        no_header = self.client.post("/api/chat", json={"message": "hi"})
        self.assertEqual(no_header.status_code, 400)

        meta = re.search(
            r'name="csrf-token" content="([^"]+)"', self.client.get("/").data.decode()
        ).group(1)
        with_header = self.client.post(
            "/api/chat", json={"message": "hi"}, headers={"X-CSRFToken": meta}
        )
        # 503 (no OpenRouter key) means the request got past CSRF
        self.assertNotEqual(with_header.status_code, 400)

    def test_pages_render_csrf_meta_tag(self):
        page = self.client.get("/preferences", follow_redirects=True).data.decode()
        self.assertIn('name="csrf-token"', page)


if __name__ == "__main__":
    unittest.main()
