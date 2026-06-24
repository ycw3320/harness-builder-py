"""PM3-B 폼 — field_specs 전 kind 커버리지 + 각 kind 필드 patch 검증(ValidationError 0)."""

from harness_app import view_model as vm
from harness_app.state import BuilderState
from harness_core.ir.registry import kind_registry

# kind → 해당 kind 를 받는 계층
_LAYER = {
    "prose-guideline": "context",
    "permission-rule": "permissions",
    "mcp-server": "mcp",
    "hook": "guardrails",
    "policy-doc": "guardrails",
    "sub-agent": "workflow",
}

_SAMPLES = {
    "scope": "global",
    "heading": "h",
    "body": "b",
    "action": "deny",
    "pattern": "Bash(x:*)",
    "server_name": "s",
    "command": "npx",
    "args": ["-y"],
    "env": {"T": "${T}"},
    "event": "PreToolUse",
    "matcher_tool": "Write",
    "path_glob": "**/x",
    "script_name": "h.sh",
    "script_body": "exit 0",
    "doc_name": "r.md",
    "name": "a",
    "description": "d",
    "tools": ["Read"],
    "model": "",
    "system_prompt": "sp",
}


def test_field_specs_cover_all_kinds():
    for kind in kind_registry:
        assert vm.field_specs(kind), kind


def test_patch_each_kind_field_validates():
    for kind, layer in _LAYER.items():
        s = BuilderState("demo", preset="minimal")
        s.set_selected_layer(layer)
        s.add_component(kind)
        cid = s.ir.components[-1].id
        for spec in vm.field_specs(kind):
            s.patch(cid, {spec.name: _SAMPLES[spec.name]})  # ValidationError 없어야 함
        s.patch(cid, {"involvement": "auto"})
        assert s.ir.components[-1].involvement == "auto"


def test_all_layers_interactive():
    s = BuilderState("demo")
    assert all(item.interactive for item in vm.nav_items(s))
