"""결정론 시뮬레이터 — LLM 0회. hook→deny→ask→allow 우선순위."""

from __future__ import annotations

import re

from ..ir.schema import HarnessIR, by_kind
from ..lint.lint import parse_pattern

_GLOB_ESCAPE = re.compile(r"([.+^${}()|\[\]\\])")
# 치환 중간 자리표시자 — `**/`→`(.*/)?` 를 먼저 넣고 그 뒤 `*`→`[^/]*` 를 돌리면 방금 삽입한
# `.*` 의 `*` 까지 오염돼 `**` 가 "정확히 한 단계"로 축소됐다(3-A 실측 결함: sub/dir/.env 가
# 시뮬=통과 / 실제 bash 훅=차단). 자리표시자를 거쳐 오염을 차단한다.
_PH_ANY_DIRS = "\x00ANYD\x00"
_PH_ANY = "\x00ANY\x00"


def glob_to_pattern(glob: str) -> str:
    """glob → 정규식 **문자열**. 시뮬(Python re)과 생성 스크립트(grep -E)가 공유하는 단일 소스.

    비캡처 그룹 `(?:...)` 는 POSIX ERE 에 없어 grep -E 에서 매칭이 실패한다 → 양쪽 모두에서
    동일하게 동작하는 평범한 그룹 `(...)` 로 생성한다(3-A 단일 생성기 계약).
    """
    escaped = _GLOB_ESCAPE.sub(r"\\\1", glob)
    body = escaped.replace("**/", _PH_ANY_DIRS).replace("**", _PH_ANY)
    body = body.replace("*", "[^/]*")
    body = body.replace(_PH_ANY_DIRS, "(.*/)?").replace(_PH_ANY, ".*")
    return "^" + body + "$"


def glob_to_regexp(glob: str) -> re.Pattern:
    """glob → 정규식 (`**` 경로 구분 포함, `*` 미포함)."""
    return re.compile(glob_to_pattern(glob))


def _permission_matches(pattern: str, action: dict) -> bool:
    pp = parse_pattern(pattern)
    if pp["tool"] != action["tool"]:
        return False
    if pp["prefix"] == "":
        return True
    subject = action.get("command") or action.get("path") or ""
    return subject.startswith(pp["prefix"])


def simulate(ir: HarnessIR, action: dict) -> dict:
    enabled = [c for c in ir.components if c.enabled]
    reasons: list[str] = []

    # 1. hook (PreToolUse, deny)
    for h in by_kind(enabled, "hook"):
        if h.event != "PreToolUse" or h.action != "deny":
            continue
        if not re.search(h.matcher_tool, action["tool"]):
            continue
        if h.path_glob:
            path = action.get("path")
            if not path or not glob_to_regexp(h.path_glob).search(path):
                continue
        suffix = f" · {h.path_glob}" if h.path_glob else ""
        reasons.append(f'hook "{h.title}" 의 matcher({h.matcher_tool}{suffix})에 걸려 차단됨')
        return {
            "action": action,
            "outcome": "blocked-by-hook",
            "reasons": reasons,
            "blockedBy": h.id,
        }

    # 2. permission deny / ask
    perms = by_kind(enabled, "permission-rule")
    for p in [x for x in perms if x.action == "deny"]:
        if _permission_matches(p.pattern, action):
            reasons.append(f'권한 deny 규칙 "{p.pattern}" 에 매칭되어 차단됨')
            return {
                "action": action,
                "outcome": "blocked-by-permission",
                "reasons": reasons,
                "blockedBy": p.id,
            }
    for p in [x for x in perms if x.action == "ask"]:
        if _permission_matches(p.pattern, action):
            reasons.append(f'권한 ask 규칙 "{p.pattern}" 에 매칭되어 사용자 확인 필요')
            return {"action": action, "outcome": "ask", "reasons": reasons, "blockedBy": p.id}

    reasons.append("매칭되는 차단/확인 규칙이 없어 통과됨")
    return {"action": action, "outcome": "allowed", "reasons": reasons}


default_scenarios: list[dict] = [
    {"tool": "Write", "path": ".env", "label": ".env 파일에 쓰기 시도"},
    {"tool": "Bash", "command": "git push --force origin main", "label": "강제 push 시도"},
    {"tool": "Bash", "command": "npm run build", "label": "정상 빌드 실행"},
]
