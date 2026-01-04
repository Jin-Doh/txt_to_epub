import argparse
import asyncio
import os
import threading
import re
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from src.lib.logger import setup_logger
from src.lib.parser import parse_books
from src.core.converter.convert import EpubFastProcessor

LOGGER = setup_logger("main")


async def _run_conversion(
    asset_dir: Path,
    output_dir: Path,
    max_workers: int,
    concurrency: Optional[int] = None,
    dry_run: bool = False,
    shutdown_timeout: Optional[float] = None,
    overwrite: bool = False,
):
    books = await parse_books(asset_dir)
    if not books:
        LOGGER.info("No books found in %s", asset_dir)
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    if concurrency is None:
        concurrency = max_workers or (os.cpu_count() or 4)

    semaphore = asyncio.Semaphore(concurrency)

    async with EpubFastProcessor(
        max_workers=max_workers, shutdown_timeout=shutdown_timeout
    ) as processor:

        async def _worker(
            txt_path: Path, out_path: Path, cancel_event: threading.Event
        ):
            # [Fast Fail] 대기열 진입 전 취소 확인
            if cancel_event.is_set():
                return

            async with semaphore:
                # 세마포어 획득 후 다시 확인
                if cancel_event.is_set():
                    return
                try:
                    await processor.process_book(
                        txt_path, out_path, cancel_event=cancel_event
                    )
                except Exception:
                    LOGGER.exception("Error converting %s", txt_path.name)
                finally:
                    pbar.update(1)

        tasks = []
        cancel_events: list[threading.Event] = []

        # 진행률 표시줄 미리 생성 (Total 계산)
        total_tasks = 0

        for txt_path, meta in books.items():
            # 출력 파일명 정제 (제목과 유사하게 깔끔하게)
            # 메타데이터의 제목이 있으면 우선 사용, 없으면 파일명 사용
            raw_name = meta.title if meta.title else txt_path.stem
            # 불필요한 태그 제거 (worker의 로직과 유사하게 적용)
            clean_name = re.sub(r"\[.*?\]|\d+[-~]\d+|@.*|텍본", "", raw_name).strip()
            # 파일시스템 안전 문자열로 변환
            safe_name = "".join(
                c if c.isalnum() or c in " -_" else "" for c in clean_name
            ).strip()
            if not safe_name:
                safe_name = "Untitled_Book"  # 비어버린 경우 대비

            out_path = output_dir / f"{safe_name}.epub"

            if dry_run:
                LOGGER.info("[dry-run] %s -> %s", txt_path.name, out_path.name)
                continue

            if out_path.exists() and not overwrite:
                LOGGER.info("Skipping existing: %s", out_path.name)
                continue

            cancel_event = threading.Event()
            cancel_events.append(cancel_event)
            tasks.append(asyncio.create_task(_worker(txt_path, out_path, cancel_event)))
            total_tasks += 1

        if not tasks:
            LOGGER.info("No conversion tasks to perform.")
            return

        pbar = tqdm(total=total_tasks, desc="Converting", unit="book")

        try:
            if shutdown_timeout is None:
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=shutdown_timeout,
                    )
                except asyncio.TimeoutError:
                    LOGGER.warning("Global timeout reached. Cancelling tasks...")
                    for ev in cancel_events:
                        ev.set()
                    for t in tasks:
                        t.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)

        except KeyboardInterrupt:
            LOGGER.warning("Interrupted by user. Stopping...")
            for ev in cancel_events:
                ev.set()
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            pbar.close()


async def main(
    asset: str | Path,
    out: str | Path,
    workers: Optional[int] = None,
    concurrency: Optional[int] = None,
    dry_run: bool = False,
    shutdown_timeout: Optional[float] = None,
    overwrite: bool = False,
):
    asset_dir = Path(asset)
    output_dir = Path(out)
    workers = workers or (os.cpu_count() or 4)

    LOGGER.info(f"Target: {asset_dir} -> {output_dir}")
    LOGGER.info(f"Config: workers={workers}, concurrency={concurrency or 'auto'}")

    await _run_conversion(
        asset_dir,
        output_dir,
        workers,
        concurrency,
        dry_run,
        shutdown_timeout,
        overwrite,
    )


def _cli():
    p = argparse.ArgumentParser(description="High-Performance Text to EPUB Converter")
    p.add_argument("--assets", "-a", default="assets", help="Input directory")
    p.add_argument("--out", "-o", default="out", help="Output directory")
    p.add_argument("--workers", "-w", type=int, help="Thread pool size")
    p.add_argument("--concurrency", "-c", type=int, help="Max concurrent tasks")
    p.add_argument("--dry-run", "-n", action="store_true", help="Dry run mode")
    p.add_argument("--shutdown-timeout", "-t", type=float, help="Timeout in seconds")
    p.add_argument(
        "--overwrite", "-f", action="store_true", help="Overwrite existing files"
    )

    args = p.parse_args()
    asyncio.run(
        main(
            args.assets,
            args.out,
            args.workers,
            args.concurrency,
            args.dry_run,
            args.shutdown_timeout,
            args.overwrite,
        )
    )


if __name__ == "__main__":
    _cli()
