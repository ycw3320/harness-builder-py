"""안전우선 프리셋 (TS preset-safety-first.ts 포팅) — 골든 preset_ir.json 과 동일."""
from __future__ import annotations

from .schema import Hook, HarnessIR, Intent, Meta, PermissionRule, PolicyDoc, ProseGuideline

_GLOBAL_LANG_BODY = "\n".join([
    "- 모든 출력은 한국어로 작성한다.",
    "- 자격 증명·API 키·토큰을 코드/커밋/로그에 남기지 않는다.",
    "- 파일 삭제·덮어쓰기 등 비가역 작업 전에는 먼저 확인한다.",
])

_SECRET_HOOK_BODY = "\n".join([
    "#!/usr/bin/env bash",
    "# .env* 파일 쓰기 차단 — 시크릿 보호 (강제수준 3단: hook)",
    "input=$(cat)",
    "path=$(printf '%s' \"$input\" | grep -oE '\"file_path\"[[:space:]]*:[[:space:]]*\"[^\"]*\"' | head -1)",
    "case \"$path\" in",
    "  *.env*) echo \"차단: .env 파일에는 쓸 수 없습니다 (시크릿 보호)\" >&2; exit 2;;",
    "esac",
    "exit 0",
])

_SECRET_POLICY_BODY = "\n".join([
    "# 시크릿 취급 규칙",
    "",
    "- 비밀키·토큰·비밀번호는 `.env`(gitignore) 또는 비밀 저장소에만 둔다.",
    "- 설정 파일에는 `${VAR}` 플레이스홀더만 사용하고 실제 값을 넣지 않는다.",
    "- 발견 즉시 사용자에게 보고하고 회수한다.",
])


def safety_first_preset(project_name: str = "my-project") -> HarnessIR:
    return HarnessIR(
        meta=Meta(
            irVersion="1.0", targetTool="claude-code", preset="safety-first", projectName=project_name
        ),
        components=[
            ProseGuideline(
                id="ctx-global-lang", layer="context", title="언어·보안 기본 자세 (전역)",
                involvement="assisted", enabled=True, scope="global",
                heading="언어·보안 기본 자세", body=_GLOBAL_LANG_BODY,
                intent=Intent(raw="한국어로, 보수적으로, 비밀키 노출 금지", compiledBy="preset", confidence=1),
            ),
            ProseGuideline(
                id="ctx-project-overview", layer="context", title="프로젝트 개요",
                involvement="assisted", enabled=True, scope="project", heading="프로젝트 개요",
                body="<!-- 프로젝트 스택·도메인·빌드 명령·명명 규칙을 여기에 기술하세요. -->",
                intent=Intent(raw="프로젝트 고유 컨텍스트 자리표시자", compiledBy="preset", confidence=1),
            ),
            PermissionRule(
                id="perm-deny-rm", layer="permissions", title="재귀 강제 삭제 금지",
                involvement="manual-gate", enabled=True, action="deny", pattern="Bash(rm -rf:*)",
                intent=Intent(raw="rm -rf 류 위험 삭제 명령 차단", compiledBy="preset", confidence=1),
            ),
            PermissionRule(
                id="perm-ask-forcepush", layer="permissions", title="강제 push 확인",
                involvement="manual-gate", enabled=True, action="ask", pattern="Bash(git push --force:*)",
                intent=Intent(raw="강제 push 는 사용자 확인 후", compiledBy="preset", confidence=1),
            ),
            PermissionRule(
                id="perm-allow-test", layer="permissions", title="테스트 실행 허용",
                involvement="manual-gate", enabled=True, action="allow", pattern="Bash(npm run test:*)",
                intent=Intent(raw="테스트 실행은 자유 허용", compiledBy="preset", confidence=1),
            ),
            Hook(
                id="guard-hook-secrets", layer="guardrails", title=".env 쓰기 차단 (시크릿 보호)",
                involvement="manual-gate", enabled=True, event="PreToolUse", matcherTool="Write|Edit",
                pathGlob="**/.env*", action="deny", scriptName="block-secrets.sh", scriptBody=_SECRET_HOOK_BODY,
                intent=Intent(raw="비밀키 파일을 못 쓰게 막아", compiledBy="preset", confidence=1),
            ),
            PolicyDoc(
                id="guard-policy-secrets", layer="guardrails", title="시크릿 취급 규칙",
                involvement="manual-gate", enabled=True, docName="secrets.md", body=_SECRET_POLICY_BODY,
                intent=Intent(raw="시크릿 취급 규칙 문서화", compiledBy="preset", confidence=1),
            ),
        ],
    )
