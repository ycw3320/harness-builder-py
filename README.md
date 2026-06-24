# 하네스 빌더 (Python 데스크톱)

Claude Code 하네스(`.claude/` + `CLAUDE.md`)를 GUI로 구성해 **로컬 프로젝트 폴더에 직접 생성/병합**하는 데스크톱 앱.

> TypeScript 웹 버전([ycw3320/harness-builder](https://github.com/ycw3320/harness-builder))을 Python 데스크톱으로 전환. 웹의 로컬 파일시스템 제약을 해소하고 "내려받아 즉시 진행"을 네이티브로 구현.

## 현재 상태 — PM1 완료

**코어 포팅 + 바이트-동일 골든 게이트 통과** (pytest 25 GREEN). TS 코어(IR/export/lint/시뮬레이터)를 Python으로 직역했고, 산출물이 TS와 **바이트 단위로 동일**함을 골든 fixture로 검증.

## 아키텍처 (3계층, 단방향 의존)

```
harness_app(GUI) → harness_fs(pathlib 직접쓰기) → harness_core(순수 로직)
```
- `harness_core/` — pydantic v2 IR + export/lint/simulate/preset. **GUI·FS 무의존.**
- `harness_fs/` — 로컬 폴더 직접 생성/병합 (PM2).
- `harness_app/` — GUI. 프레임워크는 **PM2에서 Flet·Qt 양쪽 프로토타입 비교 후 확정.**

## 개발

```bash
python -m pip install -e ".[dev]"
python -m pytest          # 코어 테스트 + 골든 바이트-동일 게이트
```

골든 fixture는 `tests/golden/`(TS 산출 박제). 재생성: TS repo에서 `npx -y tsx scripts/gen-golden.ts <out>`.

## 문서

설계·규칙·결정은 [`docs/00_INDEX.md`](docs/00_INDEX.md)에서 시작 — 아키텍처·컨벤션·용어집·계약 SPEC(IR/EXPORT/LINT/SIMULATOR)·FS/STATE/PM2 SPEC·ADR. 개발 시 각 영역은 "먼저 볼 문서"를 따른다.

## 로드맵
- **PM1** ✅ 코어 포팅 + 골든 게이트
- **PM2** Flet·Qt 최소 셸 + 직접 폴더쓰기 + 컴팩트 행 비교 → 프레임워크 확정
- **PM3** 전 계층 + 컴팩트행 + 컨텍스트 문서뷰 + 시뮬레이터 + 필드 가이드 (TS 기능 패리티)
- **PM4** 패키징·배포
