"""kind 별 빈 component 생성기."""

from __future__ import annotations

import secrets

from .schema import (
    HarnessComponent,
    Hook,
    Layer,
    McpServer,
    PermissionRule,
    PolicyDoc,
    ProseGuideline,
    SubAgent,
)


def gen_id(prefix: str) -> str:
    """짧은 고유 id (8 hex)."""
    return f"{prefix}-{secrets.token_hex(4)}"


def create_component(kind: str, layer: Layer) -> HarnessComponent:
    if kind == "prose-guideline":
        return ProseGuideline(
            id=gen_id("prose"),
            layer=layer,
            title="새 지침",
            involvement="assisted",
            enabled=True,
            scope="project",
            heading="새 섹션",
            body="",
        )
    if kind == "permission-rule":
        return PermissionRule(
            id=gen_id("perm"),
            layer=layer,
            title="새 권한 규칙",
            involvement="manual-gate",
            enabled=True,
            action="ask",
            pattern="Bash(:*)",
        )
    if kind == "mcp-server":
        return McpServer(
            id=gen_id("mcp"),
            layer=layer,
            title="새 외부 도구",
            involvement="assisted",
            enabled=True,
            server_name="my-server",
            command="npx",
            args=[],
            env={},
        )
    if kind == "hook":
        return Hook(
            id=gen_id("hook"),
            layer=layer,
            title="새 가드레일",
            involvement="auto",
            enabled=True,
            event="PreToolUse",
            matcher_tool="Write|Edit",
            action="deny",
            script_name="my-hook.sh",
            script_body="#!/usr/bin/env bash\n# 차단 조건을 작성하세요\nexit 0\n",
        )
    if kind == "policy-doc":
        return PolicyDoc(
            id=gen_id("policy"),
            layer=layer,
            title="새 규칙 문서",
            involvement="assisted",
            enabled=True,
            doc_name="my-rule.md",
            body="",
        )
    if kind == "sub-agent":
        return SubAgent(
            id=gen_id("agent"),
            layer=layer,
            title="새 에이전트",
            involvement="assisted",
            enabled=True,
            name="my-agent",
            description="",
            tools=[],
            system_prompt="",
        )
    raise ValueError(f"알 수 없는 kind: {kind}")
