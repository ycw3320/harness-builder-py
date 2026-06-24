# ADR-0001: 3계층 단방향 의존 (core / fs / app)

- **상태:** 수락 (2026-06-24)
- **맥락:** GUI 프레임워크(Flet vs Qt)를 PM2에서 양쪽 프로토타입 후 결정한다. 프레임워크 교체가 프로젝트 전체 재작성으로 번지면 안 된다.
- **결정:** 의존을 단방향으로 고정한다 — `harness_app(GUI) → harness_fs(디스크) → harness_core(순수 로직)`. 코어는 어떤 상위 계층도 import 하지 않는다. GUI 의존은 `harness_app/`에만 둔다.
- **근거:** (1) 코어/FS를 GUI 없이 pytest로 회귀. (2) Flet↔Qt 피벗 시 교체 범위를 `harness_app/`로 격리. (3) 향후 CLI·다른 프런트도 같은 코어 재사용.
- **영향:** 위젯은 로직을 담지 않고 state/fs를 호출만 한다(B7 controllers). 코어는 PM1에서 완성·동결(무수정·소비만).
