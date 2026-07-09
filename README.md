# 버클 (Buckle) — Claude Code 하네스 빌더 (Python 데스크톱)

Claude Code 하네스(`.claude/` + `CLAUDE.md`)를 GUI로 구성해 **로컬 프로젝트 폴더에 직접 생성/병합**하는 데스크톱 앱.

> **북극성:** "Claude Code 초심자도 쉽게 설정할 수 있는 하네스 설정." 모든 기본값·문구·UI 흐름은 이 기준으로 판단한다.

> TypeScript 웹 버전([ycw3320/harness-builder](https://github.com/ycw3320/harness-builder))을 Python 데스크톱으로 전환. 웹의 로컬 파일시스템 제약을 해소하고 "내려받아 즉시 진행"을 네이티브로 구현.

## 현재 상태 — PM6 완료 (pytest 71 GREEN)

PM1~5(코어·Qt 셸·동적 CRUD·프리셋·인앱 LLM·역import·exe 패키징)에 더해 **PM6 초심자 직관화** 완료:
랜딩(소개) 페이지 → **"하네스 없으면 ↔ 지금" before/after 시뮬 시연**(규칙 토글로 차단을 직접 꺼보는 체감→정의 아하) →
용어 2단 풀이(쉬운 말+호버) → export "다음 단계" 가이드. 한글 렌더는 **Pretendard 번들**(OFL)로 통일.
코어 산출물은 TS 버전과 **바이트 단위 동일**(골든 게이트).

## 다른 PC에서 시작하기 (Quick Start)

> Windows 11 + Python 3.11+ 기준. 저장소는 Private(ycw3320 계정) — clone 시 GitHub 인증 필요.

```powershell
# 1. 클론
git clone https://github.com/ycw3320/harness-builder-py.git
cd harness-builder-py

# 2. 가상환경 (권장)
python -m venv .venv
.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate

# 3. 의존성 설치 (앱 + 개발도구 + 인앱 LLM)
python -m pip install -e ".[dev,llm]"

# 4. 앱 실행
python -m harness_app.qt_shell.app

# 5. 테스트 (코어 + 골든 바이트-동일 게이트)
python -m pytest
```

- **앱만 가볍게:** `pip install -e .` (PySide6+pydantic만, LLM·테스트 제외).
- **인앱 LLM 미설치 시:** 외부 LLM 복사→붙여넣기 흐름이 기본 동작(앱은 정상 실행). API 키는 OS 자격증명관리자(keyring)에만 저장 — 코드·커밋·로그·QSettings에 미저장.
- **한글 폰트:** [Pretendard](https://github.com/orioncactus/pretendard)(SIL OFL 1.1, `harness_app/qt_shell/fonts/OFL.txt`)를 번들해 어느 PC에서나 동일 렌더. 번들 누락 시 시스템 폰트(Malgun) 폴백.

## exe 빌드 (선택)

```powershell
python -m pip install -e ".[build]"
python packaging/build_exe.py        # → dist/HarnessBuilder.exe (onefile, windowed)
```

상세는 [`docs/PACKAGING.md`](docs/PACKAGING.md).

## 아키텍처 (3계층, 단방향 의존)

```
harness_app(GUI/Qt) → harness_fs(pathlib 직접쓰기) → harness_core(순수 로직)
harness_llm(인앱 LLM, 선택)  ─ 코어 무의존, 앱에서만 호출
```
- `harness_core/` — pydantic v2 IR + export/lint/simulate/preset/enforcement/import. **GUI·FS·LLM 무의존.**
- `harness_fs/` — 로컬 폴더 비파괴 생성/병합 + 역import 리더.
- `harness_app/` — PySide6/Qt 셸 + 프레임워크 무관 `state`·`view_model`·`guides`.
- `harness_llm/` — BYO 키 인앱 LLM(credentials/prompts/content_models/client). 선택 설치(`[llm]`).

## 개발 게이트 (커밋 전)

```powershell
python -m ruff format --check .
python -m ruff check .
python -m pytest
```

골든 fixture는 `tests/golden/`(TS 산출 박제). 리팩터링 시 골든 갱신 금지 — 바이트 불변이 회귀 게이트.

## 문서

설계·규칙·결정은 [`docs/00_INDEX.md`](docs/00_INDEX.md)에서 시작. 비가역 결정은 [`docs/DECISIONS/`](docs/DECISIONS/)(ADR-0001~0011).

## 로드맵

- **PM1** ✅ 코어 포팅 + 골든 바이트-동일 게이트
- **PM2** ✅ PySide6/Qt 확정 + 직접 폴더쓰기 + Apple 테마
- **PM3** ✅ 동적 CRUD(전 6계층·전 kind) + 데이터 구동 폼 + 인앱 LLM
- **PM4** ✅ PyInstaller 패키징(`dist/HarnessBuilder.exe`)
- **PM5** ✅ 완성도 미터 + 프리셋 5종 + 강제수준 사다리 + 온보딩 + 역import
- **PM6** ✅ 초심자 직관화 — 랜딩·before/after 시뮬 시연·체감→정의 아하·용어 풀이·Pretendard 번들
- **PM7(예정)** 통합 하네스 파일(.harness.json 저장=공유) + lint 보안 룰팩 + 성숙도 레벨 (골든 게이트 2계층화 선행)
