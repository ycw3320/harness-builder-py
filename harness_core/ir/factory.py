"""kind 별 빈 component 생성기 (TS factory.ts 포팅)."""
from __future__ import annotations

import secrets

from .schema import (
    Hook,
    HarnessComponent,
    Layer,
    McpServer,
    PermissionRule,
    PolicyDoc,
    ProseGuideline,
    SubAgent,
)


def gen_id(prefix: str) -> str:
    """짧은 고유 id (TS crypto.randomUUID().slice(0,8) 대응 — 8 hex)."""
    return f"{prefix}-{secrets.token_hex(4)}"


def create_component(kind: str, layer: Layer) -> HarnessComponent:
    if kind == "prose-guideline":
        return ProseGuideline(
            id=gen_id("prose"), layer=layer, title="새 지침", involvement="assisted",
            enabled=True, scope="project", heading="새 섹션", body="",
        )
    if kind == "permission-rule":
        return PermissionRule(
            id=gen_id("perm"), layer=layer, title="새 권한 규칙", involvement="manual-gate",
            enabled=True, action="ask", pattern="Bash(:*)",
        )
    if kind == "mcp-server":
        return McpServer(
            id=gen_id("mcp"), layer=layer, title="새 외부 도구", involvement="assisted",
            enabled=True, serverName="my-server", command="npx", args=[], env={},
        )
    if kind == "hook":
        return Hook(
            id=gen_id("hook"), layer=layer, title="새 가드레일", involvement="auto",
            enabled=True, event="PreToolUse", matcherTool="Write|Edit", action="deny",
            scriptName="my-hook.sh", scriptBody="#!/usr/bin/env bash\n# 차단 조건을 작성하세요\nexit 0\n",
        )
    if kind == "policy-doc":
        return PolicyDoc(
            id=gen_id("policy"), layer=layer, title="새 규칙 문서", involvement="assisted",
            enabled=True, docName="my-rule.md", body="",
        )
    if kind == "sub-agent":
        return SubAgent(
            id=gen_id("agent"), layer=layer, title="새 에이전트", involvement="assisted",
            enabled=True, name="my-agent", description="", tools=[], systemPrompt="",
        )
    raise ValueError(f"알 수 없는 kind: {kind}")
