"""TS 골든 출력과 동치성 게이트 — 경로 집합 + 경로별 내용 바이트 동일 (리스크 R5 방어)."""
from harness_core.export.assemble_project import assemble_project
from harness_core.export.export_ir import export_ir
from harness_core.ir.presets import safety_first_preset
from harness_core.lint.lint import lint_ir
from harness_core.sim.simulate import default_scenarios, simulate


def _tree_map(tree):
    return {f.path: f.content for f in tree}


def _golden_map(rows):
    return {r["path"]: r["content"] for r in rows}


def _assert_tree_identical(py_tree, golden_rows):
    pm = _tree_map(py_tree)
    gm = _golden_map(golden_rows)
    assert set(pm) == set(gm), f"경로 집합 불일치: {set(pm) ^ set(gm)}"
    for path, content in gm.items():
        assert pm[path] == content, f"내용 불일치: {path}"


def test_export_byte_identical(golden):
    _assert_tree_identical(export_ir(safety_first_preset("demo")), golden("export_preset"))


def test_assemble_minimal(golden):
    _assert_tree_identical(assemble_project(safety_first_preset("demo"), "minimal"), golden("assemble_minimal"))


def test_assemble_harness_only(golden):
    _assert_tree_identical(assemble_project(safety_first_preset("demo"), "harness-only"), golden("assemble_harness_only"))


def test_simulate_identical(golden):
    results = [simulate(safety_first_preset("demo"), a) for a in default_scenarios]
    assert results == golden("simulate")


def test_lint_identical(golden):
    assert lint_ir(safety_first_preset("demo")) == golden("lint_preset")
