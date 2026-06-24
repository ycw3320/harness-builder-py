# _archive — 폐기 갈래 보관소

PM2 프레임워크 판정([[ADR-0007]])에서 **탈락**한 구현을 삭제하지 않고 격리한다(비파괴 원칙).

- `flet_shell/` — Flet 갈래 S1~S6 프로토타입. 동작했으나 PySide6/Qt에 루브릭 +10.5로 패배.
  탈락 사유: flet 0.85 API 불안정(파손 7건)·웹모드 폴더쓰기 불가·네이티브 splitter 부재.
  참고용으로만 남김 — 빌드/패키징/lint 대상 아님(`pyproject` `extend-exclude`).

본 폴더는 패키징(`harness_app*`/`harness_fs*`/`harness_core*` find)·ruff 대상에서 제외된다.
