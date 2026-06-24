# 정합성·보안 검사 명세 (계약)

> **진실원: `harness_core/lint/lint.py`.** error가 1건이라도 있으면 **export 차단**(`has_errors()`).

## 현재 규칙 (PM1)
- **error:** `duplicate-id` · `hook-missing-script` · `permission-conflict`(allow↔deny 동일 패턴) · `agent-tool-denied`(전면 deny된 도구를 agent가 요구) · `inline-secret`(mcp env가 `${VAR}` 아님)
- **warning:** `empty-harness` · `low-confidence`(intent.confidence<0.6)

## 확장 계획 — "실행 전 보안 검증"(PM3, 우리 해자)
ECC AgentShield 철학을 우리 라이브 패널에 내장(자체 구현, 복제 아님):
- 권한 과다(너무 넓은 `allow`) 경고
- MCP 서버 >10 / 도구 과다 → 토큰비용 경고
- 훅 스크립트 인젝션 의심 패턴
- 시크릿 패턴 강화(env 외 위치까지)

## 게이트
`lint_ir(ir)` → findings. 우 패널이 error/warning 렌더, error면 내보내기 버튼 잠금.
