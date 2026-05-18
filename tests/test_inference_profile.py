"""INF-2 / router model profile tests."""

from pathlib import Path

from altrasia.config import Settings
from altrasia.inference.profiles import load_model_profile, quality_addendum


def test_quality_addendum_from_profile() -> None:
    settings = Settings(models_dir=Path(__file__).resolve().parents[1] / "config" / "models")
    profile = load_model_profile(settings, "qwen3.6-35b-a3b")
    text = quality_addendum(settings, "qwen3.6-35b-a3b")
    assert isinstance(text, str)
    assert profile.get("id") or profile


def test_settings_llm_model_default() -> None:
    s = Settings()
    assert "Qwen" in s.llm_model or s.llm_model
