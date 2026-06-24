"""안전우선 프리셋 — 골든 preset_ir.json 과 동일."""

from __future__ import annotations

from .schema import (
    HarnessIR,
    Hook,
    Intent,
    Meta,
    PermissionRule,
    PolicyDoc,
    ProseGuideline,
    SubAgent,
)

_GLOBAL_LANG_BODY = "\n".join(
    [
        "- 모든 출력은 한국어로 작성한다.",
        "- 자격 증명·API 키·토큰을 코드/커밋/로그에 남기지 않는다.",
        "- 파일 삭제·덮어쓰기 등 비가역 작업 전에는 먼저 확인한다.",
    ]
)

_SECRET_HOOK_BODY = "\n".join(
    [
        "#!/usr/bin/env bash",
        "# .env* 파일 쓰기 차단 — 시크릿 보호 (강제수준 3단: hook)",
        "input=$(cat)",
        'path=$(printf \'%s\' "$input" | grep -oE \'"file_path"[[:space:]]*:[[:space:]]*"[^"]*"\' | head -1)',
        'case "$path" in',
        '  *.env*) echo "차단: .env 파일에는 쓸 수 없습니다 (시크릿 보호)" >&2; exit 2;;',
        "esac",
        "exit 0",
    ]
)

_SECRET_POLICY_BODY = "\n".join(
    [
        "# 시크릿 취급 규칙",
        "",
        "- 비밀키·토큰·비밀번호는 `.env`(gitignore) 또는 비밀 저장소에만 둔다.",
        "- 설정 파일에는 `${VAR}` 플레이스홀더만 사용하고 실제 값을 넣지 않는다.",
        "- 발견 즉시 사용자에게 보고하고 회수한다.",
    ]
)


def safety_first_preset(project_name: str = "my-project") -> HarnessIR:
    return HarnessIR(
        meta=Meta(
            ir_version="1.0",
            target_tool="claude-code",
            preset="safety-first",
            project_name=project_name,
        ),
        components=[
            ProseGuideline(
                id="ctx-global-lang",
                layer="context",
                title="언어·보안 기본 자세 (전역)",
                involvement="assisted",
                enabled=True,
                scope="global",
                heading="언어·보안 기본 자세",
                body=_GLOBAL_LANG_BODY,
                intent=Intent(
                    raw="한국어로, 보수적으로, 비밀키 노출 금지", compiled_by="preset", confidence=1
                ),
            ),
            ProseGuideline(
                id="ctx-project-overview",
                layer="context",
                title="프로젝트 개요",
                involvement="assisted",
                enabled=True,
                scope="project",
                heading="프로젝트 개요",
                body="<!-- 프로젝트 스택·도메인·빌드 명령·명명 규칙을 여기에 기술하세요. -->",
                intent=Intent(
                    raw="프로젝트 고유 컨텍스트 자리표시자", compiled_by="preset", confidence=1
                ),
            ),
            PermissionRule(
                id="perm-deny-rm",
                layer="permissions",
                title="재귀 강제 삭제 금지",
                involvement="manual-gate",
                enabled=True,
                action="deny",
                pattern="Bash(rm -rf:*)",
                intent=Intent(
                    raw="rm -rf 류 위험 삭제 명령 차단", compiled_by="preset", confidence=1
                ),
            ),
            PermissionRule(
                id="perm-ask-forcepush",
                layer="permissions",
                title="강제 push 확인",
                involvement="manual-gate",
                enabled=True,
                action="ask",
                pattern="Bash(git push --force:*)",
                intent=Intent(
                    raw="강제 push 는 사용자 확인 후", compiled_by="preset", confidence=1
                ),
            ),
            PermissionRule(
                id="perm-allow-test",
                layer="permissions",
                title="테스트 실행 허용",
                involvement="manual-gate",
                enabled=True,
                action="allow",
                pattern="Bash(npm run test:*)",
                intent=Intent(raw="테스트 실행은 자유 허용", compiled_by="preset", confidence=1),
            ),
            Hook(
                id="guard-hook-secrets",
                layer="guardrails",
                title=".env 쓰기 차단 (시크릿 보호)",
                involvement="manual-gate",
                enabled=True,
                event="PreToolUse",
                matcher_tool="Write|Edit",
                path_glob="**/.env*",
                action="deny",
                script_name="block-secrets.sh",
                script_body=_SECRET_HOOK_BODY,
                intent=Intent(raw="비밀키 파일을 못 쓰게 막아", compiled_by="preset", confidence=1),
            ),
            PolicyDoc(
                id="guard-policy-secrets",
                layer="guardrails",
                title="시크릿 취급 규칙",
                involvement="manual-gate",
                enabled=True,
                doc_name="secrets.md",
                body=_SECRET_POLICY_BODY,
                intent=Intent(raw="시크릿 취급 규칙 문서화", compiled_by="preset", confidence=1),
            ),
        ],
    )


def minimal_preset(project_name: str = "my-project") -> HarnessIR:
    """가벼운 시작 — 프로젝트 개요 prose 1개(본문 비움)만. 필요한 만큼 동적으로 추가."""
    return HarnessIR(
        meta=Meta(
            ir_version="1.0",
            target_tool="claude-code",
            preset="minimal",
            project_name=project_name,
        ),
        components=[
            ProseGuideline(
                id="ctx-project-overview",
                layer="context",
                title="프로젝트 개요",
                involvement="assisted",
                enabled=True,
                scope="project",
                heading="프로젝트 개요",
                body="",
                intent=Intent(
                    raw="프로젝트 고유 컨텍스트 자리표시자", compiled_by="preset", confidence=1
                ),
            ),
        ],
    )


def speed_preset(project_name: str = "my-project") -> HarnessIR:
    """속도 — 빠른 반복. 자주 쓰는 개발 명령 자유 허용, 가드레일 최소."""
    return HarnessIR(
        meta=Meta(
            ir_version="1.0", target_tool="claude-code", preset="speed", project_name=project_name
        ),
        components=[
            ProseGuideline(
                id="ctx-speed",
                layer="context",
                title="빠른 반복 자세",
                involvement="assisted",
                enabled=True,
                scope="project",
                heading="빠른 반복",
                body="- 간결하게 답하고 불필요한 확인은 줄인다.\n- 자주 쓰는 빌드·테스트 명령은 바로 실행한다.",
                intent=Intent(raw="속도 우선", compiled_by="preset", confidence=1),
            ),
            PermissionRule(
                id="perm-allow-npm",
                layer="permissions",
                title="개발 명령 허용",
                involvement="manual-gate",
                enabled=True,
                action="allow",
                pattern="Bash(npm run:*)",
                intent=Intent(raw="개발 명령 자유 허용", compiled_by="preset", confidence=1),
            ),
            PermissionRule(
                id="perm-allow-git",
                layer="permissions",
                title="git 허용",
                involvement="manual-gate",
                enabled=True,
                action="allow",
                pattern="Bash(git:*)",
                intent=Intent(raw="git 자유 허용", compiled_by="preset", confidence=1),
            ),
        ],
    )


def mvp_preset(project_name: str = "my-project") -> HarnessIR:
    """MVP — 새 프로젝트 균형 스타터. 언어·보안 기본 + 위험 삭제 차단 + 테스트 허용."""
    return HarnessIR(
        meta=Meta(
            ir_version="1.0", target_tool="claude-code", preset="mvp", project_name=project_name
        ),
        components=[
            ProseGuideline(
                id="ctx-global-lang",
                layer="context",
                title="언어·보안 기본 자세 (전역)",
                involvement="assisted",
                enabled=True,
                scope="global",
                heading="언어·보안 기본 자세",
                body=_GLOBAL_LANG_BODY,
                intent=Intent(raw="한국어·보수적", compiled_by="preset", confidence=1),
            ),
            ProseGuideline(
                id="ctx-project-overview",
                layer="context",
                title="프로젝트 개요",
                involvement="assisted",
                enabled=True,
                scope="project",
                heading="프로젝트 개요",
                body="<!-- 스택·빌드 명령·도메인을 여기에 적으세요. -->",
                intent=Intent(
                    raw="프로젝트 컨텍스트 자리표시자", compiled_by="preset", confidence=1
                ),
            ),
            PermissionRule(
                id="perm-deny-rm",
                layer="permissions",
                title="재귀 강제 삭제 금지",
                involvement="manual-gate",
                enabled=True,
                action="deny",
                pattern="Bash(rm -rf:*)",
                intent=Intent(raw="위험 삭제 차단", compiled_by="preset", confidence=1),
            ),
            PermissionRule(
                id="perm-allow-test",
                layer="permissions",
                title="테스트 실행 허용",
                involvement="manual-gate",
                enabled=True,
                action="allow",
                pattern="Bash(npm run test:*)",
                intent=Intent(raw="테스트 자유 허용", compiled_by="preset", confidence=1),
            ),
        ],
    )


def enterprise_preset(project_name: str = "my-project") -> HarnessIR:
    """엔터프라이즈 — 안전우선 + 코드 리뷰 규칙 문서 + 리뷰 sub-agent(보안·컴플라이언스 강화)."""
    base = safety_first_preset(project_name).components
    extra: list = [
        PolicyDoc(
            id="guard-policy-review",
            layer="guardrails",
            title="코드 리뷰 규칙",
            involvement="assisted",
            enabled=True,
            doc_name="review.md",
            body="- 모든 변경은 리뷰 후 머지한다.\n- 보안·에러처리·테스트 커버리지를 점검한다.",
            intent=Intent(raw="코드 리뷰 규칙 문서화", compiled_by="preset", confidence=1),
        ),
        SubAgent(
            id="wf-reviewer",
            layer="workflow",
            title="코드 리뷰어",
            involvement="assisted",
            enabled=True,
            name="code-reviewer",
            description="변경된 코드의 보안·버그를 점검(수정은 하지 않음)",
            tools=["Read", "Grep"],
            model=None,
            system_prompt="변경된 코드만 읽어 보안·버그·누락을 점검하고, 수정은 하지 않는다.",
            intent=Intent(raw="리뷰 전담 에이전트", compiled_by="preset", confidence=1),
        ),
    ]
    return HarnessIR(
        meta=Meta(
            ir_version="1.0",
            target_tool="claude-code",
            preset="enterprise",
            project_name=project_name,
        ),
        components=[*base, *extra],
    )


# 프리셋 레지스트리 — 시작 화면 선택
PRESETS = {
    "minimal": minimal_preset,
    "safety-first": safety_first_preset,
    "speed": speed_preset,
    "mvp": mvp_preset,
    "enterprise": enterprise_preset,
}
