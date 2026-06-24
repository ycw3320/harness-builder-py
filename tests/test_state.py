"""빌더 상태 컨테이너(store 포팅) 검증 — 불변 업데이트·구독·그룹 이동."""

from harness_app.state import BuilderState, group_key


def test_initial_preset_loaded():
    s = BuilderState("demo")
    assert len(s.ir.components) == 7
    assert s.selected_layer == "context"


def test_subscribe_and_unsubscribe():
    s = BuilderState("demo")
    calls: list[int] = []
    unsub = s.subscribe(lambda: calls.append(1))
    s.set_selected_layer("permissions")
    assert calls == [1]
    unsub()
    s.set_selected_layer("mcp")
    assert calls == [1]  # 해제 후 미통지


def test_update_creates_new_ir():
    s = BuilderState("demo")
    before = s.ir
    s.toggle(s.ir.components[0].id)
    assert s.ir is not before  # 제자리 변형 금지


def test_add_then_remove():
    s = BuilderState("demo")
    n = len(s.ir.components)
    s.add_component("permission-rule")
    assert len(s.ir.components) == n + 1
    s.remove(s.ir.components[-1].id)
    assert len(s.ir.components) == n


def test_duplicate_inserts_after_with_new_id():
    s = BuilderState("demo")
    first = s.ir.components[0]
    s.duplicate(first.id)
    dup = s.ir.components[1]
    assert dup.id != first.id
    assert dup.title.endswith("(복제)")


def test_move_swaps_within_group():
    s = BuilderState("demo")
    perms = [c for c in s.ir.components if c.kind == "permission-rule"]
    second_id = perms[1].id
    s.move(second_id, "up")
    new_perms = [c for c in s.ir.components if c.kind == "permission-rule"]
    assert new_perms[0].id == second_id


def test_move_blocked_across_scope_groups():
    s = BuilderState("demo")
    prose = [c for c in s.ir.components if c.kind == "prose-guideline"]
    assert len({group_key(c) for c in prose}) == 2  # global/project 다른 그룹


def test_patch_revalidates_field():
    s = BuilderState("demo")
    pid = next(c.id for c in s.ir.components if c.kind == "permission-rule")
    s.patch(pid, {"pattern": "Bash(ls:*)"})
    patched = next(c for c in s.ir.components if c.id == pid)
    assert patched.pattern == "Bash(ls:*)"


def test_add_prose_section_scope():
    s = BuilderState("demo")
    s.add_prose_section("global")
    last = s.ir.components[-1]
    assert last.kind == "prose-guideline"
    assert last.scope == "global"


def test_minimal_preset_starts_light():
    s = BuilderState("demo", preset="minimal")
    assert len(s.ir.components) == 1
    assert s.ir.components[0].kind == "prose-guideline"
    assert s.ir.meta.preset == "minimal"


def test_load_preset_switches():
    s = BuilderState("demo", preset="minimal")
    s.load_preset("safety-first")
    assert len(s.ir.components) == 7
    s.load_preset("minimal")
    assert len(s.ir.components) == 1
