# ADR-0012: 골든 게이트 2계층화 (frozen / extended)

- **상태:** 수락 (2026-06-29)
- **맥락:** PM7부터 코어에 신규 기능(migrate·보안 lint 룰셋 등)을 ADD 한다. 기존 골든 게이트는
  "TS 산출과 바이트 동일" 단일 계층이라, 코어 ADD 가 시작되면 커밋마다 '골든을 갱신해도 되는가'가
  재협상되는 문제가 있다(규율 붕괴 위험).
- **결정:** `tests/golden/` 을 2계층으로 분리.
  - **`frozen/`** — TS 기원 박제 6개(preset_ir·export_preset·assemble_*·lint_preset·simulate).
    **영구 불변** — 어떤 커밋도 재생성·수정 금지. 기존 코어 표면(기본 시그니처 호출 결과)이
    이 계층으로 봉인된다. 신규 코어 ADD 는 기본 호출 결과를 바꾸지 않는 형태(opt-in 파라미터,
    신규 모듈)여야 한다.
  - **`extended/`** — Python 자체 박제. 신규 코어 ADD 전용. `scripts/gen_golden_ext.py` 의
    GENERATORS 에 등록해 생성하며, **생성 커밋과 검증(코어 변경) 커밋을 분리**한다 — 같은 커밋에서
    코어와 extended 골든을 함께 바꾸면 게이트가 무력화되므로 금지.
- **로더:** conftest `golden(name)` 픽스처가 frozen → extended 순으로 탐색(테스트 무수정).
- **영향:** PM7 S2(migrate)·S3(보안 룰셋)이 이 절차의 첫 소비자. 관련 [[ADR-0003]](골든 게이트).
