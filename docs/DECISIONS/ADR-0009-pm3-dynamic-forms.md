# ADR-0009: PM3 동적 CRUD + 가벼운 시작 + field-spec 폼

- **상태:** 수락 (2026-06-24)
- **맥락:** 사용자 요구 — "기본 세팅 과다 → 동적으로 늘려가기"(요구1), "안 채워도 되게 + 서브에이전트 등 전 kind 확장"(요구2). PM2 셸은 context·prose만 편집, 7개 시드 고정.
- **결정:**
  1. **가벼운 시작** — `minimal_preset`(context 개요 1개) 신규(코어 ADD만, 골든 불변). `state.PRESETS` 레지스트리 + `load_preset(name)`. 앱 기본 `preset="minimal"`, 좌패널 세그먼트(빈 시작/안전우선)로 전환.
  2. **동적 CRUD** — 행별 ↑/↓/복제/삭제(기존 `state` 메서드), 계층별 add-bar(`registry.addable_kinds_by_layer`) + 고급 토글(advanced kind 노출). 빈 계층 허용(verification 등).
  3. **전 6계층 풀 패리티** — `view_model.nav_items` 게이팅 제거(전 계층 interactive).
  4. **field-spec 폼(데이터 구동)** — `view_model.field_specs(kind)`가 kind별 필드(line/textarea/combo/list/dict)를 반환, `RowWidget`이 이를 동적 렌더(서브클래스 6종 회피). 공통 제목·결정방식(involvement) 콤보 + kind 필드 + §0.6 필드 가이드(복사→붙여넣기 프롬프트).
- **근거:** 백엔드(state CRUD·factory·registry 6 kind)는 이미 완비 → UI 노출만. 데이터 구동 폼이 유지보수·일관성에서 서브클래스보다 우수. 북극성(초심자 가벼운 시작·점진 확장)과 §0.6 안내형 누적 흐름에 정합.
- **핵심 구현:**
  - 편집 포커스 보존: `_signature`에 `(layer, advanced, (id,enabled,involvement))` 포함 — 텍스트 편집(title/필드)은 우패널만 갱신, 구조/계층/결정방식/고급 변경 시에만 중앙 재빌드.
  - list/dict 미니 에디터(`ListEditor`/`DictEditor`)는 초기 로드 중 미통지(_loading)로 patch 폭주 방지. 위젯은 값 설정 후 시그널 연결.
  - 펼침 높이는 specs로 추정(`_FIELD_H`).
- **영향:** prose 외 kind도 인라인 편집(PM3-A의 prose-only 가드 제거). 관련 [[ADR-0010]](인앱 LLM), [[ADR-0008]](테마).
