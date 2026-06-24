# 문서 지도 (00_INDEX)

> 이 저장소의 모든 문서 진입점. **개발 시작 전 이 문서를 먼저 읽는다.**

## 북극성 (항상 인지)
**"Claude Code 초심자도 쉽게 설정할 수 있는 하네스 설정."** 모든 영역·UI·문서·기본값·문구는 이 기준으로 판단한다 — 어렵거나 전문가를 전제하면 재설계한다.

> 외부 자료(ECC 등)는 *설정 철학*만 참고했고, 콘텐츠·코드·문구는 복제하지 않았다. 이 저장소의 모든 문서·코드는 자체 작성이다.

## 영역 → "먼저 볼 문서" 매핑
| 개발 영역 | 먼저 볼 문서 |
|---|---|
| 전체 구조·의존 | `ARCHITECTURE.md` |
| 코드 규칙(네이밍·테스트·git) | `CONVENTIONS.md` |
| 용어 | `GLOSSARY.md` |
| IR(구성 모델) | `IR_SPEC.md` (계약) |
| 산출(폴더 매핑) | `EXPORT_SPEC.md` (계약) |
| 정합성/보안 검사 | `LINT_SPEC.md` (계약) |
| 라이브 시뮬레이터 | `SIMULATOR_SPEC.md` (계약) |
| 디스크 쓰기/병합 | `FS_SPEC.md` |
| 상태관리(store) | `STATE_SPEC.md` |
| PM2 프로토타입 | `PM2_SPEC.md` |
| GUI 레이아웃·위젯 | `UI_SPEC.md` (PM3) |
| 필드 가이드 | `FIELD_GUIDE_SPEC.md` (PM3) |
| 패키징·배포 | `PACKAGING.md` (PM4) |
| 결정 이력 | `DECISIONS/ADR-*.md` |

## SSOT(단일 진실원) 소유표
각 사실은 한 곳만 소유한다. **코드가 진실인 항목은 문서에 값을 베끼지 않고 모듈 경로만 가리킨다**(골든 드리프트 차단).

| 사실 | 소유(진실) |
|---|---|
| IR 필드·enum | `harness_core/ir/schema.py` |
| 경로 매핑(IR→파일) | `harness_core/export/export_ir.py` |
| 정합성 규칙 | `harness_core/lint/lint.py` |
| 시뮬레이터 우선순위 | `harness_core/sim/simulate.py` |
| 결정방식 색 | `STATE_SPEC.md` / app 메타 (단일 상수) |
| 비가역 결정 근거 | `DECISIONS/ADR-*.md` |

## 읽는 순서
1. `ARCHITECTURE.md` → 2. `CONVENTIONS.md` → 3. `GLOSSARY.md` → 4. 계약 SPEC(IR/EXPORT/LINT/SIMULATOR) → 5. 작업 영역 SPEC(FS/STATE/PM2).

## 마일스톤
PM1✅(코어) → PM2(프레임워크·직접쓰기) → PM3(기능 패리티 + 안내형 누적 흐름 + 역import) → PM4(패키징·MVP) → PM5(온보딩·완성도·강제수준 사다리·프리셋 확장).
