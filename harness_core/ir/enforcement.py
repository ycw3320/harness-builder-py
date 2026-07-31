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
        # 3-A: 승격만으로는 '무엇을 막을지'를 알 수 없어 여기서 진짜 차단을 만들 수 없다.
        # 가짜 차단(무조건 exit 2)은 워크플로를 망가뜨리므로 만들지 않는다 — 대신 실제 차단으로
        # 가는 길을 스크립트 안에 적는다. 경로 조건(path_glob)만 채우면 버클이 exit-2 가드를
        # 자동 생성한다(hook_codegen). 미완 상태는 lint `sec-hook-no-enforce` 가 계속 경고하고
        # 성숙도 Lv4 도 보류되므로, 이 스텁이 '거짓 안전'으로 남지 않는다.
        script = (
            "#!/usr/bin/env bash\n"
            "# 강제수준 승격: 정책문서 → hook. 아직 아무것도 막지 않는 '미완성' 상태입니다.\n"
            "# 실제로 막으려면 둘 중 하나를 하세요\n"
            "#  (1) 이 hook 의 '경로 조건'을 채우면 버클이 차단 코드를 자동으로 넣어줍니다(권장)\n"
            "#  (2) 아래에 직접 조건을 쓰고, 막을 때 exit 2 로 끝내세요\n"
            f"# {commented}\n"
            "input=$(cat)\n"
            "# 예) case \"$input\" in *비밀*) echo '차단 사유' >&2; exit 2;; esac\n"
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
