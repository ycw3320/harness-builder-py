"""kind 레지스트리 + layer 별 추가 가능 kind (TS registry.ts 포팅)."""
from __future__ import annotations

from .schema import ComponentKind, Layer

kind_registry: dict[str, dict] = {
    "prose-guideline": {"label": "지침 (CLAUDE.md)", "defaultLayer": "context", "guideKey": "prose-guideline"},
    "permission-rule": {"label": "권한 규칙", "defaultLayer": "permissions", "guideKey": "permission-rule"},
    "mcp-server": {"label": "외부 도구 (MCP)", "defaultLayer": "mcp", "guideKey": "mcp-server"},
    "hook": {"label": "가드레일 hook", "defaultLayer": "guardrails", "guideKey": "hook"},
    "policy-doc": {"label": "규칙 문서", "defaultLayer": "guardrails", "guideKey": "policy-doc"},
    "sub-agent": {"label": "에이전트 (sub-agent)", "defaultLayer": "workflow", "guideKey": "sub-agent"},
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

__all__ = ["kind_registry", "addable_kinds_by_layer", "ComponentKind", "Layer"]
