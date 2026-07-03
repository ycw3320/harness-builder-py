"""PM8 QuickStart — 스택 감지·질문→IR 매핑(성숙도 보장)·프리필 (순수, Qt 무의존)."""

from harness_app import view_model as vm
from harness_app.detect import detect_project
from harness_app.quickstart import DEFAULT_PROTECTIONS, PERSONAS, build_quick_ir
from harness_app.state import BuilderState


def _mat_level(ir) -> int:
    st = BuilderState("demo")
    st.load_ir(ir)
    return vm.maturity(st).level


def test_detect_node_with_scripts(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts": {"build": "vite build", "test": "vitest"}}', encoding="utf-8"
    )
    d = detect_project(str(tmp_path))
    assert d and d.stack == "Node.js(npm)" and d.build_cmd == "npm run build"
    assert d.test_cmd == "npm test" and d.evidence == "package.json"


def test_detect_python_and_markers(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    d = detect_project(str(tmp_path))
    assert d and d.stack == "Python" and d.test_cmd == "pytest"
    # 미감지 폴더
    empty = tmp_path / "none"
    empty.mkdir()
    assert detect_project(str(empty)) is None


def test_default_protections_reach_level4_for_all_personas():
    # 북극성 보장: 어떤 성향이든 기본값(전 보호 켬)이면 Lv4 '검증됨'.
    for key, _label, _preset in PERSONAS:
        ir = build_quick_ir("demo", key, DEFAULT_PROTECTIONS)
        assert _mat_level(ir) == 4, key


def test_protection_removal_drops_level():
    ir = build_quick_ir("demo", "careful", frozenset({"rm_guard"}))  # hook·push 해제
    assert not any(c.kind == "hook" for c in ir.components)
    assert _mat_level(ir) == 2  # 규칙만 남음


def test_detected_prefills_project_prose(tmp_path):
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest"}}', encoding="utf-8")
    d = detect_project(str(tmp_path))
    ir = build_quick_ir("demo", "fast", DEFAULT_PROTECTIONS, d)
    prose = [c for c in ir.components if c.kind == "prose-guideline" and c.scope == "project"]
    assert prose and "Node.js" in prose[0].body and "npm test" in prose[0].body
