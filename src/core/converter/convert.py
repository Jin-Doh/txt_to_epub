import asyncio
import os
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import aiofiles
from ebooklib import epub

from .worker import cpu_bound_text_parsing, OperationCancelled
from src.lib.logger import setup_logger

# 타입 힌트를 위해 필요 (실행 시 순환 참조 방지를 위해 TYPE_CHECKING 사용 가능하나 여기선 간단히 import)
from src.lib.types import BookMetadata

logger = setup_logger("converter.epub_fast_processor")

DEFAULT_CSS = """
@namespace epub "http://www.idpf.org/2007/ops";
body {
    font-family: "KoPub Batang", "Noto Serif KR", serif;
    line-height: 1.8;
    margin: 0.5em;
    padding: 0;
    word-break: keep-all;
}
h1 {
    text-align: center;
    margin-top: 2em;
    margin-bottom: 2em;
    font-weight: bold;
    font-size: 1.5em;
}
p {
    text-indent: 1em;
    margin-top: 0;
    margin-bottom: 0.8em;
    text-align: justify;
}
hr.scene-break {
    border: 0;
    border-top: 1px solid #888;
    margin: 2em auto;
    width: 50%;
}
/* 표지 스타일 */
div.cover-container {
    height: 100%;
    width: 100%;
    text-align: center;
    page-break-after: always;
}
img.cover-image {
    max-height: 100%;
    max-width: 100%;
    object-fit: contain;
}
"""


class EpubFastProcessor:
    """
    A fast EPUB processor using ThreadPoolExecutor (Python 3.14 No-GIL optimized).
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        shutdown_timeout: Optional[float] = None,
    ):
        self.max_workers = max_workers or (os.cpu_count() or 4)
        self.executor = None
        self.shutdown_timeout = shutdown_timeout

    def __enter__(self):
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        logger.debug("ThreadPoolExecutor started (max_workers=%s)", self.max_workers)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.executor:
            if self.shutdown_timeout is None:
                self.executor.shutdown(wait=True)
            else:

                def _shutdown_wait():
                    try:
                        self.executor.shutdown(wait=True)
                    except:
                        pass

                t = threading.Thread(target=_shutdown_wait)
                t.start()
                t.join(self.shutdown_timeout)
                if t.is_alive():
                    try:
                        self.executor.shutdown(wait=False)
                    except:
                        pass
        return False

    async def __aenter__(self):
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.executor:
            if self.shutdown_timeout is None:
                await asyncio.to_thread(self.executor.shutdown, True)
            else:
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(self.executor.shutdown, True),
                        timeout=self.shutdown_timeout,
                    )
                except asyncio.TimeoutError:
                    try:
                        await asyncio.to_thread(self.executor.shutdown, False)
                    except:
                        pass
        return False

    async def process_book(
        self,
        txt_path: Path,
        output_path: Path,
        cancel_event: threading.Event | None = None,
        metadata_override: Optional[BookMetadata] = None,  # 외부에서 전달된 메타데이터(예: 표지 경로)
    ):
        txt_path = Path(txt_path)
        output_path = Path(output_path)
        logger.info("Start processing: %s", txt_path.name)

        try:
            # 1. 파일 읽기 & 인코딩 감지
            async with aiofiles.open(txt_path, mode="rb") as f:
                raw_bytes = await f.read()

            raw_text = None
            # 인코딩 탐지 순서: BOM 우선 -> UTF-8 -> 한국어(cp949, euc-kr) -> 서유럽(latin-1)
            for enc, bom in [
                ("utf-8-sig", b"\xef\xbb\xbf"),
                ("utf-16", b"\xff\xfe"),
                ("utf-8", None),
                ("cp949", None),
                ("euc-kr", None),
                ("latin-1", None),
            ]:
                if bom and raw_bytes.startswith(bom):
                    try:
                        raw_text = raw_bytes.decode(enc)
                        break
                    except:
                        continue
                elif not bom:
                    try:
                        raw_text = raw_bytes.decode(enc)
                        break
                    except:
                        continue

            if not raw_text:
                raise ValueError("Failed to detect encoding")

            # 2. Worker 파싱 (CPU Bound)
            loop = asyncio.get_running_loop()
            try:
                result = await loop.run_in_executor(
                    self.executor,
                    cpu_bound_text_parsing,
                    raw_text,
                    txt_path,
                    cancel_event,
                )
            except OperationCancelled:
                logger.info("Parsing cancelled: %s", txt_path.name)
                return

            chapters, worker_metadata = result

            # 메타데이터 병합: Worker가 생성한 제목을 기본으로 사용하되,
            # 필요하면 외부에서 전달된 메타데이터(예: 표지 경로)를 반영
            final_metadata = worker_metadata
            if metadata_override:
                # 표지 경로가 있으면 덮어쓰기
                if metadata_override.cover_image_path:
                    final_metadata.cover_image_path = metadata_override.cover_image_path
                # 필요하다면 제목도 override 가능 (현재는 Worker의 정제된 제목 선호)

            # 3. EPUB 조립
            book = epub.EpubBook()
            book.set_identifier(str(uuid.uuid4()))
            book.set_title(final_metadata.title)
            book.set_language("ko")

            # 스타일시트 추가
            css_item = epub.EpubItem(
                uid="style_nav",
                file_name="style/nav.css",
                media_type="text/css",
                content=DEFAULT_CSS,
            )
            book.add_item(css_item)

            # 표지 처리: 표지 이미지를 EPUB에 추가하고, 본문에 삽입할 표지 페이지 HTML을 생성
            cover_page_item = None
            try:
                if getattr(final_metadata, "cover_image_path", None):
                    cover_path = Path(final_metadata.cover_image_path)
                    if cover_path.exists():
                        cover_bytes = cover_path.read_bytes()
                        internal_img_name = (
                            f"cover{cover_path.suffix}"  # e.g., cover.jpg
                        )

                        # A. 서재 썸네일용 (자동 페이지 생성 끔)
                        book.set_cover(
                            internal_img_name, cover_bytes, create_page=False
                        )

                        # B. 본문 첫 페이지용 (HTML 직접 생성)
                        cover_page_item = epub.EpubHtml(
                            title="Cover", file_name="cover_page.xhtml", lang="ko"
                        )
                        cover_page_item.content = (
                            f'<div class="cover-container">'
                            f'<img src="{internal_img_name}" alt="Cover" class="cover-image"/>'
                            f"</div>"
                        )
                        cover_page_item.add_item(css_item)
                        book.add_item(cover_page_item)

                        logger.debug("Attached cover: %s", cover_path.name)
            except Exception:
                logger.warning("Failed to attach cover for %s", txt_path.name)

            # 챕터 추가
            for chapter in chapters:
                chapter.add_item(css_item)
                book.add_item(chapter)

            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # 스파인 설정: 표지 페이지가 있으면 맨 앞에 배치
            spine_list = ["nav"] + chapters
            if cover_page_item:
                spine_list.insert(0, cover_page_item)
            book.spine = spine_list

            # 4. 파일 저장
            if cancel_event and cancel_event.is_set():
                return
            await loop.run_in_executor(
                self.executor, epub.write_epub, output_path, book, {}
            )
            logger.info(
                "Saved EPUB: %s (Chapters: %d)", output_path.name, len(chapters)
            )

        except Exception:
            logger.exception("Failed to process book: %s", txt_path.name)
            raise
