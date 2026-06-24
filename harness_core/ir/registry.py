"""kind 레지스트리 + layer 별 추가 가능 kind."""

from __future__ import annotations

from .schema import ComponentKind, Layer

kind_registry: dict[str, dict] = {
    "prose-guideline": {
        "label": "지침 (CLAUDE.md)",
        "default_layer": "context",
        "guide_key": "prose-guideline",
    },
    "permission-rule": {
        "label": "권한 규칙",
        "default_layer": "permissions",
        "guide_key": "permission-rule",
    },
    "mcp-server": {"label": "외부 도구 (MCP)", "default_layer": "mcp", "guide_key": "mcp-server"},
    "hook": {"label": "가드레일 hook", "default_layer": "guardrails", "guide_key": "hook"},
    "policy-doc": {"label": "규칙 문서", "default_layer": "guardrails", "guide_key": "policy-doc"},
    "sub-agent": {
        "label": "에이전트 (sub-agent)",
        "default_layer": "workflow",
        "guide_key": "sub-agent",
    },
}

# basic=False 는 고급 모드에서만 노출
addable_kinds_by_layer: dict[str, list[dict]] = {
    "context": [
        {"kind": "prose-guideline", "basic": True},
        {"kind": "policy-doc", "basic": False},
    ],
    "permissions": [{"kind": "permission-rule", "basic": True}],
    "mcp": [{"kind": "mcp-server", "basic": True}],
    "guardrails": [
        {"kind": "hook", "basic": True},
        {"kind": "policy-doc", "basic": True},
    ],
    "workflow": [{"kind": "sub-agent", "basic": True}],
    "verification": [],
}

__all__ = ["ComponentKind", "Layer", "addable_kinds_by_layer", "kind_registry"]
