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
    # 2-A: PowerShell·Python 인라인 실행 — 구체 패턴을 먼저 둬야 메시지가 정확해진다.
    (
        re.compile(r"(?i)(invoke-webrequest|curl|wget)[^\n]*\|\s*(iex|invoke-expression)"),
        "내려받은 내용을 곧바로 PowerShell 로 실행",
    ),
    (re.compile(r"(?i)\b(iex|invoke-expression)\b"), "PowerShell iex 로 문자열을 코드로 실행"),
    (re.compile(r"\bpython[0-9.]*\s+-c\b"), "python -c 로 인라인 코드 실행"),
]
_SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[bap]-[A-Za-z0-9-]{10,}"),
    # 2-A: 벤더 확장 — OpenAI(프로젝트/레거시)·Google·PEM 개인키.
    re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
_MCP_OVERLOAD_THRESHOLD = 5

# 2-C: POSIX 셸 shebang 판별(첫 줄만) — Windows 에서 git-bash/WSL 없으면 미실행되는 훅 표면화.
# `pwsh` 가 `sh` 로 뭉개지지 않도록 경로 구분자 뒤 토큰만 매칭한다(`\S*[/\\\s]` 뒤).
_POSIX_SHELL_SHEBANG = re.compile(r"^#!\S*[/\\\s](bash|sh|zsh)(\.exe)?\b")
# 2-B: deny 훅이 실제로 차단하려면 exit 2(PreToolUse 차단 규약)가 있어야 한다.
_EXIT_2 = re.compile(r"\bexit\s+2\b")


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
    # 2-A: MCP 실행 명령·인자도 스캔(예: --api-key 뒤 실제 키). env 는 core 규칙
    # inline-secret 이 이미 error 로 잡으므로 중복 보고를 피해 제외한다.
    if c.kind == "mcp-server":
        return [c.command, *c.args]
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

        # 2-B: '금지(deny)'로 표시됐지만 스크립트가 실제로 차단하지 않는 훅(발견 A 탐지).
        # PreToolUse 차단은 exit 2 규약이라, exit 2 가 없으면 화면의 '차단'이 산출물에서 안 지켜진다.
        if h.action == "deny" and not _EXIT_2.search(h.script_body):
            findings.append(
                {
                    "level": "warning",
                    "code": "sec-hook-no-enforce",
                    "message": f'hook "{h.title}" 은 금지로 표시됐지만 스크립트가 실제로 막지 않아요 — 차단하려면 막을 때 exit 2 로 끝내야 합니다',
                    "componentId": h.id,
                }
            )

        # 2-C: bash/sh 훅은 Windows 에 git-bash/WSL 이 없으면 조용히 미실행된다(발견 B).
        # 코어 lint 는 플랫폼을 모르므로 '이식성 주의'까지만 — 실제 이 PC 판정은 앱의 1-C precheck.
        # sec- 접두를 쓰지 않는 이유: 모든 플랫폼에서 무조건 발화하므로 성숙도 게이트에 걸면
        # macOS/Linux 에서도 Lv4 가 영구 불가가 된다(게이팅은 환경을 아는 앱 계층 책임).
        if _POSIX_SHELL_SHEBANG.match(
            (h.script_body or "").splitlines()[0] if h.script_body else ""
        ):
            findings.append(
                {
                    "level": "warning",
                    "code": "hook-portability",
                    "message": f'hook "{h.title}" 은 bash 로 작성돼 있어요 — Windows 에서는 Git Bash(또는 WSL)가 있어야 실행됩니다. 없으면 이 차단은 동작하지 않아요',
                    "componentId": h.id,
                }
            )

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

    # 2-A: 죽은 규칙 — 더 넓은 deny 에 가려 효과가 없는 allow(우선순위 deny > ask > allow).
    # 완전히 같은 패턴이 allow/deny 양쪽에 있는 경우는 core 의 permission-conflict(error)가
    # 이미 잡으므로 여기서는 제외해 중복 보고를 피한다.
    denies = [(x, parse_pattern(x.pattern)) for x in perms if x.action == "deny"]
    for a in [x for x in perms if x.action == "allow"]:
        ap = parse_pattern(a.pattern)
        for d, dp in denies:
            if d.pattern == a.pattern or dp["tool"] != ap["tool"]:
                continue
            if dp["prefix"] == "" or ap["prefix"].startswith(dp["prefix"]):
                findings.append(
                    {
                        "level": "warning",
                        "code": "sec-dead-rule",
                        "message": f'허용 "{a.pattern}" 은 더 넓은 금지 "{d.pattern}" 에 가려 효과가 없어요 — 금지가 항상 우선합니다',
                        "componentId": a.id,
                    }
                )
                break  # allow 당 1건

    mcps = by_kind(enabled, "mcp-server")
    # 2-A: MCP 실행 명령·인자의 의심 패턴(외부에서 받은 하네스의 임의 명령 실행 경로).
    for s in mcps:
        joined = " ".join([s.command, *s.args])
        for pat, what in _INJECTION_PATTERNS:
            if pat.search(joined):
                findings.append(
                    {
                        "level": "warning",
                        "code": "sec-mcp-suspicious",
                        "message": f'외부 도구 "{s.server_name}" 의 실행 명령에 의심 패턴({what})이 있어요 — 연결 전에 명령·인자를 꼭 확인하세요',
                        "componentId": s.id,
                    }
                )
                break
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
