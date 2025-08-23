import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    temp_dir: Path = Path("temp")
    max_file_size_mb: int = 10
    max_concurrent_checks: int = 3
    api_delay_seconds: float = 0.5
    max_retries: int = 5
    retry_delay_seconds: int = 15

    def __post_init__(self) -> None:
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")

        # Create temp directory if it doesn't exist
        self.temp_dir.mkdir(exist_ok=True)


def get_config() -> Config:
    return Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        temp_dir=Path(os.getenv("TEMP_DIR", "temp")),
        max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "10")),
        max_concurrent_checks=int(os.getenv("MAX_CONCURRENT_CHECKS", "5")),
        api_delay_seconds=float(os.getenv("API_DELAY_SECONDS", "0.5")),
        max_retries=int(os.getenv("MAX_RETRIES", "5")),
        retry_delay_seconds=int(os.getenv("RETRY_DELAY_SECONDS", "10")),
    )
