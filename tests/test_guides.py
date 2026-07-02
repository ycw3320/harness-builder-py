"""필드 가이드·계층 소개·UI 메타 포팅 검증."""

from harness_app.guides import (
    field_guides,
    guidance_for,
    involvement_meta,
    layer_intros,
    layer_order,
)
from harness_core.ir.presets import safety_first_preset

_KINDS = [
    "prose-guideline:project",
    "prose-guideline:global",
    "permission-rule",
    "hook",
    "policy-doc",
    "sub-agent",
    "mcp-server",
]


def test_all_kinds_have_guides():
    for key in _KINDS:
        assert key in field_guides


def test_guidance_for_prose_scope_variants():
    prose = [c for c in safety_first_preset("demo").components if c.kind == "prose-guideline"]
    g_global = guidance_for(next(c for c in prose if c.scope == "global"))
    g_project = guidance_for(next(c for c in prose if c.scope == "project"))
    assert g_global is not None and g_project is not None
    assert g_global is not g_project  # scope 별로 다른 가이드


def test_guidance_for_hook():
    hook = next(c for c in safety_first_preset("demo").components if c.kind == "hook")
    g = guidance_for(hook)
    assert g is not None
    assert g.produces_file.startswith(".claude/settings.json")


def test_layer_intros_cover_all_layers():
    for layer in layer_order:
        assert layer in layer_intros


def test_involvement_colors_single_source():
    assert involvement_meta["auto"]["color"] == "#1a7f37"
    assert involvement_meta["assisted"]["color"] == "#0969da"
    assert involvement_meta["manual-gate"]["color"] == "#bc4c00"


def test_layer_flow_caption_matches_layer_count():
    # PM6 흐름 캡션은 6개 영역과 1:1 — 단계 수가 어긋나면(페르소나 공통 지적) 실패해야 한다.
    from harness_app.guides import LAYER_FLOW_CAPTION

    assert len(LAYER_FLOW_CAPTION.split("→")) == len(layer_order)
