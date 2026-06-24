"""하네스 정의 IR — pydantic v2 (TS zod 스키마 포팅).

component 6종 discriminated union + 공통 필드(involvement/enabled/intent).
필드명은 TS/JSON 계약과 동일하게 camelCase 유지(상호운용·골든 동치).
"""
from __future__ import annotations

from typing import Annotated, Literal, TypeVar, Union

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

Layer = Literal["context", "permissions", "mcp", "guardrails", "workflow", "verification"]
Involvement = Literal["auto", "assisted", "manual-gate"]
PermissionAction = Literal["allow", "ask", "deny"]
HookEvent = Literal["PreToolUse", "PostToolUse", "SessionStart", "Stop"]


class Intent(BaseModel):
    raw: str
    compiledBy: Literal["preset", "manual", "llm"]
    confidence: float


class _Base(BaseModel):
    id: str
    layer: Layer
    title: str
    involvement: Involvement
    enabled: bool
    intent: Intent | None = None


class ProseGuideline(_Base):
    kind: Literal["prose-guideline"] = "prose-guideline"
    scope: Literal["global", "project"]
    heading: str
    body: str


class PermissionRule(_Base):
    kind: Literal["permission-rule"] = "permission-rule"
    action: PermissionAction
    pattern: str


class McpServer(_Base):
    kind: Literal["mcp-server"] = "mcp-server"
    serverName: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class Hook(_Base):
    kind: Literal["hook"] = "hook"
    event: HookEvent
    matcherTool: str
    pathGlob: str | None = None
    action: Literal["deny", "allow", "warn"]
    scriptName: str
    scriptBody: str


class PolicyDoc(_Base):
    kind: Literal["policy-doc"] = "policy-doc"
    docName: str
    body: str


class SubAgent(_Base):
    kind: Literal["sub-agent"] = "sub-agent"
    name: str
    description: str
    tools: list[str] = Field(default_factory=list)
    model: str | None = None
    systemPrompt: str


HarnessComponent = Annotated[
    Union[ProseGuideline, PermissionRule, McpServer, Hook, PolicyDoc, SubAgent],
    Field(discriminator="kind"),
]

ComponentKind = Literal[
    "prose-guideline", "permission-rule", "mcp-server", "hook", "policy-doc", "sub-agent"
]


class Meta(BaseModel):
    irVersion: str
    targetTool: Literal["claude-code"]
    preset: str
    projectName: str


class HarnessIR(BaseModel):
    meta: Meta
    components: list[HarnessComponent]


_component_adapter: TypeAdapter[object] = TypeAdapter(HarnessComponent)
_T = TypeVar("_T")


def by_kind(comps: list, kind: str) -> list:
    """특정 kind 의 component 만 추출 (TS byKind 직역)."""
    return [c for c in comps if c.kind == kind]


def parse_component(data: dict):
    """검증 후 component 반환 (실패 시 ValidationError)."""
    return _component_adapter.validate_python(data)


def safe_parse_component(data: dict) -> dict:
    """zod safeParse 시맨틱 재현 — {ok, data} 또는 {ok: False, errors}."""
    try:
        return {"ok": True, "data": _component_adapter.validate_python(data)}
    except ValidationError as e:
        return {"ok": False, "errors": e.errors()}


def parse_ir(data: dict) -> HarnessIR:
    return HarnessIR.model_validate(data)
