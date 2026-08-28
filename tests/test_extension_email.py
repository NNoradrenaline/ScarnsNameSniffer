import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "browser-extension"


def test_extension_manifest_wires_email_helper():
    manifest = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == 3
    assert manifest["version"] == "2.5.1"
    assert manifest["background"]["service_worker"] == "background.js"
    assert "https://users.roblox.com/*" in manifest["host_permissions"]

    scripts = manifest["content_scripts"]
    assert any(
        "email.js" in entry.get("js", [])
        and "https://www.roblox.com/*" in entry.get("matches", [])
        for entry in scripts
    )


def test_popup_exposes_email_controls():
    html = (EXT / "popup.html").read_text(encoding="utf-8")
    assert 'id="email"' in html
    assert 'id="auto-email"' in html
    assert 'id="clear-email"' in html


def test_content_script_arms_email_without_persistent_password_storage():
    content = (EXT / "content.js").read_text(encoding="utf-8")
    assert "armEmailSetup" in content
    assert "scarn:storePendingSecret" in content
    assert "chrome.storage.session" not in content


def test_email_helper_stops_at_verification_request():
    email = (EXT / "email.js").read_text(encoding="utf-8")
    assert "scarn:getAuthenticatedUser" in email
    assert "findAddEmailButton" in email
    assert "findExistingEmailControl" in email
    assert "scarn:getPendingSecret" in email
    assert "Verification requested" in email
    assert "verify it manually" in email
    assert "inbox" in email.lower()


def test_background_owns_session_secret():
    background = (EXT / "background.js").read_text(encoding="utf-8")
    assert "chrome.storage.session.set" in background
    assert "chrome.storage.session.get" in background
    assert "chrome.storage.session.remove" in background
    assert "pendingSignupSecret" in background
