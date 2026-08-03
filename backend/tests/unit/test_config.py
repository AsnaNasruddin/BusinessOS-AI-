from app.config import get_settings


def test_settings_are_cached():
    assert get_settings() is get_settings()


def test_default_model_is_configurable_not_hardcoded():
    settings = get_settings()
    assert settings.default_model_provider == "ollama"
    assert settings.default_model_name  # non-empty, but not asserted verbatim —
    # Section 12, rule 4: model choice must stay configurable, this test just
    # confirms Settings is where it lives.
