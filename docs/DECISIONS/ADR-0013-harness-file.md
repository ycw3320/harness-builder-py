# ADR-0013: 통합 하네스 파일(.harness.json) — 저장=공유=마이그레이션 단일 포맷

- **상태:** 수락 (2026-06-29)
- **맥락:** PM7 진화 1순위(심사 9/10). 작업이 메모리 전용이라 앱을 끄면 소실되고, 하네스를
  남에게 전달할 무손실 수단이 없었다(.claude 폴더 역import 는 hook action/path_glob 유실 best-effort).
- **결정:**
  - **단일 포맷·단일 확장자 `.harness.json`** — 작업 파일과 공유 파일을 나누지 않는다
    (이중 포맷 금지, 심사 지적 채택). 내용 = `HarnessIR.model_dump_json(by_alias=True, indent=2)`
    (camelCase alias — frozen 골든 `preset_ir.json` 과 같은 표현).
  - **코어 ADD `harness_core/ir/migrate.py`** — `load_ir_any(text)`: `meta.irVersion` 을 읽어
    `MIGRATIONS`(구버전→다음 버전 순수 변환) 를 순차 적용 후 검증 파싱. `dump_ir(ir)`: 직렬화 단일점.
    현재 1.0 단일 버전이라 MIGRATIONS 는 빈 dict — **스키마 버전을 올리는 커밋에서만 변환기 등록**.
  - **스키마 진화 규칙:** 신규 필드는 default 필수(구파일 호환), `extra="forbid"` 유지(오타 조기 검출),
    의미 변경·필드 제거 시에만 버전 상향+마이그레이션.
  - **수신 검증(해자의 두 번째 사용처):** 열기 직후 가져오기 전에 `lint_ir` + `sim_compare_ir` 로
    "이 하네스가 하는 일"을 결정론(LLM 0회) 표시 — 받은 하네스도 실행 전 안전 검증. hook 스크립트
    본문 확인 유도 문구 포함(스크립트는 실행 코드).
- **영향:** '회사 표준 하네스를 파일 1개로 전달 → 신입이 열고 before/after 로 이해' 시나리오 성립.
  frozen 골든 불변(신규 모듈 ADD). 관련 [[ADR-0002]](alias), [[ADR-0012]](2계층 골든).
