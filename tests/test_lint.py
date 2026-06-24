from harness_core.ir.presets import safety_first_preset
from harness_core.ir.schema import McpServer, PermissionRule
from harness_core.lint.lint import has_errors, lint_ir


def _codes(findings):
    return {f["code"] for f in findings}


def test_preset_no_errors():
    assert not has_errors(lint_ir(safety_first_preset("demo")))


def test_duplicate_id():
    ir = safety_first_preset("demo")
    ir.components.append(ir.components[0].model_copy())
    f = lint_ir(ir)
    assert "duplicate-id" in _codes(f)
    assert has_errors(f)


def test_inline_secret():
    ir = safety_first_preset("demo")
    ir.components.append(
        McpServer(
            id="mcp-x",
            layer="mcp",
            title="X",
            involvement="manual-gate",
            enabled=True,
            server_name="x",
            command="node",
            args=[],
            env={"TOKEN": "sk-live-12345"},
        )
    )
    assert "inline-secret" in _codes(lint_ir(ir))


def test_placeholder_ok():
    ir = safety_first_preset("demo")
    ir.components.append(
        McpServer(
            id="mcp-ok",
            layer="mcp",
            title="ok",
            involvement="manual-gate",
            enabled=True,
            server_name="ok",
            command="node",
            args=[],
            env={"TOKEN": "${MY_TOKEN}"},
        )
    )
    assert "inline-secret" not in _codes(lint_ir(ir))


def test_permission_conflict():
    ir = safety_first_preset("demo")
    ir.components.append(
        PermissionRule(
            id="p-allow",
            layer="permissions",
            title="a",
            involvement="manual-gate",
            enabled=True,
            action="allow",
            pattern="Bash(rm -rf:*)",
        )
    )
    assert "permission-conflict" in _codes(lint_ir(ir))


def test_empty_harness():
    ir = safety_first_preset("demo")
    for c in ir.components:
        c.enabled = False
    f = lint_ir(ir)
    assert "empty-harness" in _codes(f)
    assert not has_errors(f)
