import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import aiofiles
from aiogram.types import Document

from config import Config


class FileManager:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.temp_files: dict[str, Path] = {}

    async def save_document(self, document: Document, file_content: bytes) -> tuple[str, Path]:
        file_id = str(uuid.uuid4())
        file_extension = Path(document.file_name or "file.xlsx").suffix
        file_path = self.config.temp_dir / f"{file_id}{file_extension}"

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        self.temp_files[file_id] = file_path
        return file_id, file_path

    async def create_output_file(self, input_file_id: str) -> tuple[str, Path]:
        moscow_tz = ZoneInfo("Europe/Moscow")
        output_file_id = datetime.now(moscow_tz).strftime("kkt-result-%d-%m-%Y-%H-%M-%S")
        input_path = self.temp_files.get(input_file_id)

        if not input_path:
            raise ValueError("Input file not found")

        output_path = self.config.temp_dir / f"{output_file_id}{input_path.suffix}"
        self.temp_files[output_file_id] = output_path
        return output_file_id, output_path

    def get_file_path(self, file_id: str) -> Path | None:
        return self.temp_files.get(file_id)

    async def cleanup_file(self, file_id: str) -> None:
        file_path = self.temp_files.pop(file_id, None)
        if file_path and file_path.exists():
            file_path.unlink()

    async def cleanup_all_files(self) -> None:
        for file_id in list(self.temp_files.keys()):
            await self.cleanup_file(file_id)


def validate_excel_file(document: Document, config: Config) -> bool:
    if not document.file_name:
        return False

    # Check file extension
    if not document.file_name.lower().endswith((".xlsx", ".xls")):
        return False

    # Check file size
    if document.file_size and document.file_size > config.max_file_size_mb * 1024 * 1024:
        return False

    return True


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
