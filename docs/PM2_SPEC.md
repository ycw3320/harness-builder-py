# PM2 명세 — 프레임워크 결정 + 직접 폴더쓰기

> 목표: Flet·Qt **양쪽** 최소 셸을 만들어 실측 비교 → 프레임워크 1종 확정. 판정=에이전트 정량 + 사용자 최종(ADR-0004).

## 수직 슬라이스 S1~S6 (양 갈래 공통, context 1계층만 실동작)
| # | 요소 |
|---|---|
| S1 | 3-pane 셸(리사이즈 분할) |
| S2 | 좌 nav — `context`만 실동작, 나머지 5계층 비활성 라벨 + 결정방식 대표 색점 |
| S3 | 컴팩트 36px 행 — prose 행(제목+요약+색점+토글), 클릭 펼침 → heading/body 편집 |
| S4 | 편집 → `state.patch` → 우측 라이브 갱신 |
| S5 | 우 패널 — `lint_ir(ir)` + `assemble_project(ir)` 파일목록 + [폴더 선택→생성] |
| S6 | `write_tree(tree, dest)` 직접 폴더쓰기(비파괴 디폴트) |

시드: `safety_first_preset("my-project")`(context prose 2행 = 전역1·프로젝트1).
**PM3 이월:** 나머지 5계층 편집기·전 kind 폼·필드가이드·settings 딥머지·역import·멀티타깃.

## 갈래별
- **Flet** `harness_app/flet_shell/`: `ft.Row`+`VerticalDivider` 3-pane · 커스텀 nav · `Container(height=36)`+`AnimatedSwitcher` · `FilePicker.get_directory_path` · `flet run -d` 핫리로드.
- **PySide6**(LGPL) `harness_app/qt_shell/`: `QSplitter` 3-pane · `QListWidget` nav · `setFixedHeight(36)`+`QPropertyAnimation`+QSS · `QFileDialog.getExistingDirectory`.
- **state mutator는 갈래 무관 동일**(B1). 차이는 `subscribe` 배선뿐(`page.update()` vs `Signal.emit`) — 이 LOC도 M6에 반영.

## 결정 루브릭 (가중 100)
| 항목 | 가중 | 채점 |
|---|---|---|
| M1 36px 밀도 | 15 | 에이전트(정량) |
| M2 색점 픽셀제어 | 10 | 에이전트 |
| M3 펼침 애니 | 12 | 에이전트 1차 + 사용자 승인 |
| M4 3-pane 리사이즈 | 12 | 에이전트 1차 + 사용자 승인 |
| M5 모던룩 | 13 | **사용자 최종** |
| M6 LOC/구현시간 | 20 | 에이전트(정량) |
| M7 핫리로드 | 8 | 에이전트 |
| M8 패키징 | 10 | 에이전트 |

점수 = Σ(PASS=가중 / 부분=×0.5 / FAIL=0).

## 임계 (pass / pivot)
- 점수차 ≥ 10 → 고득점 즉시 채택.
- < 10 & 양 갈래 M1·M3·M4 FAIL 0 → 사용자 M5 결선(동률 시 M6 → M8).
- 한 갈래라도 M1·M3·M4 FAIL → 탈락. 양 갈래 동반 FAIL → 보조 갈래 검토를 사용자에 보고.
- 시간박스: 갈래당 셸 1~2일.

## DoD
양 셸 S1~S6 동작(동일 시드·state API) + `write_tree` 실폴더 생성/병합(비파괴 확인) + 루브릭 채점·스크린샷 + 사용자 M5 확정 → 1종 채택, 폐기 갈래 `_archive/` 격리.
