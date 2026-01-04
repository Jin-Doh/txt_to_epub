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

logger = setup_logger("converter.epub_fast_processor")

DEFAULT_CSS = """
@namespace epub "http://www.idpf.org/2007/ops";
body { font-family: "KoPub Batang", "Noto Serif KR", serif; line-height: 1.8; margin: 0.5em; padding: 0; word-break: keep-all; }
h1 { text-align: center; margin-top: 2em; margin-bottom: 2em; font-weight: bold; font-size: 1.5em; }
p { text-indent: 1em; margin-top: 0; margin-bottom: 0.8em; text-align: justify; }
hr.scene-break { border: 0; border-top: 1px solid #888; margin: 2em auto; width: 50%; }
/* 표지 스타일 */
div.cover-container { height: 100%; width: 100%; text-align: center; page-break-after: always; }
img.cover-image { max-height: 100%; max-width: 100%; object-fit: contain; }
"""


class EpubFastProcessor:
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
    ):
        txt_path = Path(txt_path)
        output_path = Path(output_path)
        logger.info("Processing: %s", txt_path.name)

        try:
            # 1. 파일 읽기
            async with aiofiles.open(txt_path, mode="rb") as f:
                raw_bytes = await f.read()

            raw_text = None
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
                raise ValueError("Encoding failed")

            # 2. Worker 파싱
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
                return

            chapters, metadata = result

            # 3. EPUB 조립
            book = epub.EpubBook()
            book.set_identifier(str(uuid.uuid4()))
            book.set_title(metadata.title)
            book.set_language("ko")

            css_item = epub.EpubItem(
                uid="style_nav",
                file_name="style/nav.css",
                media_type="text/css",
                content=DEFAULT_CSS,
            )
            book.add_item(css_item)

            # [표지 처리] 아이폰 호환성 강화
            cover_page_item = None
            if getattr(metadata, "cover_image_path", None):
                cover_path = Path(metadata.cover_image_path)
                if cover_path.exists():
                    cover_bytes = cover_path.read_bytes()
                    img_name = f"cover{cover_path.suffix}"
                    # A. 메타데이터 표지 (서재용) - 페이지 자동생성 끔
                    book.set_cover(img_name, cover_bytes, create_page=False)

                    # B. 본문 첫 페이지용 표지 (HTML 수동 생성)
                    cover_page_item = epub.EpubHtml(
                        title="Cover", file_name="cover_page.xhtml", lang="ko"
                    )
                    cover_page_item.content = f'<div class="cover-container"><img src="{img_name}" alt="Cover" class="cover-image"/></div>'
                    cover_page_item.add_item(css_item)
                    book.add_item(cover_page_item)

            for chapter in chapters:
                chapter.add_item(css_item)
                book.add_item(chapter)

            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # 스파인 설정 (표지 페이지가 있으면 맨 앞에 배치)
            book.spine = (
                ([cover_page_item] if cover_page_item else []) + ["nav"] + chapters
            )

            if cancel_event and cancel_event.is_set():
                return
            await loop.run_in_executor(
                self.executor, epub.write_epub, output_path, book, {}
            )
            logger.info("Saved: %s", output_path.name)

        except Exception:
            logger.exception("Failed: %s", txt_path.name)
            raise
