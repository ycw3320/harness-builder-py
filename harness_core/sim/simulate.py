"""결정론 시뮬레이터 (TS simulate.ts 포팅) — LLM 0회. hook→deny→ask→allow 우선순위."""
from __future__ import annotations

import re

from ..ir.schema import HarnessIR, by_kind
from ..lint.lint import parse_pattern


def glob_to_regexp(glob: str) -> re.Pattern:
    """glob → 정규식 (`**` 경로 구분 포함, `*` 미포함)."""
    escaped = re.sub(r"([.+^${}()|\[\]\\])", r"\\\1", glob)
    body = escaped.replace("**/", "(?:.*/)?").replace("**", ".*").replace("*", "[^/]*")
    return re.compile("^" + body + "$")


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
        if not re.search(h.matcherTool, action["tool"]):
            continue
        if h.pathGlob:
            path = action.get("path")
            if not path or not glob_to_regexp(h.pathGlob).search(path):
                continue
        suffix = f" · {h.pathGlob}" if h.pathGlob else ""
        reasons.append(f'hook "{h.title}" 의 matcher({h.matcherTool}{suffix})에 걸려 차단됨')
        return {"action": action, "outcome": "blocked-by-hook", "reasons": reasons, "blockedBy": h.id}

    # 2. permission deny / ask
    perms = by_kind(enabled, "permission-rule")
    for p in [x for x in perms if x.action == "deny"]:
        if _permission_matches(p.pattern, action):
            reasons.append(f'권한 deny 규칙 "{p.pattern}" 에 매칭되어 차단됨')
            return {"action": action, "outcome": "blocked-by-permission", "reasons": reasons, "blockedBy": p.id}
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
