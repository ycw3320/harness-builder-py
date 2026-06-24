"""LLM 구조화 출력용 kind별 content 모델 — 편집 필드만(id/layer/involvement/enabled 제외).

`messages.parse(output_format=...)` 스키마로 사용. structured-outputs 제약상 열린 dict 금지 →
env 는 (name,value) 쌍 리스트로 받아 앱에서 dict 로 변환. extra=forbid(additionalProperties:false).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

_CFG = ConfigDict(extra="forbid")


class ProseContent(BaseModel):
    model_config = _CFG
    scope: Literal["global", "project"]
    heading: str
    body: str


class PermissionContent(BaseModel):
    model_config = _CFG
    action: Literal["allow", "ask", "deny"]
    pattern: str


class EnvVar(BaseModel):
    model_config = _CFG
    name: str
    value: str  # 반드시 ${VAR} 플레이스홀더


class McpContent(BaseModel):
    model_config = _CFG
    server_name: str
    command: str
    args: list[str] = []
    env: list[EnvVar] = []


class HookContent(BaseModel):
    model_config = _CFG
    event: Literal["PreToolUse", "PostToolUse", "SessionStart", "Stop"]
    matcher_tool: str
    path_glob: str | None = None
    action: Literal["deny", "allow", "warn"]
    script_name: str
    script_body: str


class PolicyContent(BaseModel):
    model_config = _CFG
    doc_name: str
    body: str


class AgentContent(BaseModel):
    model_config = _CFG
    name: str
    description: str
    tools: list[str] = []
    model: str | None = None
    system_prompt: str


CONTENT_MODELS: dict[str, type[BaseModel]] = {
    "prose-guideline": ProseContent,
    "permission-rule": PermissionContent,
    "mcp-server": McpContent,
    "hook": HookContent,
    "policy-doc": PolicyContent,
    "sub-agent": AgentContent,
}


def to_patch(kind: str, data: dict) -> dict:
    """content 모델 dump → state.patch 용 필드 dict. mcp env 쌍 리스트는 dict 로 변환."""
    out = dict(data)
    if kind == "mcp-server":
        out["env"] = {p["name"]: p["value"] for p in out.get("env", []) if p.get("name")}
    return out
