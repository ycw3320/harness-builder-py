"""역import — 파일트리(path→content) → HarnessIR. export_ir 의 역방향(순수 함수).

best-effort: CC settings 에 없는 IR 개념(hook 의 action/path_glob)은 복원 불가 → 기본값.
디스크 IO 없음(harness_fs.importer 가 디스크→dict 후 호출) — 라운드트립 테스트 가능.
"""

from __future__ import annotations

import json
import re

from ..ir.factory import gen_id
from ..ir.schema import (
    HarnessComponent,
    HarnessIR,
    Hook,
    Intent,
    McpServer,
    Meta,
    PermissionRule,
    PolicyDoc,
    ProseGuideline,
    SubAgent,
)

_INTENT = Intent(raw="역import", compiled_by="manual", confidence=1)


def _prose(scope: str, heading: str, body: str) -> ProseGuideline:
    return ProseGuideline(
        id=gen_id("prose"),
        layer="context",
        title=heading or "지침",
        involvement="assisted",
        enabled=True,
        scope=scope,  # type: ignore[arg-type]
        heading=heading,
        body=body,
        intent=_INTENT,
    )


def _parse_claude_md(content: str, scope: str) -> list[ProseGuideline]:
    content = re.sub(r"(?s)^<!--.*?-->\s*", "", content)  # 전역 안내 주석 제거
    content = re.sub(r"(?m)^# .*\n?", "", content, count=1)  # 제목 줄 제거
    out: list[ProseGuideline] = []
    for part in re.split(r"(?m)^## ", content):
        part = part.strip("\n")
        if not part:
            continue
        seg = part.split("\n", 1)
        heading = seg[0].strip()
        body = seg[1].strip("\n") if len(seg) > 1 else ""
        out.append(_prose(scope, heading, body))
    return out


def _import_settings(text: str, files: dict[str, str]) -> list[HarnessComponent]:
    out: list[HarnessComponent] = []
    data = json.loads(text)
    for action in ("allow", "ask", "deny"):
        for pattern in data.get("permissions", {}).get(action, []):
            out.append(
                PermissionRule(
                    id=gen_id("perm"),
                    layer="permissions",
                    title=pattern,
                    involvement="manual-gate",
                    enabled=True,
                    action=action,  # type: ignore[arg-type]
                    pattern=pattern,
                    intent=_INTENT,
                )
            )
    for event, entries in data.get("hooks", {}).items():
        for entry in entries:
            matcher = entry.get("matcher", "")
            for hk in entry.get("hooks", []):
                name = hk.get("command", "").rsplit("/", 1)[-1] or "hook.sh"
                body = files.get(f".claude/hooks/{name}", "").rstrip("\n")
                out.append(
                    Hook(
                        id=gen_id("hook"),
                        layer="guardrails",
                        title=name,
                        involvement="manual-gate",
                        enabled=True,
                        event=event,  # type: ignore[arg-type]
                        matcher_tool=matcher,
                        path_glob=None,  # settings.json 에 미보존
                        action="deny",  # IR 전용 개념 — 복원 불가, 기본값
                        script_name=name,
                        script_body=body,
                        intent=_INTENT,
                    )
                )
    return out


def _import_agent(content: str) -> SubAgent:
    m = re.match(r"(?s)^---\n(.*?)\n---\n?(.*)$", content)
    fm_text, body = (m.group(1), m.group(2)) if m else ("", content)
    fm: dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    tools = [t.strip() for t in fm.get("tools", "").split(",") if t.strip()]
    return SubAgent(
        id=gen_id("agent"),
        layer="workflow",
        title=fm.get("name", "agent"),
        involvement="assisted",
        enabled=True,
        name=fm.get("name", "agent"),
        description=fm.get("description", ""),
        tools=tools,
        model=fm.get("model") or None,
        system_prompt=body.strip("\n"),
        intent=_INTENT,
    )


def import_ir(files: dict[str, str], project_name: str = "imported-project") -> HarnessIR:
    """파일트리(path→content) → HarnessIR. 인식 못 한 파일은 무시(best-effort)."""
    components: list[HarnessComponent] = []

    if "CLAUDE.md" in files:
        components += _parse_claude_md(files["CLAUDE.md"], "project")
    g = files.get("_global/CLAUDE.md")
    if g:
        components += _parse_claude_md(g, "global")

    if ".claude/settings.json" in files:
        components += _import_settings(files[".claude/settings.json"], files)

    for path, content in files.items():
        if path.startswith(".claude/rules/") and path.endswith(".md"):
            name = path.rsplit("/", 1)[-1]
            components.append(
                PolicyDoc(
                    id=gen_id("policy"),
                    layer="guardrails",
                    title=name,
                    involvement="assisted",
                    enabled=True,
                    doc_name=name,
                    body=content.rstrip("\n"),
                    intent=_INTENT,
                )
            )

    if ".mcp.json" in files:
        for name, cfg in json.loads(files[".mcp.json"]).get("mcpServers", {}).items():
            components.append(
                McpServer(
                    id=gen_id("mcp"),
                    layer="mcp",
                    title=name,
                    involvement="assisted",
                    enabled=True,
                    server_name=name,
                    command=cfg.get("command", ""),
                    args=list(cfg.get("args", [])),
                    env=dict(cfg.get("env", {})),
                    intent=_INTENT,
                )
            )

    for path, content in files.items():
        if path.startswith(".claude/agents/") and path.endswith(".md"):
            components.append(_import_agent(content))

    return HarnessIR(
        meta=Meta(
            ir_version="1.0",
            target_tool="claude-code",
            preset="imported",
            project_name=project_name,
        ),
        components=components,
    )
