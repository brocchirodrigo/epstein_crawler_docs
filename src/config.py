"""
Configuration module using Pydantic Settings.
Supports environment variables and .env files.
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

HTML_PARSER = "html.parser"
NO_RESULTS_TEXT = "No results found"

class ScraperSettings(BaseSettings):
    """Main configuration for the Epstein Files Scraper."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    base_url: str = Field(default="https://www.justice.gov")
    epstein_path: str = Field(default="/epstein")

    alphabet: str = Field(default="abcdefghijklmnopqrstuvwxyz")
    max_pages_per_letter: int | None = Field(default=None)
    max_downloads: int | None = Field(default=None)

    headless: bool = False
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)
    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    navigation_timeout: int = Field(default=60000)
    page_load_timeout: int = Field(default=30000)

    @property
    def epstein_page(self) -> str:
        return f"{self.base_url}{self.epstein_path}"

    @property
    def letters(self) -> list[str]:
        return list(self.alphabet)

    @property
    def viewport(self) -> dict:
        return {"width": self.viewport_width, "height": self.viewport_height}

    @property
    def browser_args(self) -> list[str]:
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
        ]
        if self.headless:
            args.append("--headless=new")
        return args


class PathSettings(BaseSettings):
    """Path configuration for project directories."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_root: Path = Field(default=Path(__file__).parent.parent)

    @property
    def src_dir(self) -> Path:
        return self.project_root / "src"

    @property
    def downloads_dir(self) -> Path:
        return self.project_root / "downloads"

    @property
    def logs_dir(self) -> Path:
        return self.project_root / "logs"

    @property
    def output_json(self) -> Path:
        return self.project_root / "epstein_urls.json"


settings = ScraperSettings()
paths = PathSettings()
