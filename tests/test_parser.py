import pytest
from pathlib import Path
from src.lib.parser import parse_books, BookMetadata


@pytest.mark.asyncio
async def test_parser_cover_priority(tmp_path: Path):
    """
    표지 이미지 탐색 우선순위 테스트
    1순위: 파일명 일치 (Book.jpg)
    2순위: cover.jpg
    """
    assets = tmp_path / "assets"
    assets.mkdir()

    # Case 1: 파일명 일치 이미지가 있는 경우 (Highest Priority)
    case1_dir = assets / "case1"
    case1_dir.mkdir()
    (case1_dir / "story.txt").write_text("content")
    (case1_dir / "story.jpg").write_bytes(b"ExactMatch")
    (case1_dir / "cover.jpg").write_bytes(b"CoverFile")  # 이건 무시돼야 함

    # Case 2: 파일명 일치는 없고 cover.jpg만 있는 경우
    case2_dir = assets / "case2"
    case2_dir.mkdir()
    (case2_dir / "novel.txt").write_text("content")
    (case2_dir / "cover.png").write_bytes(b"CoverPNG")

    results = await parse_books(assets)

    # 결과 검증
    # Case 1 검증
    txt1 = case1_dir / "story.txt"
    assert txt1 in results
    meta1 = results[txt1]
    assert meta1.cover_image_path.name == "story.jpg"  # cover.jpg보다 우선

    # Case 2 검증
    txt2 = case2_dir / "novel.txt"
    assert txt2 in results
    meta2 = results[txt2]
    assert meta2.cover_image_path.name == "cover.png"
