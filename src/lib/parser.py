"""Utilities to parse book assets (text files + cover images)."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.lib.logger import setup_logger
from src.lib.types import BookMetadata

LOGGER = setup_logger("parser")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _collect_images(p: Path) -> List[Path]:
    """해당 경로의 모든 지원되는 이미지 파일을 수집합니다."""
    images = []
    for ext in IMAGE_EXTENSIONS:
        images.extend(p.glob(f"*{ext}"))
        images.extend(p.glob(f"*{ext.upper()}"))
    return sorted(list(set(images)))


def _find_cover_image(target_stem: str, image_files: List[Path]) -> Optional[Path]:
    """
    이미지 파일 목록 중에서 표지를 결정합니다.
    1. 파일명 일치 (Book.jpg)
    2. 'cover' 파일 (cover.jpg)
    3. 폴더 내 유일한 이미지
    """
    if not image_files:
        return None
    # 1. 파일명 일치
    matches = [img for img in image_files if img.stem == target_stem]
    if matches:
        return matches[0]
    # 2. cover.jpg
    covers = [img for img in image_files if img.stem.lower() == "cover"]
    if covers:
        return covers[0]
    # 3. 유일한 이미지
    if len(image_files) == 1:
        return image_files[0]
    return None


def _process_file_sync(file_path: Path, root: Path) -> List[Tuple[Path, BookMetadata]]:
    """단일 텍스트 파일을 처리하며 같은 폴더의 형제 이미지를 표지로 탐색합니다."""
    txt = file_path
    title = txt.stem
    cover: Optional[Path] = None

    # 1. 같은 폴더(root)에 있는 형제 이미지 파일 검색
    sibling_images = []
    for ext in IMAGE_EXTENSIONS:
        target = txt.with_suffix(ext)
        if target.exists():
            sibling_images.append(target)
        cover_target = root / f"cover{ext}"
        if cover_target.exists():
            sibling_images.append(cover_target)

    sibling_images = sorted(list(set(sibling_images)))
    if sibling_images:
        cover = _find_cover_image(txt.stem, sibling_images)

    # 2. 하위 폴더 검색 (기존 로직)
    if not cover:
        sibling_dir = root / txt.stem
        if sibling_dir.exists() and sibling_dir.is_dir():
            jpgs = _collect_images(sibling_dir)
            if jpgs:
                cover = _find_cover_image(txt.stem, jpgs) or jpgs[0]

    return [(txt, BookMetadata(title=title, text_path=txt, cover_image_path=cover))]


def _process_dir_sync(dir_path: Path) -> List[Tuple[Path, BookMetadata]]:
    out: List[Tuple[Path, BookMetadata]] = []
    try:
        all_files = list(dir_path.iterdir())
    except FileNotFoundError:
        return []
    txt_files = [f for f in all_files if f.suffix.lower() == ".txt"]
    img_files = _collect_images(dir_path)
    for txt in txt_files:
        cover = _find_cover_image(txt.stem, img_files)
        out.append(
            (
                txt,
                BookMetadata(
                    title=dir_path.name, text_path=txt, cover_image_path=cover
                ),
            )
        )
    return out


async def _process_entry(
    entry: Path, asset_path: Path
) -> List[Tuple[Path, BookMetadata]]:
    if await asyncio.to_thread(entry.is_dir):
        return await asyncio.to_thread(_process_dir_sync, entry)
    if await asyncio.to_thread(
        lambda: entry.is_file() and entry.suffix.lower() == ".txt"
    ):
        return await asyncio.to_thread(_process_file_sync, entry, asset_path)
    return []


async def parse_books(asset_dir: Path | str) -> Dict[Path, BookMetadata]:
    asset_path = Path(asset_dir)
    if not await asyncio.to_thread(asset_path.exists):
        LOGGER.error("Directory not found: %s", asset_path)
        return {}
    results: Dict[Path, BookMetadata] = {}
    entries = await asyncio.to_thread(lambda: list(asset_path.iterdir()))
    tasks = [asyncio.create_task(_process_entry(e, asset_path)) for e in entries]
    results_lists = await asyncio.gather(*tasks)
    for lst in results_lists:
        for txt, _meta in lst:
            results[txt] = _meta
    return results


__all__ = ["parse_books", "BookMetadata"]

if __name__ == "__main__":
    # Test execution
    _root_dir = Path(__file__).parents[2] / "assets"
    if not _root_dir.exists():
        _root_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Parsing books in directory: %s", _root_dir)
    books = asyncio.run(parse_books(_root_dir))
    for txt_path, meta in books.items():
        LOGGER.info(
            "Found book: %s (%s)",
            txt_path,
            meta,
        )
    LOGGER.info("Parsing completed.")
