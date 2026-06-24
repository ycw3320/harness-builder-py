"""강제수준 사다리 — 레벨·승격(프로즈→정책문서→hook) 검증."""

from harness_core.ir.enforcement import can_promote, enforcement_level, promote
from harness_core.ir.factory import create_component


def test_levels_and_can_promote():
    assert enforcement_level("prose-guideline") == "권고"
    assert enforcement_level("policy-doc") == "문서"
    assert enforcement_level("hook") == "자동 차단"
    assert can_promote("prose-guideline")
    assert can_promote("policy-doc")
    assert not can_promote("hook")
    assert not can_promote("permission-rule")


def test_promote_prose_to_policy():
    p = create_component("prose-guideline", "context").model_copy(
        update={"heading": "보안 규칙", "body": "- 비밀키 금지"}
    )
    pol = promote(p)
    assert pol.kind == "policy-doc"
    assert pol.layer == "guardrails"
    assert pol.doc_name == "보안-규칙.md"
    assert pol.body == "- 비밀키 금지"


def test_promote_policy_to_hook():
    d = create_component("policy-doc", "guardrails").model_copy(
        update={"doc_name": "rules.md", "body": "규칙"}
    )
    h = promote(d)
    assert h.kind == "hook"
    assert h.script_name == "rules.sh"
    assert "exit 2" in h.script_body


def test_promote_hook_is_top():
    assert promote(create_component("hook", "guardrails")) is None
