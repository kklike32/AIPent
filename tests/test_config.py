from tracker.config import DEFAULT_VERTEX_MODEL, TrackerConfig, normalize_llm_model


def test_normalize_llm_model_keeps_official_vertex_model() -> None:
    assert normalize_llm_model("gemini-3.5-flash") == DEFAULT_VERTEX_MODEL


def test_normalize_llm_model_maps_friendly_flash_light_alias() -> None:
    assert normalize_llm_model("gemini-3.1-flash-light") == DEFAULT_VERTEX_MODEL


def test_normalize_llm_model_maps_flash_lite_alias() -> None:
    assert normalize_llm_model("gemini-3.1-flash-lite") == DEFAULT_VERTEX_MODEL


def test_config_reads_capture_and_insforge_user(monkeypatch) -> None:
    monkeypatch.setenv("SCREENSHOT_INTERVAL_SECONDS", "1")
    monkeypatch.setenv("ENABLE_AUDIO_CAPTURE", "true")
    monkeypatch.setenv("AUDIO_INPUT_DEVICE", ":1")
    monkeypatch.setenv("INSFORGE_CURRENT_USER_ID", "user-1")

    config = TrackerConfig.from_env()

    assert config.screenshot_interval_seconds == 1
    assert config.enable_audio_capture is True
    assert config.audio_input_device == ":1"
    assert config.insforge_current_user_id == "user-1"
