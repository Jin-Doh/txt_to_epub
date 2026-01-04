from pathlib import Path

import pytest

from src.core.converter.worker import cpu_bound_text_parsing


def test_cpu_bound_text_parsing_basic(tmp_path: Path):
    sample = "Paragraph one.\n\nParagraph two."
    chapter, metadata = cpu_bound_text_parsing(sample, "sample.txt")
    # Ensure returned object has expected attributes
    assert hasattr(chapter, "title")
    assert hasattr(chapter, "content")
    assert "Paragraph one." in chapter.content
    assert "Paragraph two." in chapter.content
    assert chapter.title == "sample"
    # Ensure metadata was returned and is correct
    assert metadata.title == "sample"
    assert metadata.text_path.name == "sample.txt"
