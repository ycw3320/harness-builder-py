"""표시용 view-model — 상태·코어에서 화면 데이터를 파생 (프레임워크 무의존).

두 셸(Flet/Qt)이 동일하게 소비한다 → 위젯 배선만 갈리고 로직은 공유(M6 LOC 공정).
"""

from __future__ import annotations

from dataclasses import dataclass

from harness_core.export.assemble_project import assemble_project
from harness_core.lint.lint import lint_ir
from harness_core.sim.simulate import default_scenarios, simulate

from .guides import involvement_meta, layer_intros, layer_meta, layer_order
from .state import BuilderState

# 이 수직 슬라이스에서 실제 편집 동작하는 계층 (S2: context만)
SLICE_ACTIVE_LAYER = "context"


@dataclass(frozen=True)
class NavItemVM:
    layer: str
    label: str
    hint: str
    interactive: bool  # 슬라이스에서 클릭 가능 여부
    selected: bool
    count: int  # enabled component 수
    dot_color: str  # 내용 있음(녹)/없음(회)


@dataclass(frozen=True)
class RowVM:
    id: str
    title: str
    kind: str
    involvement: str
    involvement_label: str
    color: str
    enabled: bool
    # 펼침 편집 필드 (prose 슬라이스: heading/body)
    heading: str | None
    body: str | None


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


_OUTCOME_LABEL = {
    "blocked-by-hook": "hook 차단",
    "blocked-by-permission": "권한 차단",
    "ask": "사용자 확인",
    "allowed": "통과",
}


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
                interactive=(layer == SLICE_ACTIVE_LAYER),
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
        rows.append(
            RowVM(
                id=c.id,
                title=c.title,
                kind=c.kind,
                involvement=c.involvement,
                involvement_label=inv["label"],
                color=inv["color"],
                enabled=c.enabled,
                heading=getattr(c, "heading", None),
                body=getattr(c, "body", None),
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
