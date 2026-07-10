from app.core.config import Settings


def test_settings_are_safe_without_api_key() -> None:
    settings = Settings(DASHSCOPE_API_KEY="")

    assert settings.qwen_configured is False
    assert settings.qwen_model == "qwen3.7-plus"
    assert settings.qwen_base_url.endswith("/compatible-mode/v1")


def test_settings_detect_configured_key() -> None:
    settings = Settings(DASHSCOPE_API_KEY="sk-test-not-real")

    assert settings.qwen_configured is True
    assert "sk-test-not-real" not in str(settings)
