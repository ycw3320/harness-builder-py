"""역import 라운드트립 — export_ir 산출을 import_ir 가 복원(복원 가능 필드 동일)."""

from harness_app.state import BuilderState
from harness_core.export.export_ir import export_ir
from harness_core.export.import_ir import import_ir
from harness_core.ir.presets import safety_first_preset


def _tree(ir):
    return {vf.path: vf.content for vf in export_ir(ir)}


def _by_kind(components, kind):
    return [c for c in components if c.kind == kind]


def test_roundtrip_recoverable_fields():
    ir = safety_first_preset("demo")
    imp = import_ir(_tree(ir), "demo")
    o, n = ir.components, imp.components

    for k in ["prose-guideline", "permission-rule", "hook", "policy-doc"]:
        assert len(_by_kind(o, k)) == len(_by_kind(n, k)), k

    op, npr = _by_kind(o, "prose-guideline"), _by_kind(n, "prose-guideline")
    assert {(p.scope, p.heading, p.body) for p in op} == {(p.scope, p.heading, p.body) for p in npr}

    assert {(p.action, p.pattern) for p in _by_kind(o, "permission-rule")} == {
        (p.action, p.pattern) for p in _by_kind(n, "permission-rule")
    }

    oh, nh = _by_kind(o, "hook")[0], _by_kind(n, "hook")[0]
    assert (oh.event, oh.matcher_tool, oh.script_name, oh.script_body) == (
        nh.event,
        nh.matcher_tool,
        nh.script_name,
        nh.script_body,
    )

    assert {(d.doc_name, d.body) for d in _by_kind(o, "policy-doc")} == {
        (d.doc_name, d.body) for d in _by_kind(n, "policy-doc")
    }


def test_roundtrip_mcp_and_agent():
    s = BuilderState("demo", preset="minimal")
    s.set_selected_layer("mcp")
    s.add_component("mcp-server")
    s.patch(
        s.ir.components[-1].id,
        {"server_name": "gh", "command": "npx", "args": ["-y", "x"], "env": {"TOK": "${TOK}"}},
    )
    s.set_selected_layer("workflow")
    s.add_component("sub-agent")
    s.patch(
        s.ir.components[-1].id,
        {"name": "rev", "description": "d", "tools": ["Read", "Grep"], "system_prompt": "sp"},
    )
    imp = import_ir(_tree(s.ir), "demo")
    m = _by_kind(imp.components, "mcp-server")[0]
    assert m.server_name == "gh"
    assert m.command == "npx"
    assert m.args == ["-y", "x"]
    assert m.env == {"TOK": "${TOK}"}
    a = _by_kind(imp.components, "sub-agent")[0]
    assert (a.name, a.description, a.tools, a.system_prompt) == ("rev", "d", ["Read", "Grep"], "sp")
