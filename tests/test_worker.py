from pathlib import Path
import pytest
from ebooklib import epub
from src.core.converter.worker import cpu_bound_text_parsing


def test_cpu_bound_text_parsing_basic_structure(tmp_path: Path):
    """기본적인 텍스트 파싱 및 객체 반환 구조 테스트"""
    sample = "Introduction line.\n\nBody content."
    filename = "test_book.txt"

    # 변경된 로직: chapters는 리스트여야 함
    chapters, metadata = cpu_bound_text_parsing(sample, filename)

    # 1. 반환 타입 검증
    assert isinstance(chapters, list)
    assert len(chapters) > 0
    assert isinstance(chapters[0], epub.EpubHtml)

    # 2. 메타데이터 검증
    assert metadata.title == "test_book"
    assert metadata.text_path.name == filename


def test_chapter_splitting_logic():
    """챕터 자동 분할 정규식 동작 테스트"""
    # 챕터 구분자가 포함된 텍스트
    raw_text = (
        "프롤로그 내용입니다.\n\n"
        "#1. 첫 번째 이야기\n"
        "내용 1입니다.\n\n"
        "제2장 두 번째 이야기\n"
        "내용 2입니다."
    )

    chapters, _ = cpu_bound_text_parsing(raw_text, "split_test.txt")

    # 예상: Intro(프롤로그), #1, 제2장 -> 총 3개 챕터
    assert len(chapters) == 3

    # 챕터 제목 및 내용 검증
    assert chapters[0].title == "Intro"
    assert "프롤로그" in chapters[0].content

    assert chapters[1].title == "#1. 첫 번째 이야기"
    assert "내용 1입니다" in chapters[1].content

    assert "제2장" in chapters[2].title


def test_filename_cleaning():
    """파일명에서 불필요한 태그 제거 테스트"""
    dirty_name = "[9월-도서] 정말 재미있는 소설 001-500 完@국뽕.txt"

    _, metadata = cpu_bound_text_parsing("내용", dirty_name)

    # 정제된 제목 확인
    assert metadata.title == "정말 재미있는 소설"
    # [9월-도서], 001-500, 完, @국뽕 등이 제거되어야 함
