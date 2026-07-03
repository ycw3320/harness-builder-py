"""빠른 시작(QuickStart) — 질문 3개(성향·보호·폴더)를 검증된 하네스 IR 로 컴파일 (순수).

PM8 실험: '최소 입력' 경로. 답 → IR 매핑은 전부 결정론(LLM 0회)이고, 보호 장치는
safety_first 프리셋의 검증된 시드를 복제해 쓴다(직접 조립과 같은 품질 보장).
기본값(전 보호 켬)이면 어떤 성향이든 성숙도 Lv4(검증됨)가 되도록 설계됐다 — 테스트로 고정.
"""

from __future__ import annotations

from harness_core.ir.factory import create_component, gen_id
from harness_core.ir.presets import PRESETS, safety_first_preset
from harness_core.ir.schema import HarnessComponent, HarnessIR

from .detect import DetectedProject

# 성향(1클릭) — key → (라벨, 한 줄 설명, 기반 프리셋)
PERSONAS: list[tuple[str, str, str]] = [
    ("careful", "조심조심 — 위험한 건 다 막거나 물어봐요", "safety-first"),
    ("balanced", "균형 — 기본 안전망 + 자유로운 작업", "mvp"),
    ("fast", "빠르게 — 자주 쓰는 명령은 자유 허용", "speed"),
]

# 핵심 보호(체크, 기본 전부 켬) — key → (쉬운 라벨, 개발자용 풀이=? 칩).
# 라벨은 위험 시나리오 중심 쉬운 말 — '체크=이 규칙이 하네스에 들어감'은 다이얼로그 캡션이 설명.
PROTECTIONS: list[tuple[str, str, str]] = [
    (
        "env_guard",
        "비밀키 파일(.env) 지키기 — AI가 건드리면 자동 차단",
        "hook(도구 실행 전 검사)이 .claude/hooks/ 스크립트로 생성됩니다 — .env 쓰기 시도를 exit 2 로 차단",
    ),
    (
        "rm_guard",
        "폴더 통째 삭제 막기 — 되돌릴 수 없는 삭제 금지",
        "권한 규칙 deny: Bash(rm -rf:*) — settings.json permissions 에 들어갑니다",
    ),
    (
        "push_guard",
        "강제 push 전에 물어보기 — 실수로 원격 덮어쓰기 방지",
        "권한 규칙 ask: Bash(git push --force:*) — 실행 전 매번 사용자 확인",
    ),
]
DEFAULT_PROTECTIONS = frozenset(k for k, *_ in PROTECTIONS)


def _is_env_hook(c: HarnessComponent) -> bool:
    return c.kind == "hook" and bool(c.path_glob) and ".env" in c.path_glob


def _is_rm_deny(c: HarnessComponent) -> bool:
    return c.kind == "permission-rule" and c.action == "deny" and "rm -rf" in c.pattern


def _is_push_ask(c: HarnessComponent) -> bool:
    return c.kind == "permission-rule" and c.action == "ask" and "push --force" in c.pattern


_PROTECTION_PREDICATES = {
    "env_guard": _is_env_hook,
    "rm_guard": _is_rm_deny,
    "push_guard": _is_push_ask,
}


def _protection_templates(project_name: str) -> dict[str, HarnessComponent]:
    """보호 장치의 원본 시드 — safety_first 프리셋에서 추출(검증된 필드값 재사용)."""
    seed = safety_first_preset(project_name)
    out: dict[str, HarnessComponent] = {}
    for key, pred in _PROTECTION_PREDICATES.items():
        for c in seed.components:
            if pred(c):
                out[key] = c
                break
    return out


def build_quick_ir(
    project_name: str,
    persona: str,
    protections: frozenset[str] | set[str] = DEFAULT_PROTECTIONS,
    detected: DetectedProject | None = None,
) -> HarnessIR:
    """답 3개 → 하네스 IR. 성향 프리셋 기반 + 보호 ensure/remove + 감지 결과 프리필."""
    preset_name = next((p for k, _, p in PERSONAS if k == persona), "safety-first")
    base = PRESETS[preset_name](project_name)
    comps: list[HarnessComponent] = []

    # 1) 보호 remove: 선택 해제된 보호 장치는 프리셋에 있어도 제외
    for c in base.components:
        drop = any(
            key not in protections and pred(c) for key, pred in _PROTECTION_PREDICATES.items()
        )
        if not drop:
            comps.append(c)

    # 2) 보호 ensure: 선택됐는데 없으면 safety_first 시드 복제(id 재부여)
    templates = _protection_templates(project_name)
    for key, pred in _PROTECTION_PREDICATES.items():
        if key in protections and not any(pred(c) for c in comps) and key in templates:
            t = templates[key]
            comps.append(t.model_copy(update={"id": gen_id(t.kind)}))

    # 3) 감지 프리필: 프로젝트 prose 본문을 스택·명령으로 채움(없으면 생성)
    if detected is not None:
        body = detected.prose_body()
        idx = next(
            (
                i
                for i, c in enumerate(comps)
                if c.kind == "prose-guideline" and c.scope == "project"
            ),
            None,
        )
        if idx is not None:
            comps[idx] = comps[idx].model_copy(update={"body": body})
        else:
            prose = create_component("prose-guideline", "context").model_copy(
                update={
                    "scope": "project",
                    "title": "프로젝트 개요",
                    "heading": "프로젝트 개요",
                    "body": body,
                }
            )
            comps.append(prose)

    return HarnessIR(meta=base.meta, components=comps)
