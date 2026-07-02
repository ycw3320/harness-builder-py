"""PM7-S4 성숙도 산식 — 프리셋별 기대 레벨 + 전이(토글) 회귀."""

from harness_app import view_model as vm
from harness_app.state import BuilderState
from harness_core.ir.schema import HarnessIR


def _level(preset: str) -> int:
    return vm.maturity(BuilderState("demo", preset=preset)).level


def test_preset_levels():
    assert _level("minimal") == 1  # prose 1개 = 약속
    assert _level("speed") == 2  # allow 권한만 = 규칙(hook 없음)
    assert _level("mvp") == 2  # deny 권한 있어도 차단 hook 없음
    assert _level("safety-first") == 4  # hook+오류0+보안0+핵심 커버 = 검증됨
    assert _level("enterprise") == 4


def test_empty_is_level0():
    st = BuilderState("demo", preset="minimal")
    st.load_ir(HarnessIR(meta=st.ir.meta, components=[]))
    m = vm.maturity(st)
    assert m.level == 0 and m.next_hint


def test_hook_off_drops_from_verified():
    st = BuilderState("demo", preset="safety-first")
    hook = next(c for c in st.ir.components if c.kind == "hook")
    st.toggle(hook.id)  # 차단 hook off → 강제 상실
    m = vm.maturity(st)
    assert m.level == 2 and "hook" in m.next_hint


def test_security_warning_blocks_level4():
    from harness_core.ir.factory import create_component

    st = BuilderState("demo", preset="safety-first")
    broad = create_component("permission-rule", "permissions").model_copy(
        update={"action": "allow", "pattern": "Bash"}
    )
    st.load_ir(HarnessIR(meta=st.ir.meta, components=[*st.ir.components, broad]))
    m = vm.maturity(st)
    assert m.level == 3  # 보안 경고가 '검증됨'을 막는다
    assert "경고" in m.next_hint


def test_label_and_detail_exposed():
    m = vm.maturity(BuilderState("demo", preset="safety-first"))
    assert m.label.startswith("Lv4")
    assert "산식" in m.detail  # 산식 공개(게임화 역효과 통제)
    assert m.next_hint is None
