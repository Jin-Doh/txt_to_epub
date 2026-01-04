import asyncio
import pytest
import zipfile
from pathlib import Path
from src.core.converter.convert import EpubFastProcessor
from src.lib.types import BookMetadata


@pytest.mark.asyncio
async def test_epub_generation_full_features(tmp_path: Path):
    """
    CSS, 표지, 챕터 분할이 모두 포함된 EPUB 생성 테스트
    """
    # 1. 파일 준비
    txt_path = tmp_path / "integration.txt"
    txt_path.write_text(
        "#1. Chap One\nContent 1\n\n#2. Chap Two\nContent 2", encoding="utf-8"
    )

    cover_path = tmp_path / "cover.jpg"
    cover_path.write_bytes(b"fake_jpg_data")

    out_path = tmp_path / "final.epub"

    # 2. 메타데이터 수동 생성 (main.py가 parser에서 받아오는 역할 흉내)
    meta = BookMetadata(
        title="Integration Test", text_path=txt_path, cover_image_path=cover_path
    )

    # 3. 변환 실행
    with EpubFastProcessor(max_workers=2) as proc:
        await proc.process_book(
            txt_path, out_path, metadata_override=meta  # 수정된 인자 사용
        )

    # 4. 검증 (Zipfile로 EPUB 내부 까보기)
    assert out_path.exists()

    with zipfile.ZipFile(out_path) as z:
        file_list = z.namelist()

        # A. CSS 존재 여부
        assert "EPUB/style/nav.css" in file_list

        # B. 표지 페이지 존재 여부 (커버 이미지가 있었으므로 생성되어야 함)
        assert "EPUB/cover_page.xhtml" in file_list
        # 내부 이미지 파일 존재 여부 (이름은 cover.jpg 또는 유사하게 변환됨)
        assert any("cover" in f and f.endswith(".jpg") for f in file_list)

        # C. 챕터 분할 확인 (Intro 혹은 #1, #2 포함하여 최소 2개 이상)
        xhtmls = [f for f in file_list if f.endswith(".xhtml") and "chap_" in f]
        assert len(xhtmls) >= 2
