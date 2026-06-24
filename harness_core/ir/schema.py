"""하네스 정의 IR — pydantic v2.

필드명은 snake_case + camelCase alias(ADR-0002). 속성 접근은 snake_case,
직렬화/입력은 snake/camel 둘 다 허용(populate_by_name). 산출 바이트는 불변(골든 게이트).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

Layer = Literal["context", "permissions", "mcp", "guardrails", "workflow", "verification"]
Involvement = Literal["auto", "assisted", "manual-gate"]
PermissionAction = Literal["allow", "ask", "deny"]
HookEvent = Literal["PreToolUse", "PostToolUse", "SessionStart", "Stop"]

_CFG = ConfigDict(populate_by_name=True, extra="forbid")


class Intent(BaseModel):
    model_config = _CFG
    raw: str
    compiled_by: Literal["preset", "manual", "llm"] = Field(alias="compiledBy")
    confidence: float


class _Base(BaseModel):
    model_config = _CFG
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
    server_name: str = Field(alias="serverName")
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class Hook(_Base):
    kind: Literal["hook"] = "hook"
    event: HookEvent
    matcher_tool: str = Field(alias="matcherTool")
    path_glob: str | None = Field(default=None, alias="pathGlob")
    action: Literal["deny", "allow", "warn"]
    script_name: str = Field(alias="scriptName")
    script_body: str = Field(alias="scriptBody")


class PolicyDoc(_Base):
    kind: Literal["policy-doc"] = "policy-doc"
    doc_name: str = Field(alias="docName")
    body: str


class SubAgent(_Base):
    kind: Literal["sub-agent"] = "sub-agent"
    name: str
    description: str
    tools: list[str] = Field(default_factory=list)
    model: str | None = None
    system_prompt: str = Field(alias="systemPrompt")


HarnessComponent = Annotated[
    ProseGuideline | PermissionRule | McpServer | Hook | PolicyDoc | SubAgent,
    Field(discriminator="kind"),
]

ComponentKind = Literal[
    "prose-guideline", "permission-rule", "mcp-server", "hook", "policy-doc", "sub-agent"
]


class Meta(BaseModel):
    model_config = _CFG
    ir_version: str = Field(alias="irVersion")
    target_tool: Literal["claude-code"] = Field(alias="targetTool")
    preset: str
    project_name: str = Field(alias="projectName")


class HarnessIR(BaseModel):
    model_config = _CFG
    meta: Meta
    components: list[HarnessComponent]


_component_adapter: TypeAdapter[object] = TypeAdapter(HarnessComponent)


def by_kind(comps: list, kind: str) -> list:
    """특정 kind 의 component 만 추출."""
    return [c for c in comps if c.kind == kind]


def parse_component(data: dict):
    return _component_adapter.validate_python(data)


def safe_parse_component(data: dict) -> dict:
    """zod safeParse 시맨틱 — {ok, data} 또는 {ok: False, errors}."""
    try:
        return {"ok": True, "data": _component_adapter.validate_python(data)}
    except ValidationError as e:
        return {"ok": False, "errors": e.errors()}


def parse_ir(data: dict) -> HarnessIR:
    return HarnessIR.model_validate(data)
