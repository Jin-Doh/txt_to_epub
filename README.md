
txt-to-epub — 로컬 텍스트 파일을 고속으로 EPUB으로 변환하는 도구

간단 설명
---------------

`txt-to-epub`는 로컬에 보관된 텍스트(.txt) 파일과 동봉된 표지 이미지를 분석하여 EPUB 파일로 변환하는 고성능 파이썬 도구입니다. 대량 변환을 염두에 둔 비동기/스레드 결합 처리로 빠른 처리 속도를 제공합니다.

주요 기능
----------

- 자동으로 텍스트 폴더와 형제 이미지에서 표지 이미지를 탐색합니다.
- 챕터 헤더(예: "1화", "제1장", "Chapter 1")를 감지해 챕터별로 EPUB을 생성합니다.
- 멀티스레드·비동기 조합으로 병렬 변환을 수행합니다.
- 드라이런, 덮어쓰기, 작업 제한(동시성/워커 수), 전역 타임아웃 등을 지원합니다.

설치
-----

다음 예시는 Bash(Windows의 `bash.exe` 포함)를 기준으로 한 빠른 설정 방법입니다.

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install --upgrade pip
pip install aiofiles ebooklib tqdm pytest pytest-asyncio
```

또는 현재 디렉터리의 `pyproject.toml`에 정의된 의존성을 이용해 설치하려면:

```bash
pip install -e .
```

사용법 (`uv` 기준)
-------------------

이 저장소에서는 로컬에서 명령을 실행할 때 `uv` 유틸리티를 이용해 파이썬 모듈을 실행하는 사례가 있습니다. `uv`는 임의의 실행 래퍼로 사용되는 예시 커맨드입니다. 아래 예시는 `uv run <command>` 형식으로 실행할 수 있습니다.

- 텍스트 자산 파싱(검사용):

```bash
uv run python -m src.lib.parser
```

- 전체 변환 (예: `assets` 폴더를 `out` 폴더로 변환):

```bash
uv run python -m src.main --assets assets --out out --workers 4
```

- 드라이런(실제 파일 생성 없이 흐름만 검증):

```bash
uv run python -m src.main --assets assets --out out --dry-run
```

- 기존 출력을 강제로 덮어쓰기:

```bash
uv run python -m src.main --assets assets --out out --overwrite
```

명령행 옵션 요약 (주요 옵션)

- `--assets`, `-a`: 입력 자산 디렉터리 (기본: `assets`)
- `--out`, `-o`: 출력 디렉터리 (기본: `out`)
- `--workers`, `-w`: 워커(스레드) 수
- `--concurrency`, `-c`: 동시 실행 제한
- `--dry-run`, `-n`: 드라이런 모드
- `--shutdown-timeout`, `-t`: 전체 작업에 대한 타임아웃(초)
- `--overwrite`, `-f`: 기존 출력 파일 덮어쓰기

테스트
-----

로컬에서 유닛/통합 테스트를 실행하려면:

```bash
uv run python -m pytest tests/ -q
```

코드 구조(간단)
----------------

- `src/main.py`: 전체 변환 파이프라인의 엔트리 포인트. 명령행 인자 처리 및 변환 루프를 담당합니다.
- `src/lib/parser.py`: 자산(텍스트 및 표지 이미지) 분석 및 메타데이터 추출 유틸리티.
- `src/core/converter/`: 텍스트를 EPUB으로 변환하는 핵심 로직(텍스트 파싱, 챕터 분할, Epub 생성 등).
- `tests/`: 유닛 및 통합 테스트

기여
-----

기여는 환영합니다. 간단한 방식:

1. 포크(fork) 및 feature 브랜치 생성
2. 변경 사항 커밋
3. 테스트(`pytest`) 통과 확인
4. PR 보내기

라이선스
--------

이 저장소는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 루트의 `LICENSE` 파일을 참고하세요.

저작권 및 연도 정보를 `LICENSE` 파일에서 직접 수정하세요.
