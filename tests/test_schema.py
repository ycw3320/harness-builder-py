from harness_core.ir.presets import safety_first_preset
from harness_core.ir.schema import parse_ir, safe_parse_component


def test_preset_roundtrip():
    ir = safety_first_preset("demo")
    ir2 = parse_ir(ir.model_dump())
    assert len(ir2.components) == 7
    assert ir2.components[0].kind == "prose-guideline"
    assert ir2.components[5].kind == "hook"


def test_safe_parse_ok():
    res = safe_parse_component({
        "id": "x", "kind": "permission-rule", "layer": "permissions", "title": "t",
        "involvement": "manual-gate", "enabled": True, "action": "deny", "pattern": "Bash(x:*)",
    })
    assert res["ok"] is True


def test_safe_parse_fail():
    res = safe_parse_component({"id": "x", "kind": "permission-rule"})
    assert res["ok"] is False
    assert res["errors"]
