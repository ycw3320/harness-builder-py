# 상태관리 명세 (store 포팅) — harness_app/state

> TS `store.ts`(Zustand) → Python 순수 상태 컨테이너. **UI 프레임워크 무의존**(Flet/Qt 공용).

## 상태 필드
`ir: HarnessIR` · `selected_layer: Layer` · `selected_file: str|None` · `advanced_mode: bool` · `scaffold: "minimal"|"harness-only"`

## CRUD / 액션
`add_component(kind)` · `add_prose_section(scope)` · `remove(id)` · `duplicate(id)` · `move(id, dir)` · `toggle(id)` · `patch(id, dict)` · `load_preset()`

## 규칙 (불변식)
- **불변 업데이트:** 매 변경마다 새 `HarnessIR`(`model_copy`/재구성) — 구독 diff 가능, 제자리 변형 금지.
- **move 그룹키:** `group_key(c) = f"{c.layer}|{c.scope if prose else ''}"` — **같은 그룹 내에서만 스왑**(전역/프로젝트 경계 보존). TS와 동치.
- **patch:** 호출측이 kind 유효 필드만 전달. patch 후 `parse_component` 재검증 권장.
- **duplicate:** 새 id + `"{title} (복제)"` + 원본 바로 뒤 삽입.

## 구독 (프레임워크 어댑터 경계)
`subscribe(listener)` → 상태 변경 통지. 위젯은 이 통지로 리렌더(Flet observable / Qt Signal). **이 한 곳이 프레임워크 배선의 유일 접점**(피벗 시 교체 지점).

## 결정방식(involvement) 색 — 단일 상수
`auto #1a7f37` · `assisted #0969da` · `manual-gate #bc4c00` (UI 메타 단일 출처).
