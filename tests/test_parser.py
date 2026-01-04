import asyncio
from pathlib import Path

import pytest

from src.lib.parser import parse_books, BookMetadata


@pytest.mark.asyncio
async def test_parse_books_directory_and_root(tmp_path: Path):
    # Create asset structure
    assets = tmp_path / "assets"
    assets.mkdir()

    # Subdir with txt + jpg
    sub = assets / "bookdir"
    sub.mkdir()
    txt1 = sub / "book.txt"
    txt1.write_text("Chapter 1\n\nChapter 2", encoding="utf-8")
    cover = sub / "cover.jpg"
    cover.write_bytes(b"JPEGDATA")

    # Root standalone txt and sibling dir with image
    solo = assets / "solo.txt"
    solo.write_text("Solo content", encoding="utf-8")
    sibling = assets / "solo"
    sibling.mkdir()
    sibling_cover = sibling / "cover.jpg"
    sibling_cover.write_bytes(b"JPEGDATA")

    results = await parse_books(assets)

    # Expect both txt files discovered
    keys = {p.name for p in results.keys()}
    assert "book.txt" in keys
    assert "solo.txt" in keys

    meta_book: BookMetadata = results[txt1]
    assert meta_book.title == "bookdir"
    assert meta_book.cover_image_path is not None
    assert meta_book.cover_image_path.name == "cover.jpg"

    meta_solo: BookMetadata = results[solo]
    assert meta_solo.title == "solo"
    assert meta_solo.cover_image_path is not None
    assert meta_solo.cover_image_path.name == "cover.jpg"
