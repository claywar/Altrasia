from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ALTRASIA_", env_file=".env", extra="ignore")

    data_dir: Path = Path.home() / ".altrasia"
    db_path: Path | None = None
    api_token: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "Qwen3.6-35B-A3B"
    mock_llm: bool = True
    web_tools_mock: bool = True
    web_allowlist: str = "example.com,www.example.org"
    embed_base_url: str | None = None
    embed_model: str = "text-embedding-3-small"
    comfy_url: str | None = None
    scheduler_enabled: bool = False
    gpu_max_depth: int = 4
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    fixtures_dir: Path = _REPO_ROOT / "tests" / "fixtures"
    models_dir: Path = _REPO_ROOT / "config" / "models"

    def web_allowlist_set(self) -> set[str]:
        return {h.strip().lower() for h in self.web_allowlist.split(",") if h.strip()}

    @property
    def sqlite_path(self) -> Path:
        if self.db_path:
            return self.db_path
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "operator.db"


def get_settings() -> Settings:
    return Settings()
