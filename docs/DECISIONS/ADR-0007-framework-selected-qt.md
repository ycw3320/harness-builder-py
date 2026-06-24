# ADR-0007: 프레임워크 확정 = PySide6/Qt

- **상태:** 수락 (2026-06-24) — [[ADR-0004]](판정 방식)의 결과
- **맥락:** PM2에서 Flet·PySide6/Qt 양쪽 최소 셸(S1~S6)을 동일 시드·동일 `state`/`view_model` API로 구현하고 루브릭(가중 100)으로 채점했다. 에이전트 정량 + 사용자 모던룩(M5) 최종.
- **결정:** **PySide6/Qt 채택.** Flet 갈래는 `_archive/flet_shell/` 로 격리(삭제 아님).
- **루브릭 결과(M5 제외 /87):** Qt **74** vs Flet 63.5 (Qt +10.5, 임계 ≥10 충족). 사용자가 모던룩(M5) 포함 Qt 확정.

  | 지표(가중) | Qt | Flet |
  |---|---|---|
  | M1 36px 밀도(15) | 15 | 7.5 |
  | M2 색점(10) | 10 | 10 |
  | M3 펼침 애니(12) | 12 | 12 |
  | M4 리사이즈(12) | 12 | 6 |
  | M6 LOC/시간(20) | 16 | 13 |
  | M7 핫리로드(8) | 0 | 8 |
  | M8 패키징(10) | 9 | 7 |

- **근거(점수 외 핵심):** 북극성("초심자도 쉽게 + 신뢰 가능")에 정합.
  1. **안정 성숙 API** — Qt 첫 시도 동작. Flet 0.85(1.0 직전)는 한 세션에 API 파손 7건(`FilePicker(on_result)`·`page.open`·`padding.symmetric`·`border.all`·`Dropdown.on_change`·`FilePicker=Service`·`ElevatedButton deprecated`) → 유지보수 위험.
  2. **오프스크린 렌더** — `QT_QPA_PLATFORM=offscreen` 로 무디스플레이 PNG 캡처 → 자동 시각 회귀 테스트/CI 가능(결정성 제품과 정합).
  3. **네이티브 폴더 다이얼로그 + QSplitter** — 직접 폴더쓰기(핵심 차별점)와 3-pane 리사이즈가 1급. Flet 웹모드는 로컬 폴더쓰기 불가.
- **포기한 것:** Flet의 더 적은 LOC(211 vs 321)·핫리로드·Material 룩 기본 제공. 한글은 Qt 오프스크린에서 폰트 파일 명시 로드 필요(`make_app` 처리됨).
- **영향:** PM3 본구현은 `harness_app/qt_shell/` 확장. 공유 `state`·`view_model`·`guides` 는 프레임워크 무관이라 그대로 재사용. PySide6 고정(PyQt6 GPL 회피, LGPL 준수).
