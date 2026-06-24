"""강제수준 사다리 — 프로즈(권고) < 정책문서(문서) < hook(자동 차단) 승격(순수 함수).

같은 의도를 더 강하게 집행하도록 한 단계 올린다. prose→policy-doc(텍스트 이전),
policy-doc→hook(검사 스크립트 템플릿, 사용자가 조건 완성). hook 은 최상위(승격 없음).
"""

from __future__ import annotations

import re

from .factory import gen_id
from .schema import HarnessComponent, Hook, Intent, PolicyDoc

_LEVELS = {"prose-guideline": "권고", "policy-doc": "문서", "hook": "자동 차단"}


def enforcement_level(kind: str) -> str | None:
    return _LEVELS.get(kind)


def can_promote(kind: str) -> bool:
    return kind in ("prose-guideline", "policy-doc")


def _slug(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|]+', "", s).strip()
    s = re.sub(r"\s+", "-", s)
    return s or "rule"


def promote(c: HarnessComponent) -> HarnessComponent | None:
    """한 단계 강한 강제수준 컴포넌트 생성. 이미 최상위면 None."""
    if c.kind == "prose-guideline":
        return PolicyDoc(
            id=gen_id("policy"),
            layer="guardrails",
            title=c.title,
            involvement=c.involvement,
            enabled=c.enabled,
            doc_name=f"{_slug(c.heading)}.md",
            body=c.body,
            intent=Intent(raw="강제수준 승격: 프로즈→정책문서", compiled_by="manual", confidence=1),
        )
    if c.kind == "policy-doc":
        commented = c.body.replace("\n", "\n# ")
        script = (
            "#!/usr/bin/env bash\n"
            "# 강제수준 승격: 정책문서 → hook. 아래 규칙을 검사해 위반 시 exit 2.\n"
            f"# {commented}\n"
            "input=$(cat)\n"
            "# TODO: $input(도구 입력 JSON) 을 검사하는 조건 작성\n"
            "exit 0\n"
        )
        return Hook(
            id=gen_id("hook"),
            layer="guardrails",
            title=c.title,
            involvement="manual-gate",
            enabled=c.enabled,
            event="PreToolUse",
            matcher_tool="Write|Edit",
            path_glob=None,
            action="deny",
            script_name=f"{_slug(c.doc_name.removesuffix('.md'))}.sh",
            script_body=script,
            intent=Intent(raw="강제수준 승격: 정책문서→hook", compiled_by="manual", confidence=1),
        )
    return None
