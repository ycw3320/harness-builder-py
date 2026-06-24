"""표시용 view-model — 상태·코어에서 화면 데이터를 파생 (프레임워크 무의존).

두 셸(Flet/Qt)이 동일하게 소비한다 → 위젯 배선만 갈리고 로직은 공유(M6 LOC 공정).
PM3-B: 전 6계층 interactive, kind별 field_specs(데이터 구동 폼), 행별 필드 가이드.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from harness_core.export.assemble_project import assemble_project
from harness_core.lint.lint import lint_ir
from harness_core.sim.simulate import default_scenarios, simulate

from .guides import guidance_for, involvement_meta, layer_intros, layer_meta, layer_order
from .state import BuilderState

# 결정방식(involvement) 콤보 옵션 — (라벨, 키)
INVOLVEMENT_OPTIONS = [(meta["label"], key) for key, meta in involvement_meta.items()]


@dataclass(frozen=True)
class NavItemVM:
    layer: str
    label: str
    hint: str
    interactive: bool  # 클릭 가능 여부(PM3-B: 전 계층 True)
    selected: bool
    count: int  # enabled component 수
    dot_color: str  # 내용 있음(녹)/없음(회)


@dataclass(frozen=True)
class FieldSpec:
    """kind별 편집 필드 1개 — 위젯 종류로 데이터 구동 렌더(서브클래스 6종 회피)."""

    name: str  # 스키마 필드명(snake_case)
    label: str
    widget: str  # line | textarea | combo | list | dict
    options: tuple[str, ...] = ()  # combo 용
    placeholder: str = ""


@dataclass(frozen=True)
class RowVM:
    id: str
    title: str
    kind: str
    involvement: str
    involvement_label: str
    color: str
    enabled: bool
    values: dict = field(default_factory=dict)  # 편집 필드 현재값(model_dump)
    guide: dict | None = None  # {purpose, produces, ask, examples}


@dataclass(frozen=True)
class LintVM:
    level: str
    code: str
    message: str


@dataclass(frozen=True)
class SimVM:
    label: str
    outcome: str
    reason: str


@dataclass(frozen=True)
class CompletionVM:
    filled: int
    total: int
    percent: int
    next_layer: str | None  # 비어 있는 다음 추천 계층
    next_label: str | None


# 완성도 집계 대상(편집 가능 계층). verification 은 내보내기 전용이라 제외.
_COUNTABLE = ["context", "permissions", "mcp", "guardrails", "workflow"]


def completion(state: BuilderState) -> CompletionVM:
    """§0.6 완성도 미터 — 구성된 영역 수 + 다음 추천(비어 있는) 영역."""
    counts = {
        layer: sum(1 for c in state.ir.components if c.layer == layer and c.enabled)
        for layer in _COUNTABLE
    }
    filled = sum(1 for layer in _COUNTABLE if counts[layer] > 0)
    total = len(_COUNTABLE)
    nxt = next((layer for layer in _COUNTABLE if counts[layer] == 0), None)
    return CompletionVM(
        filled=filled,
        total=total,
        percent=round(filled / total * 100),
        next_layer=nxt,
        next_label=layer_meta[nxt]["label"] if nxt else None,
    )


_OUTCOME_LABEL = {
    "blocked-by-hook": "hook 차단",
    "blocked-by-permission": "권한 차단",
    "ask": "사용자 확인",
    "allowed": "통과",
}

# kind별 편집 필드 스펙 (스키마 필드와 1:1). id/layer/involvement/enabled/title 은 공통 처리.
_SPECS: dict[str, list[FieldSpec]] = {
    "prose-guideline": [
        FieldSpec("scope", "범위", "combo", ("project", "global")),
        FieldSpec("heading", "섹션 제목", "line"),
        FieldSpec("body", "본문", "textarea", placeholder="외부 LLM 답변을 붙여넣으세요…"),
    ],
    "permission-rule": [
        FieldSpec("action", "동작", "combo", ("allow", "ask", "deny")),
        FieldSpec("pattern", "패턴", "line", placeholder="Bash(rm -rf:*)"),
    ],
    "mcp-server": [
        FieldSpec("server_name", "서버 이름", "line", placeholder="github"),
        FieldSpec("command", "실행 명령", "line", placeholder="npx"),
        FieldSpec("args", "인자", "list"),
        FieldSpec("env", "환경변수 (${VAR} 플레이스홀더만)", "dict"),
    ],
    "hook": [
        FieldSpec("event", "시점", "combo", ("PreToolUse", "PostToolUse", "SessionStart", "Stop")),
        FieldSpec("matcher_tool", "대상 도구", "line", placeholder="Write|Edit"),
        FieldSpec("path_glob", "경로 glob(선택)", "line", placeholder="**/.env*"),
        FieldSpec("action", "동작", "combo", ("deny", "allow", "warn")),
        FieldSpec("script_name", "스크립트 파일", "line", placeholder="block-secrets.sh"),
        FieldSpec("script_body", "스크립트 본문 (exit 2=차단)", "textarea"),
    ],
    "policy-doc": [
        FieldSpec("doc_name", "문서 파일", "line", placeholder="secrets.md"),
        FieldSpec("body", "본문", "textarea"),
    ],
    "sub-agent": [
        FieldSpec("name", "이름", "line", placeholder="code-reviewer"),
        FieldSpec("description", "설명(언제 부르는지)", "line"),
        FieldSpec("tools", "도구", "list"),
        FieldSpec("model", "모델(선택)", "line"),
        FieldSpec("system_prompt", "시스템 프롬프트", "textarea"),
    ],
}


def field_specs(kind: str) -> list[FieldSpec]:
    return _SPECS.get(kind, [])


def nav_items(state: BuilderState) -> list[NavItemVM]:
    items: list[NavItemVM] = []
    for layer in layer_order:
        meta = layer_meta[layer]
        count = sum(1 for c in state.ir.components if c.layer == layer and c.enabled)
        items.append(
            NavItemVM(
                layer=layer,
                label=meta["label"],
                hint=meta["hint"],
                interactive=True,
                selected=(layer == state.selected_layer),
                count=count,
                dot_color="#1a7f37" if count else "#8c959f",
            )
        )
    return items


def rows_for_selected(state: BuilderState) -> list[RowVM]:
    rows: list[RowVM] = []
    for c in state.ir.components:
        if c.layer != state.selected_layer:
            continue
        inv = involvement_meta[c.involvement]
        g = guidance_for(c)
        guide = None
        if g is not None:
            guide = {
                "purpose": g.purpose,
                "produces": g.produces_file,
                "ask": g.ask_llm_template,
                "examples": list(g.good_examples),
            }
        rows.append(
            RowVM(
                id=c.id,
                title=c.title,
                kind=c.kind,
                involvement=c.involvement,
                involvement_label=inv["label"],
                color=inv["color"],
                enabled=c.enabled,
                values=c.model_dump(by_alias=False),
                guide=guide,
            )
        )
    return rows


def layer_meta_label(state: BuilderState) -> str:
    return layer_meta[state.selected_layer]["label"]


def layer_intro(state: BuilderState) -> dict[str, str]:
    intro = layer_intros[state.selected_layer]
    return {
        "what": intro.what_it_controls,
        "minimum": intro.minimum_to_do,
        "if_unsure": intro.if_unsure,
    }


def lint_items(state: BuilderState) -> list[LintVM]:
    return [
        LintVM(level=f["level"], code=f["code"], message=f["message"]) for f in lint_ir(state.ir)
    ]


def export_paths(state: BuilderState) -> list[str]:
    """산출 파일 경로 목록 (생성될 트리 미리보기)."""
    tree = assemble_project(state.ir, state.scaffold)
    return [vf.path for vf in tree]


def sim_items(state: BuilderState) -> list[SimVM]:
    """라이브 결정론 시뮬레이터 (LLM 0회) — 기본 시나리오 평가."""
    out: list[SimVM] = []
    for scenario in default_scenarios:
        r = simulate(state.ir, scenario)
        out.append(
            SimVM(
                label=scenario["label"],
                outcome=_OUTCOME_LABEL.get(r["outcome"], r["outcome"]),
                reason=r["reasons"][-1] if r["reasons"] else "",
            )
        )
    return out
