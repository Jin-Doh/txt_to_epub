# 📚 High-Performance TXT to EPUB Converter

> **Python 3.14 (Free-Threading) Ready** > 대용량 텍스트 파일(웹소설 등)을 고품질 EPUB 전자책으로 초고속 변환하는 도구입니다.

![Python Version](https://img.shields.io/badge/python-3.14%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-stable-brightgreen)

## ✨ 주요 기능 (Key Features)

이 프로젝트는 단순한 텍스트 변환을 넘어, 전자책 리더기에서의 **가독성**과 **호환성**에 최적화되어 있습니다.

- **🚀 압도적인 성능 (High Performance)**
  - **AsyncIO** (비동기 I/O)와 **Multi-threading**을 결합하여 수백 권의 책도 순식간에 변환합니다.
  - Python 3.14의 **No-GIL(Free-Threading)** 환경에서 CPU 코어를 100% 활용하도록 설계되었습니다.

- **📖 스마트 챕터 분할 (Smart Chapter Splitting)**
  - 통파일(예: `0-1230화.txt`)을 분석하여 챕터(`1화`, `#1`, `Chapter 1`) 단위로 자동 분할합니다.
  - 리더기에서 목차(TOC) 기능이 완벽하게 작동하여 쾌적한 탐색이 가능합니다.

- **🎨 표지 이미지 자동 감지 & Apple Books 호환**
  - 텍스트 파일과 같은 이름의 이미지(`Book.jpg`)나 폴더 내 `cover.jpg`를 자동으로 찾아 표지로 설정합니다.
  - **아이폰/아이패드 최적화**: 서재 썸네일뿐만 아니라, 책을 펼쳤을 때 첫 페이지에도 표지가 나오도록 강제 페이지를 생성합니다.

- **💅 고품질 타이포그래피 (Styling)**
  - 가독성을 위한 기본 CSS(`KoPub Batang` 기반)가 내장되어 있습니다.
  - `===`, `* * *` 같은 텍스트 구분선을 깔끔한 `<hr>` 태그로 자동 변환합니다.

- **🌍 강력한 인코딩 감지**
  - UTF-8, UTF-8-SIG, CP949(EUC-KR), Latin-1 등을 순차적으로 감지하여 글자 깨짐(Mojibake)을 방지합니다.

---

## 🛠️ 설치 방법 (Installation)

이 프로젝트는 [uv](https://github.com/astral-sh/uv) 패키지 매니저를 권장합니다. (일반 `pip`도 사용 가능)

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/txt-to-epub.git
cd txt-to-epub
```

### 2. 의존성 설치

**방법 A: `uv` 사용 (권장)**
```bash
# 가상환경 생성 및 패키지 동기화
uv sync
```

**방법 B: `pip` 사용**
```bash
pip install -r requirements.txt
# 또는 직접 설치
pip install ebooklib aiofiles tqdm
```

---

## 🚀 사용 방법 (Usage)

변환할 텍스트 파일과 표지 이미지를 `assets` 폴더에 넣고 실행하면 됩니다.

### 기본 실행
```bash
# uv 사용 시
uv run python -m src.main

# 일반 python 사용 시
python -m src.main
```
위 명령어를 실행하면 `assets/` 폴더의 모든 텍스트 파일을 변환하여 `out/` 폴더에 저장합니다.

### 고급 옵션 (CLI Arguments)
```bash
python -m src.main \
    --assets "./my_novels" \    # 입력 폴더 지정 (기본값: assets)
    --out "./ebooks" \          # 출력 폴더 지정 (기본값: out)
    --workers 8 \               # CPU 작업 스레드 수 (기본값: CPU 코어 수)
    --concurrency 4 \           # 동시 변환 파일 수 (I/O 제어)
    --overwrite                 # 기존 파일 덮어쓰기 (기본값: 건너뛰기)
```

---

## 📂 파일 정리 가이드 (File Structure)

표지 이미지를 자동으로 인식시키려면 아래 예시처럼 파일을 배치하세요.

### 권장 구조 1: 폴더별 정리 (가장 확실함)
```
assets/
├── 전지적 독자 시점/
│   ├── 전독시.txt
│   └── cover.jpg        <-- 'cover.jpg' 자동 인식
└── 나 혼자만 레벨업/
    ├── 나혼렙.txt
    └── cover.png
```

### 권장 구조 2: 파일명 일치
```
assets/
├── 달빛조각사.txt
├── 달빛조각사.jpg       <-- 텍스트 파일명과 같으면 표지로 인식
├── 룬의아이들.txt
└── 룬의아이들.webp
```

---

## ⚙️ 설정 및 커스터마이징

- **CSS 스타일 변경**: `src/core/converter/convert.py` 내의 `DEFAULT_CSS` 변수를 수정하여 폰트나 여백을 조정할 수 있습니다.
- **챕터 감지 패턴**: `src/core/converter/worker.py` 내의 `chapter_pattern` 정규표현식을 수정하여 특이한 챕터 양식에 대응할 수 있습니다.

## 📝 라이선스

MIT License. 자유롭게 수정하고 배포하세요.