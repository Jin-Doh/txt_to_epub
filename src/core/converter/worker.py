import uuid
import threading
import re
from typing import Union, Optional, Tuple, List, Dict
from pathlib import Path

from ebooklib import epub

from src.lib.logger import setup_logger
from src.lib.types import BookMetadata


# 예외 클래스는 모듈 레벨에 정의
class OperationCancelled(Exception):
    """Raised when a CPU-bound operation is cancelled via a threading.Event."""

    pass


def clean_book_title(filename_stem: str) -> str:
    """파일명에서 불필요한 수식어를 제거하여 깔끔한 책 제목을 추출합니다."""
    # 1. 대괄호 및 내용 제거 ([9월-도서] 등)
    title = re.sub(r"\[.*?\]", "", filename_stem)
    # 2. 숫자 범위 제거 (0-1230, 001-444 등)
    title = re.sub(r"\d+[-~]\d+", "", title)
    # 3. 기타 잡다한 태그 제거 (完, @..., 텍본 등)
    title = re.sub(r"(完|@.*|텍본)", "", title)
    # 4. 다중 공백 정리
    return re.sub(r"\s+", " ", title).strip()


def split_chapters(raw_text: str) -> List[Dict[str, str]]:
    """텍스트에서 챕터 헤더를 감지하여 내용을 분할합니다."""
    # 챕터 감지 패턴: #1., 1화, 제1장, Chapter 1
    chapter_pattern = re.compile(
        r"(?:^|\n)\s*(?:"
        r"(?:#\s*\d+\.?)|"  # #1, #1.
        r"(?:<?\s*\d+\s*화\s*>?)|"  # 1화, < 1화 >
        r"(?:제\s*\d+\s*[장편])|"  # 제1장
        r"(?:Chapter\s*\d+)"  # Chapter 1
        r").*?(?=\n)",
        re.IGNORECASE,
    )

    chapters = []
    last_pos = 0

    # 정규식으로 헤더 위치 찾기
    for match in chapter_pattern.finditer(raw_text):
        # 헤더가 나오기 전까지의 내용은 이전 챕터(혹은 서문)의 내용
        if last_pos < match.start():
            content = raw_text[last_pos : match.start()].strip()
            if content:
                if not chapters:
                    # 첫 챕터 전의 내용은 Intro/Prologue로 처리
                    chapters.append({"title": "Intro", "content": content})
                else:
                    chapters[-1]["content"] = content

        # 새 챕터 시작
        title_line = match.group().strip()
        # 제목 정제: "< 1화 >" -> "1화"
        clean_title = re.sub(r"[<>]", "", title_line).strip()

        chapters.append(
            {"title": clean_title, "content": ""}  # 다음 루프(혹은 종료 후)에서 채워짐
        )
        last_pos = match.end()

    # 마지막 챕터 내용 처리
    if last_pos < len(raw_text):
        content = raw_text[last_pos:].strip()
        if chapters:
            chapters[-1]["content"] = content
        else:
            # 패턴을 하나도 못 찾은 경우 (통파일)
            chapters.append({"title": "본문", "content": content})

    return chapters


def cpu_bound_text_parsing(
    raw_text: str,
    filename: Union[Path, str],
    cancel_event: Optional[threading.Event] = None,
) -> Tuple[List[epub.EpubHtml], BookMetadata]:
    """
    텍스트를 파싱하여 챕터 리스트(List[EpubHtml])와 메타데이터를 생성합니다.
    """
    logger = setup_logger("converter.worker")
    fname_stem = Path(filename).stem

    # 1. 제목 정제
    book_title = clean_book_title(fname_stem)
    logger.debug("Parsing '%s' (detected title: '%s')", fname_stem, book_title)

    # 2. 챕터 분할
    split_data = split_chapters(raw_text)
    logger.debug("Detected %d chapters for %s", len(split_data), filename)

    epub_chapters = []

    # 3. 각 챕터를 HTML로 변환
    for idx, data in enumerate(split_data):
        # 주기적인 취소 확인
        if cancel_event is not None and cancel_event.is_set():
            logger.info("Parsing cancelled for %s", filename)
            raise OperationCancelled(f"Operation cancelled for {filename}")

        body_parts = []
        for p in data["content"].split("\n\n"):
            clean_p = p.strip()
            if not clean_p:
                continue

            # 구분선(===, ---, ***)은 장면 전환으로 간주해 <hr/>로 변환
            # (줄이 =, -, * 및 공백으로만 구성되어 있는 경우)
            if set(clean_p) <= {"=", "-", "*", " "}:
                body_parts.append('<hr class="scene-break"/>')
            else:
                body_parts.append(f"<p>{clean_p.replace('\n', '<br/>')}</p>\n")

        # HTML 객체 생성
        chapter = epub.EpubHtml(
            title=data["title"],
            file_name=f"chap_{idx:04d}.xhtml",  # 정렬을 위해 0001, 0002...
            lang="ko",
            direction="ltr",
        )
        chapter.content = f"<h1>{data['title']}</h1>{''.join(body_parts)}"
        epub_chapters.append(chapter)

    # 4. 메타데이터 생성 (정제된 제목 사용)
    metadata = BookMetadata(title=book_title, text_path=Path(filename))

    return epub_chapters, metadata
