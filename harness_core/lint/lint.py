"""정합성 검사 — error=Export 차단, warning=경고.

PM7-S3: rulesets opt-in — 기본 ("core",) 호출은 기존과 바이트 동일(frozen 골든 보호),
("core","security") 로 실행 전 보안 검증(전부 warning — export 차단 없음)을 추가한다.
"""

from __future__ import annotations

import re

from ..ir.schema import HarnessIR, by_kind

_PLACEHOLDER = re.compile(r"^\$\{[A-Z0-9_]+\}$")

# 보안 룰셋 데이터 — 결정론 정규식(LLM 0회). 문구는 2단 톤(쉬운 말 + 부가).
_DANGEROUS_ALLOW_FRAGMENTS = ("rm -rf", "push --force", "sudo ", "del /", "format ")
_INJECTION_PATTERNS = [
    (re.compile(r"curl[^\n]*\|\s*(ba)?sh"), "curl 결과를 곧바로 셸로 실행"),
    (re.compile(r"wget[^\n]*\|\s*(ba)?sh"), "wget 결과를 곧바로 셸로 실행"),
    (re.compile(r"eval\s+[\"']?\$"), "변수 내용을 eval 로 실행"),
    (re.compile(r"base64\s+(-d|--decode)"), "base64 로 숨긴 내용을 해독"),
]
_SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[bap]-[A-Za-z0-9-]{10,}"),
]
_MCP_OVERLOAD_THRESHOLD = 5


def parse_pattern(pattern: str) -> dict:
    """권한 패턴 "Tool(arg:*)" → {tool, prefix}."""
    m = re.match(r"^([^(]+)(?:\((.*)\))?$", pattern)
    tool = (m.group(1) if m else pattern).strip()
    inside = m.group(2) if (m and m.group(2)) else ""
    prefix = re.sub(r":?\*$", "", inside).strip()
    return {"tool": tool, "prefix": prefix}


def _text_fields(c) -> list[str]:
    """kind별 시크릿 스캔 대상 자유 텍스트 필드."""
    if c.kind == "prose-guideline":
        return [c.heading, c.body]
    if c.kind == "policy-doc":
        return [c.body]
    if c.kind == "sub-agent":
        return [c.description, c.system_prompt]
    if c.kind == "hook":
        return [c.script_body]
    return []


def _security_findings(enabled: list) -> list[dict]:
    """실행 전 보안 검증(ECC 반영 잔여 — 해자 강화). 전부 warning: export 를 막지 않는다."""
    findings: list[dict] = []
    perms = by_kind(enabled, "permission-rule")

    for p in [x for x in perms if x.action == "allow"]:
        pp = parse_pattern(p.pattern)
        if pp["prefix"] == "":
            findings.append(
                {
                    "level": "warning",
                    "code": "sec-broad-allow",
                    "message": f'권한 "{p.pattern}" 는 {pp["tool"]} 전체를 허용해요 — 위험한 하위 명령까지 자유 실행됩니다. 범위를 좁히세요(예: {pp["tool"]}(명령:*))',
                    "componentId": p.id,
                }
            )
        elif any(frag in pp["prefix"] for frag in _DANGEROUS_ALLOW_FRAGMENTS):
            findings.append(
                {
                    "level": "warning",
                    "code": "sec-dangerous-allow",
                    "message": f"위험한 명령이 허용(allow)돼 있어요: {p.pattern} — 질문(ask)이나 금지(deny)를 권장합니다",
                    "componentId": p.id,
                }
            )

    for h in by_kind(enabled, "hook"):
        for pat, what in _INJECTION_PATTERNS:
            if pat.search(h.script_body):
                findings.append(
                    {
                        "level": "warning",
                        "code": "sec-hook-injection",
                        "message": f'hook "{h.title}" 스크립트에 의심 패턴({what})이 있어요 — 외부에서 받은 하네스라면 본문을 꼭 확인하세요(스크립트는 실행 코드)',
                        "componentId": h.id,
                    }
                )
                break  # hook 당 1건

    for c in enabled:
        for text in _text_fields(c):
            if any(p.search(text) for p in _SECRET_PATTERNS):
                findings.append(
                    {
                        "level": "warning",
                        "code": "sec-secret-literal",
                        "message": f'"{c.title}" 에 실제 비밀키로 보이는 문자열이 있어요 — 파일에 그대로 저장·공유됩니다. ${{VAR}} 플레이스홀더로 바꾸세요',
                        "componentId": c.id,
                    }
                )
                break

    mcps = by_kind(enabled, "mcp-server")
    if len(mcps) > _MCP_OVERLOAD_THRESHOLD:
        findings.append(
            {
                "level": "warning",
                "code": "sec-mcp-overload",
                "message": f"외부 도구(MCP)가 {len(mcps)}개예요 — 필요한 것만 연결하세요(토큰 비용·공격면 증가)",
            }
        )
    return findings


def lint_ir(ir: HarnessIR, rulesets: tuple[str, ...] = ("core",)) -> list[dict]:
    findings: list[dict] = []
    enabled = [c for c in ir.components if c.enabled]
    if "security" in rulesets:
        findings.extend(_security_findings(enabled))
    if "core" not in rulesets:
        return findings

    # 1. 중복 id
    seen: set[str] = set()
    for c in ir.components:
        if c.id in seen:
            findings.append(
                {
                    "level": "error",
                    "code": "duplicate-id",
                    "message": f"중복된 component id: {c.id}",
                    "componentId": c.id,
                }
            )
        seen.add(c.id)

    # 2. hook 스크립트 본문 누락
    for h in by_kind(enabled, "hook"):
        if h.script_body.strip() == "":
            findings.append(
                {
                    "level": "error",
                    "code": "hook-missing-script",
                    "message": f'hook "{h.title}" 의 스크립트 본문이 비어 있습니다',
                    "componentId": h.id,
                }
            )

    # 3. 권한 allow ↔ deny 동일 패턴 모순
    perms = by_kind(enabled, "permission-rule")
    allow_patterns = {p.pattern for p in perms if p.action == "allow"}
    for p in [x for x in perms if x.action == "deny"]:
        if p.pattern in allow_patterns:
            findings.append(
                {
                    "level": "error",
                    "code": "permission-conflict",
                    "message": f"같은 패턴이 allow 와 deny 에 동시 존재: {p.pattern}",
                    "componentId": p.id,
                }
            )

    # 4. sub-agent 가 요구하는 도구가 전면 deny
    blanket_denied = {
        parse_pattern(p.pattern)["tool"]
        for p in perms
        if p.action == "deny" and parse_pattern(p.pattern)["prefix"] == ""
    }
    for a in by_kind(enabled, "sub-agent"):
        for tool in a.tools:
            if tool in blanket_denied:
                findings.append(
                    {
                        "level": "error",
                        "code": "agent-tool-denied",
                        "message": f'sub-agent "{a.name}" 가 요구하는 도구 {tool} 가 전면 deny 됨',
                        "componentId": a.id,
                    }
                )

    # 5. mcp env 인라인 시크릿
    for s in by_kind(enabled, "mcp-server"):
        for key, value in s.env.items():
            if not _PLACEHOLDER.match(value):
                findings.append(
                    {
                        "level": "error",
                        "code": "inline-secret",
                        "message": f'mcp "{s.server_name}" 의 env {key} 는 ${{VAR}} 플레이스홀더여야 합니다',
                        "componentId": s.id,
                    }
                )

    # 6. 빈 하네스 (경고)
    if len(enabled) == 0:
        findings.append(
            {"level": "warning", "code": "empty-harness", "message": "활성화된 구성요소가 없습니다"}
        )

    # 7. 낮은 confidence (경고)
    for c in enabled:
        if c.intent and c.intent.confidence < 0.6:
            findings.append(
                {
                    "level": "warning",
                    "code": "low-confidence",
                    "message": f'"{c.title}" 의 의도 해석 신뢰도가 낮습니다 (검토 권장)',
                    "componentId": c.id,
                }
            )

    return findings


def has_errors(findings: list[dict]) -> bool:
    return any(f["level"] == "error" for f in findings)
