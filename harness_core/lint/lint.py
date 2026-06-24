"""정합성 검사 (TS lint.ts 포팅) — error=Export 차단, warning=경고."""
from __future__ import annotations

import re

from ..ir.schema import HarnessIR, by_kind

_PLACEHOLDER = re.compile(r"^\$\{[A-Z0-9_]+\}$")


def parse_pattern(pattern: str) -> dict:
    """권한 패턴 "Tool(arg:*)" → {tool, prefix}."""
    m = re.match(r"^([^(]+)(?:\((.*)\))?$", pattern)
    tool = (m.group(1) if m else pattern).strip()
    inside = m.group(2) if (m and m.group(2)) else ""
    prefix = re.sub(r":?\*$", "", inside).strip()
    return {"tool": tool, "prefix": prefix}


def lint_ir(ir: HarnessIR) -> list[dict]:
    findings: list[dict] = []
    enabled = [c for c in ir.components if c.enabled]

    # 1. 중복 id
    seen: set[str] = set()
    for c in ir.components:
        if c.id in seen:
            findings.append({"level": "error", "code": "duplicate-id",
                             "message": f"중복된 component id: {c.id}", "componentId": c.id})
        seen.add(c.id)

    # 2. hook 스크립트 본문 누락
    for h in by_kind(enabled, "hook"):
        if h.scriptBody.strip() == "":
            findings.append({"level": "error", "code": "hook-missing-script",
                             "message": f'hook "{h.title}" 의 스크립트 본문이 비어 있습니다', "componentId": h.id})

    # 3. 권한 allow ↔ deny 동일 패턴 모순
    perms = by_kind(enabled, "permission-rule")
    allow_patterns = {p.pattern for p in perms if p.action == "allow"}
    for p in [x for x in perms if x.action == "deny"]:
        if p.pattern in allow_patterns:
            findings.append({"level": "error", "code": "permission-conflict",
                             "message": f"같은 패턴이 allow 와 deny 에 동시 존재: {p.pattern}", "componentId": p.id})

    # 4. sub-agent 가 요구하는 도구가 전면 deny
    blanket_denied = {
        parse_pattern(p.pattern)["tool"]
        for p in perms
        if p.action == "deny" and parse_pattern(p.pattern)["prefix"] == ""
    }
    for a in by_kind(enabled, "sub-agent"):
        for tool in a.tools:
            if tool in blanket_denied:
                findings.append({"level": "error", "code": "agent-tool-denied",
                                 "message": f'sub-agent "{a.name}" 가 요구하는 도구 {tool} 가 전면 deny 됨', "componentId": a.id})

    # 5. mcp env 인라인 시크릿
    for s in by_kind(enabled, "mcp-server"):
        for key, value in s.env.items():
            if not _PLACEHOLDER.match(value):
                findings.append({"level": "error", "code": "inline-secret",
                                 "message": f"mcp \"{s.serverName}\" 의 env {key} 는 ${{VAR}} 플레이스홀더여야 합니다", "componentId": s.id})

    # 6. 빈 하네스 (경고)
    if len(enabled) == 0:
        findings.append({"level": "warning", "code": "empty-harness", "message": "활성화된 구성요소가 없습니다"})

    # 7. 낮은 confidence (경고)
    for c in enabled:
        if c.intent and c.intent.confidence < 0.6:
            findings.append({"level": "warning", "code": "low-confidence",
                             "message": f'"{c.title}" 의 의도 해석 신뢰도가 낮습니다 (검토 권장)', "componentId": c.id})

    return findings


def has_errors(findings: list[dict]) -> bool:
    return any(f["level"] == "error" for f in findings)
