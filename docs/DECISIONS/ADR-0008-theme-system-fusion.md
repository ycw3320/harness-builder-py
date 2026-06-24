# ADR-0008: 테마 시스템(라이트/다크) + Fusion 스타일 + QSS 규칙

- **상태:** 수락 (2026-06-24)
- **맥락:** 사용자 요구 — "애플 앱처럼 심플, 하얀(크림) ↔ 스페이스그레이 라이트/다크 토글". 기존 GitHub풍 단일 스타일을 Apple 미니멀 2-테마로 교체.
- **결정:**
  1. **토큰 단일 소스** — `LIGHT`/`DARK` dict(`harness_app/qt_shell/app.py`) + `string.Template` 기반 `build_qss(tokens)`. 팔레트는 워크플로(디자인 패널 4종→합성 'Graphite Crème', WCAG AA 검증) 산출. 라이트=크림 `#FBFBF9`/흰 카드, 다크=Space Gray `#1C1C1E→#2C2C2E→#3A3A3C`. 강조=Apple systemBlue(라이트 `#0A6FD6`/다크 `#0A84FF`).
  2. **런타임 토글** — 우상단 세그먼트(`라이트`/`다크`), `QApplication.setStyleSheet` 전체 스왑(재시작 불요), `QSettings("harness-builder","qt-shell")` persist. `HB_THEME` env 로 초기 테마 강제(스크린샷용).
  3. **Fusion 스타일 고정** — `app.setStyle("Fusion")`. 네이티브 `windowsvista` 스타일은 `QPushButton`의 `background-color` 등 QSS를 무시 → Fusion 으로 일관 적용.
- **QSS 규칙(회귀 방지):**
  - **무선택자 `setStyleSheet("background: transparent;")` 금지.** 위젯에 건 무선택자 선언은 *자식까지* 전파되어 하위 버튼/콤보의 배경을 덮어쓴다(이번에 기본 버튼 배경이 안 칠해진 원인). 투명이 필요하면 QSS 에서 **타입/objectName 선택자**로 스코프하라(예: `QScrollArea { background: transparent; }`).
  - 본문 패널 배경은 objectName 선택자(`#centerPane`/`#leftPane`/`#rightPane`)로만 칠하고, 중간 컨테이너는 규칙 없이 두어 투명 상속(중앙 빈 영역도 캔버스색으로 채워짐).
  - involvement 색(dot 면색·pill 틴트+텍스트)은 행 빌드 시 토큰에서 인라인 주입(모드별 셰이드).
- **부수 개선:** 편집(콘텐츠 patch)은 우패널만 갱신, 구조/계층/테마 변경 시에만 중앙·좌측 재빌드 → **타자 중 편집 포커스 보존**(시그니처 비교 라우팅).
- **영향:** 한글은 오프스크린에서 `malgun.ttf` 명시 로드 유지. 향후 신규 위젯도 토큰·objectName 선택자 규칙을 따른다. 관련 [[ADR-0007]](Qt 채택).
