# 용어집 (단일 정의처)

> 모든 문서·UI 문구는 여기 정의를 따른다. (자체 작성 — 외부 자료 복제 아님)

## 도메인
- **하네스(harness):** 모델을 감싸 그 동작을 신뢰·반복 가능하게 만드는 비-모델 구성 전체. 여기선 Claude Code의 `.claude/` + `CLAUDE.md`.
- **하네스 엔지니어링:** 모델을 내 도메인·표준에 맞춰 길들이는 설정 행위. **이 도구의 대상은 그게 미숙한 초심자.**
- **IR(중간표현):** 하네스 구성을 코드/UI 무관하게 담는 데이터 모델(`harness_core/ir/schema.py`).
- **component:** IR의 구성 원자. 6 kind.
- **kind(6종):** `prose-guideline`(CLAUDE.md 지침) · `permission-rule`(권한) · `mcp-server`(외부도구) · `hook`(자동 차단) · `policy-doc`(규칙문서) · `sub-agent`(전문 역할).
- **layer(6종):** `context` · `permissions` · `mcp` · `guardrails` · `workflow` · `verification`. 좌측 nav의 영역.

## 두 눈금자
- **결정방식(involvement):** 이 항목을 누가 정하나 — `자동(auto)` / `추천(assisted)` / `직접(manual-gate)`. 색: auto `#1a7f37` / assisted `#0969da` / manual-gate `#bc4c00`.
- **강제수준(enforcement) 사다리:** 같은 의도의 강제력 단계 — 프로즈(권고) < 정책문서 < hook(자동 차단). (사다리 UI는 PM5)

## 산출·동작
- **export:** IR → 가상 파일트리(`VirtualFile{path, content}`).
- **assemble:** export 결과를 프로젝트 폴더 트리로 조립. **scaffold** 옵션: `minimal`(골격 동봉) / `harness-only`(하네스만).
- **write_tree:** 가상 트리를 실제 디스크에 쓰기. 기본 **비파괴(SKIP_EXISTING)** + dry-run.
- **라이브 시뮬레이터:** 가상 액션(.env 쓰기 등)을 IR에 대조해 차단/확인/통과를 **LLM 0회·실시간** 시연(`harness_core/sim`). 우리 핵심 차별점.
- **lint(실행 전 안전 검증):** 시크릿·모순 + (확장) 권한 과다·MCP 과다·훅 인젝션 경고. error면 export 차단.
- **골든 게이트:** TS 산출과 바이트 동치 회귀(ADR-0003).
- **살아있는 관리자(역import):** 기존 `.claude/`를 읽어 IR로 역구성(A3, PM3).

## UX
- **안내형 누적 빌드 흐름(§0.6):** 설정항목 제시 → "외부 LLM에 이렇게 요청" 제안·복사 → 답 채우기 → 시뮬·lint·완성도 실시간 → 반복 누적 → 완성·내보내기. **주력 UX.**
- **필드 가이드:** 항목별 "외부 LLM에 이렇게 요청하세요" 프롬프트·예시·복사(PM3).
- **프리셋:** 초기 구성 묶음. 현재 `안전우선(safety-first)`.
- **완성도 미터 / 다음 영역 추천:** 누적 진행 가시화(PM3).
