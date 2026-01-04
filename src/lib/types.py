from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BookMetadata:
    """Metadata for a book asset."""

    title: str
    text_path: Path
    cover_image_path: Optional[Path] = None
