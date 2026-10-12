"""Sharing publishes only a saved shopping list, never an authenticated session."""

import re
import json
import shutil
import subprocess
from datetime import date
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

import pytest
from bs4 import BeautifulSoup

import app_flask
from grocery_shares import GroceryShares


@pytest.fixture
def sharing(tmp_path, monkeypatch):
    monkeypatch.setattr(app_flask.i18n, "LANG", "en")
    store = GroceryShares("sqlite", str(tmp_path / "shares.db"))
    monkeypatch.setattr(app_flask, "get_grocery_shares", lambda: store)
    monkeypatch.setattr(app_flask.auth_ctx, "backend", "postgresql")
    monkeypatch.setattr(
        app_flask.auth_ctx.auth_manager, "get_user_by_id", lambda uid: {"id": uid}
    )
    pantry = Mock()
    pantry.get_grocery_list.return_value = [
        {
            "name": "Tomatoes & basil",
            "quantity": 2.5,
            "unit": "kg",
            "private": "secret",
        },
        {"name": '<script>alert("x")</script>', "quantity": 1, "unit": "Piece"},
    ]
    pantry.get_meal_plan.return_value = []
    pantry.get_all_recipes.return_value = []
    monkeypatch.setattr(app_flask, "get_current_user_pantry", lambda: pantry)
    monkeypatch.setitem(app_flask.app.config, "TESTING", True)
    monkeypatch.setitem(app_flask.app.config, "WTF_CSRF_ENABLED", True)
    return store, pantry


def publish():
    owner = app_flask.app.test_client()
    with owner.session_transaction() as session:
        session["user_id"] = 7
    page = owner.get("/meal-plan").get_data(as_text=True)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    response = owner.post("/meal-plan/share", data={"csrf_token": csrf})
    assert response.status_code == 303
    return response.headers["Location"]


def test_anonymous_recipient_sees_saved_list_and_whatsapp_url(sharing):
    store, pantry = sharing
    url = publish()
    pantry.get_grocery_list.return_value = []
    pantry.get_grocery_list.reset_mock()
    recipient = app_flask.app.test_client()
    response = recipient.get(url)
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Tomatoes &amp; basil" in page
    assert "2.5 kg" in page
    assert "&lt;script&gt;" in page
    assert '<script>alert("x")</script>' not in page
    assert "secret" not in page
    assert "Login" not in page
    html = BeautifulSoup(page, "html.parser")
    assert len(html.select('.shopping-item input[type="checkbox"]')) == 2
    assert all(item.find_parent("label") for item in html.select("[data-item-index]"))
    assert (
        html.select_one('meta[name="viewport"]')["content"]
        == "width=device-width, initial-scale=1.0"
    )
    whatsapp = html.select_one("a.whatsapp")["href"]
    assert parse_qs(urlparse(whatsapp).query)["text"] == [
        "Grocery List\nhttp://localhost" + url
    ]
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    pantry.get_grocery_list.assert_not_called()
    # A new store instance can read the same URL after a restart.
    reopened = GroceryShares("sqlite", store.db.connection_string)
    assert (
        reopened.get(url.rsplit("/", 1)[-1])["items"][0]["name"] == "Tomatoes & basil"
    )


def test_sharing_requires_login_and_csrf(sharing):
    anonymous = app_flask.app.test_client()
    with app_flask.app.test_request_context():
        from flask_wtf.csrf import generate_csrf

        token = generate_csrf()
        from flask import session

        csrf_secret = session["csrf_token"]
    with anonymous.session_transaction() as session:
        session["csrf_token"] = csrf_secret
    response = anonymous.post("/meal-plan/share", data={"csrf_token": token})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    owner = app_flask.app.test_client()
    with owner.session_transaction() as session:
        session["user_id"] = 7
    response = owner.post("/meal-plan/share")
    assert response.status_code == 302
    assert sharing[1].get_grocery_list.call_count == 0


def test_unknown_tokens_and_public_writes_are_rejected(sharing):
    client = app_flask.app.test_client()
    assert client.get("/shopping-list/unknown").status_code == 404
    assert client.get("/shopping-list/" + "a" * 43).status_code == 404
    url = publish()
    assert client.post(url).status_code == 405


def test_independent_lists_empty_list_and_dutch(sharing):
    store, _ = sharing
    first = store.create(
        [{"name": "Milk", "quantity": 1, "unit": "Liter"}], date.today(), "en"
    )
    second = store.create([], date.today(), "nl")
    assert first != second
    client = app_flask.app.test_client()
    page = client.get("/shopping-list/" + second).get_data(as_text=True)
    assert "Milk" not in page
    assert "Delen via WhatsApp" in page
    assert 'lang="nl"' in page


def test_basket_ticks_survive_reopening_and_stay_specific_to_the_list(sharing):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to exercise the checklist JavaScript")
    url = publish()
    page = app_flask.app.test_client().get(url).get_data(as_text=True)
    script = BeautifulSoup(page, "html.parser").find("script").string
    harness = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const script = SCRIPT;
const saved = new Map();
const storage = {
    getItem(key) { return saved.get(key) || null; },
    setItem(key, value) { saved.set(key, value); }
};
function openList(path, localStorage = storage) {
    const boxes = ['0', '1'].map(index => ({
        dataset: { itemIndex: index }, checked: false,
        addEventListener(event, callback) { this.change = callback; }
    }));
    const progress = { textContent: '' };
    const document = {
        querySelectorAll() { return boxes; },
        getElementById(id) {
            return id === 'basket-progress' ? progress : { addEventListener() {} };
        }
    };
    vm.runInNewContext(script, { document, window: { location: { pathname: path } }, localStorage });
    return { boxes, progress };
}
const first = openList('/shopping-list/one');
assert.equal(first.progress.textContent, '0 of 2 items in your basket');
first.boxes[0].checked = true;
first.boxes[0].change();
assert.equal(first.progress.textContent, '1 of 2 items in your basket');
const reopened = openList('/shopping-list/one');
assert.equal(reopened.boxes[0].checked, true);
assert.equal(reopened.boxes[1].checked, false);
assert.equal(openList('/shopping-list/two').boxes[0].checked, false);
reopened.boxes[0].checked = false;
reopened.boxes[0].change();
assert.equal(openList('/shopping-list/one').boxes[0].checked, false);
const blocked = openList('/shopping-list/three', {
    getItem() { throw Error('disabled'); },
    setItem() { throw Error('disabled'); }
});
blocked.boxes[1].checked = true;
blocked.boxes[1].change();
assert.equal(blocked.progress.textContent, '1 of 2 items in your basket');
saved.set('shopping-list:/shopping-list/four', 'invalid json');
assert.equal(openList('/shopping-list/four').boxes[0].checked, false);
"""
    subprocess.run(
        [node, "-e", harness.replace("SCRIPT", json.dumps(script))],
        check=True,
        capture_output=True,
        text=True,
    )
