import asyncio
from pathlib import Path

import pytest

from src.core.converter.convert import EpubFastProcessor


@pytest.mark.asyncio
async def test_process_book_creates_epub(tmp_path: Path):
    # prepare input txt
    txt = tmp_path / "input.txt"
    txt.write_text("Title\n\nContent paragraph.", encoding="utf-8")

    output = tmp_path / "out.epub"

    # run processor
    with EpubFastProcessor(max_workers=2) as proc:
        await proc.process_book(str(txt), str(output))

    assert output.exists()
    assert output.stat().st_size > 0
