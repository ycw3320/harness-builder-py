"""IR → 가상 파일트리 (TS exportIR.ts 포팅). enabled=false 제외. 순수 함수.

정렬: TS 는 localeCompare(로케일 의존) → Python 은 결정론 코드포인트 sort.
골든 게이트는 '경로 집합 + 경로별 내용 바이트 동일'로 검증(순서 무관).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..ir.schema import HarnessIR, by_kind

_ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


@dataclass
class VirtualFile:
    path: str
    content: str


def _dedupe_sort(xs: list[str]) -> list[str]:
    return sorted(set(xs))


def _build_claude_md(title: str, sections: list) -> str:
    head = f"# {title}\n"
    blocks = [f"## {s.heading}\n\n{s.body}\n" for s in sections]
    return "\n".join([head, *blocks])


def _ensure_nl(s: str) -> str:
    return s if s.endswith("\n") else s + "\n"


def export_ir(ir: HarnessIR) -> list[VirtualFile]:
    enabled = [c for c in ir.components if c.enabled]
    files: list[VirtualFile] = []
    referenced_env: set[str] = set()

    # 1. prose-guideline → CLAUDE.md / _global/CLAUDE.md
    prose = by_kind(enabled, "prose-guideline")
    project_prose = [c for c in prose if c.scope == "project"]
    global_prose = [c for c in prose if c.scope == "global"]
    if project_prose:
        files.append(VirtualFile("CLAUDE.md", _build_claude_md(f"{ir.meta.projectName} — 프로젝트 지침", project_prose)))
    if global_prose:
        files.append(VirtualFile(
            "_global/CLAUDE.md",
            "<!-- 이 파일 내용을 ~/.claude/CLAUDE.md 에 병합하세요 (전역 지침) -->\n\n"
            + _build_claude_md("전역 지침", global_prose),
        ))

    # 2. settings.json — permissions + hooks
    settings: dict = {}
    perms = by_kind(enabled, "permission-rule")
    if perms:
        grouped: dict[str, list[str]] = {}
        for p in perms:
            grouped.setdefault(p.action, []).append(p.pattern)
        permissions: dict[str, list[str]] = {}
        for action in ("allow", "ask", "deny"):
            if grouped.get(action):
                permissions[action] = _dedupe_sort(grouped[action])
        settings["permissions"] = permissions

    hooks = by_kind(enabled, "hook")
    if hooks:
        hook_map: dict[str, list] = {}
        for h in hooks:
            command = f".claude/hooks/{h.scriptName}"
            hook_map.setdefault(h.event, []).append(
                {"matcher": h.matcherTool, "hooks": [{"type": "command", "command": command}]}
            )
            files.append(VirtualFile(command, _ensure_nl(h.scriptBody)))
        settings["hooks"] = hook_map

    if settings.get("permissions") or settings.get("hooks"):
        files.append(VirtualFile(".claude/settings.json", json.dumps(settings, indent=2, ensure_ascii=False) + "\n"))

    # 3. policy-doc → .claude/rules/*
    for doc in by_kind(enabled, "policy-doc"):
        files.append(VirtualFile(f".claude/rules/{doc.docName}", _ensure_nl(doc.body)))

    # 4. mcp-server → .mcp.json
    mcp = by_kind(enabled, "mcp-server")
    if mcp:
        mcp_servers: dict = {}
        for s in mcp:
            mcp_servers[s.serverName] = {"command": s.command, "args": s.args, "env": s.env}
            for v in s.env.values():
                referenced_env.update(_ENV_RE.findall(v))
        files.append(VirtualFile(".mcp.json", json.dumps({"mcpServers": mcp_servers}, indent=2, ensure_ascii=False) + "\n"))

    # 5. sub-agent → .claude/agents/*.md
    for a in by_kind(enabled, "sub-agent"):
        fm = "\n".join([
            "---",
            f"name: {a.name}",
            f"description: {a.description}",
            f"tools: {', '.join(a.tools)}",
            *([f"model: {a.model}"] if a.model else []),
            "---",
            "",
            a.systemPrompt,
        ])
        files.append(VirtualFile(f".claude/agents/{a.name}.md", _ensure_nl(fm)))

    # 6. .env.example
    if referenced_env:
        lines = [f"{n}=" for n in sorted(referenced_env)]
        files.append(VirtualFile(".env.example", "\n".join(lines) + "\n"))

    return sorted(files, key=lambda f: f.path)
