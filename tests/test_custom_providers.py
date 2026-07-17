"""Tests für die Custom-Provider-Registry (mehrere eigene Endpoints).

Deckt die pure Config-Logik ab: Slug-Helfer, CRUD, model-Key-Übersetzung
(configparser verträgt kein ':' im Options-Namen), all_providers,
current_api-Validierung und die Legacy-Migration des früheren einzelnen
Custom-Endpoints. Läuft gegen eine **isolierte** ConfigManager-Instanz
(eigene tmp-config.ini), rührt weder die echte Config noch den Keyring an.
"""
import configparser

import pytest

from talktrace_ai.config.config_manager import (
    ConfigManager,
    KNOWN_PROVIDERS,
    custom_provider_id,
    custom_provider_slug,
    is_custom_provider,
)


def _cm(tmp_path):
    """Ein ConfigManager, der nur auf eine tmp-config.ini schreibt."""
    cm = ConfigManager.__new__(ConfigManager)
    cm.config = configparser.ConfigParser()
    cm.config_dir = tmp_path
    cm.config_file = tmp_path / "config.ini"
    cm.default_config = tmp_path / "does-not-exist.ini"
    cm._legacy_custom_key_id = None
    cm.required_sections = ["PROMPTS", "MODELS", "ADVANCED"]
    for s in cm.required_sections:
        cm.config.add_section(s)
    return cm


# --- Slug-Helfer ----------------------------------------------------------

def test_slug_helpers_roundtrip():
    assert is_custom_provider("custom:uni-vllm")
    assert not is_custom_provider("openai")
    assert not is_custom_provider(None)
    assert custom_provider_id("custom:uni-vllm") == "uni-vllm"
    assert custom_provider_id("openai") is None
    assert custom_provider_slug("uni-vllm") == "custom:uni-vllm"


# --- CRUD -----------------------------------------------------------------

def test_add_and_list_custom_provider(tmp_path):
    cm = _cm(tmp_path)
    pid = cm.add_custom_provider("Uni vLLM", "https://host.example/v1/")
    assert pid == "uni-vllm"
    entries = cm.list_custom_providers()
    assert len(entries) == 1
    assert entries[0]["name"] == "Uni vLLM"
    # Trailing slash stripped.
    assert entries[0]["base_url"] == "https://host.example/v1"
    assert cm.custom_base_url(custom_provider_slug(pid)) == "https://host.example/v1"
    assert cm.custom_base_url(pid) == "https://host.example/v1"  # bare id also ok


def test_add_multiple_and_id_collision(tmp_path):
    cm = _cm(tmp_path)
    a = cm.add_custom_provider("My Server", "https://a/v1")
    b = cm.add_custom_provider("My Server", "https://b/v1")
    c = cm.add_custom_provider("My Server", "https://c/v1")
    assert [a, b, c] == ["my-server", "my-server-2", "my-server-3"]
    assert len(cm.list_custom_providers()) == 3


def test_update_custom_provider(tmp_path):
    cm = _cm(tmp_path)
    pid = cm.add_custom_provider("Old", "https://old/v1")
    assert cm.update_custom_provider(pid, name="New", base_url="https://new/v2/")
    e = cm.get_custom_provider(pid)
    assert e["name"] == "New"
    assert e["base_url"] == "https://new/v2"
    assert not cm.update_custom_provider("nope", name="x")


def test_remove_custom_provider_drops_models(tmp_path):
    cm = _cm(tmp_path)
    pid = cm.add_custom_provider("Srv", "https://srv/v1")
    slug = custom_provider_slug(pid)
    cm.add_model(slug, "my-model", 1.0, 2.0)
    assert cm.get_models(slug) == ["my-model"]
    assert cm.config.has_option("MODELS", f"custom_{pid}_models")
    assert cm.remove_custom_provider(pid)
    assert cm.list_custom_providers() == []
    assert not cm.config.has_option("MODELS", f"custom_{pid}_models")
    assert not cm.remove_custom_provider(pid)  # second call: nothing to do


# --- Modelle & Preise routen über custom_<id>_models ----------------------

def test_models_key_uses_underscore_not_colon(tmp_path):
    cm = _cm(tmp_path)
    assert cm._models_key("openai") == "openai_models"
    assert cm._models_key("custom:uni-vllm") == "custom_uni-vllm_models"


def test_set_get_models_for_custom_slug(tmp_path):
    cm = _cm(tmp_path)
    pid = cm.add_custom_provider("Srv", "https://srv/v1")
    slug = custom_provider_slug(pid)
    cm.set_models(slug, [{"name": "m1", "input": 0, "output": 0, "local": False}])
    assert cm.get_models(slug) == ["m1"]
    # …and shows up in the combined (provider=None) list.
    assert "m1" in cm.get_models()


def test_pricing_includes_custom(tmp_path):
    cm = _cm(tmp_path)
    pid = cm.add_custom_provider("Srv", "https://srv/v1")
    slug = custom_provider_slug(pid)
    cm.add_model(slug, "m1", 1.5, 3.0)
    pricing = cm.get_api_pricing()
    assert pricing[slug]["m1"] == {"input": 1.5, "output": 3.0}


def test_all_providers_lists_builtins_plus_custom(tmp_path):
    cm = _cm(tmp_path)
    pid = cm.add_custom_provider("Srv", "https://srv/v1")
    providers = cm.all_providers()
    assert providers[: len(KNOWN_PROVIDERS)] == list(KNOWN_PROVIDERS)
    assert custom_provider_slug(pid) in providers
    assert "custom" not in providers  # bare legacy slug is gone


# --- current_api-Validierung ---------------------------------------------

def test_set_current_api_accepts_custom_slug(tmp_path):
    cm = _cm(tmp_path)
    pid = cm.add_custom_provider("Srv", "https://srv/v1")
    slug = custom_provider_slug(pid)
    cm.set_current_api(slug)
    assert cm.get_current_api() == slug


def test_current_api_snaps_back_when_custom_deleted(tmp_path):
    cm = _cm(tmp_path)
    pid = cm.add_custom_provider("Srv", "https://srv/v1")
    slug = custom_provider_slug(pid)
    cm.set_current_api(slug)
    cm.remove_custom_provider(pid)
    # Pointing at a now-deleted custom provider must migrate to the default.
    assert cm.get_current_api() == KNOWN_PROVIDERS[0]


def test_set_current_api_rejects_unknown(tmp_path):
    cm = _cm(tmp_path)
    with pytest.raises(ValueError):
        cm.set_current_api("bogus")
    with pytest.raises(ValueError):
        cm.set_current_api("custom")  # bare legacy slug no longer valid


# --- Legacy-Migration -----------------------------------------------------

def test_migrate_legacy_custom_folds_single_endpoint(tmp_path, monkeypatch):
    # Keyring hermetisch halten: kein echter Zugriff/Schreibvorgang.
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda *a, **k: None)
    cm = _cm(tmp_path)
    cm.config.add_section("CUSTOM")
    cm.config.set("CUSTOM", "base_url", "https://legacy.example/v1")
    cm.config.set("MODELS", "custom_models",
                  "[{'name': 'legacy-model', 'input': 1, 'output': 2, 'local': False}]")

    cm.migrate_legacy_custom()

    entries = cm.list_custom_providers()
    assert len(entries) == 1
    e = entries[0]
    assert e["from_legacy"] is True
    assert e["base_url"] == "https://legacy.example/v1"
    # Modelle wandern unter den neuen Key.
    assert cm.get_models(custom_provider_slug(e["id"])) == ["legacy-model"]
    # Legacy-Marker geleert.
    assert cm.config.get("CUSTOM", "base_url") == ""
    assert not cm.config.has_option("MODELS", "custom_models")
    assert cm._legacy_custom_key_id == e["id"]


def test_migrate_legacy_custom_is_idempotent(tmp_path, monkeypatch):
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda *a, **k: None)
    cm = _cm(tmp_path)
    cm.config.add_section("CUSTOM")
    cm.config.set("CUSTOM", "base_url", "https://legacy.example/v1")
    cm.migrate_legacy_custom()
    cm.migrate_legacy_custom()  # zweiter Lauf: kein zweiter Eintrag
    assert len(cm.list_custom_providers()) == 1


def test_migrate_noop_on_fresh_install(tmp_path):
    cm = _cm(tmp_path)
    # Frisch: kein [CUSTOM], leere custom_models — nichts zu migrieren.
    cm.config.set("MODELS", "custom_models", "[]")
    cm.migrate_legacy_custom()
    assert cm.list_custom_providers() == []
