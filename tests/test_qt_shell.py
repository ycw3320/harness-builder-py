"""Qt 셸 상태기계 회귀 게이트 (offscreen) — PM6 핵심 흐름 무보호 해소(리뷰 #7).

대상: 랜딩↔빌더 스택, 아하 트리거(진짜 변화만), 예시 표식 수명주기(편집·복제·import),
RuleToggle 콜백, 점프(계층 전환+펼침), matcher regex 붕괴 방어.
QSettings 는 temp_settings 로 격리(사용자 레지스트리 미접촉).
"""

import pytest

pytest.importorskip("PySide6")


def _make_window(qapp, temp_settings, preset="safety-first"):
    from harness_app.qt_shell.app import BuilderWindow
    from harness_app.state import BuilderState

    win = BuilderWindow(state=BuilderState("demo", preset=preset), settings=temp_settings)
    win.show()
    qapp.processEvents()
    return win


def test_landing_skip_requires_landing_and_aha(qapp, temp_settings):
    win = _make_window(qapp, temp_settings)
    assert win._stack.currentIndex() == 0  # 첫 실행 = 랜딩
    win._enter_builder()
    assert win._stack.currentIndex() == 1
    win._show_landing()
    assert win._stack.currentIndex() == 0  # '소개' 버튼 재방문
    # 랜딩만 보고 종료(아하 미달성) → 재실행 시 여전히 랜딩(정의 노출 0회 불변식)
    win2 = _make_window(qapp, temp_settings)
    assert win2._stack.currentIndex() == 0
    # 아하 달성(결과가 실제 변하는 토글) 후 재실행 → 빌더 직행 + 배너 복원
    hook = next(c for c in win2.state.ir.components if c.kind == "hook")
    win2._on_rule_toggle(hook.id)
    win3 = _make_window(qapp, temp_settings)
    assert win3._stack.currentIndex() == 1
    assert win3._aha_revealed is True


def test_aha_only_on_real_change_and_persists(qapp, temp_settings):
    from harness_app.qt_shell.app import QFrame

    win = _make_window(qapp, temp_settings)
    assert win._aha_revealed is False
    hook = next(c for c in win.state.ir.components if c.kind == "hook")
    win._on_rule_toggle(hook.id)  # .env 차단 OFF → 결과 실제 역전
    qapp.processEvents()
    assert win._aha_revealed is True
    win._rebuild_right()  # 2차 재빌드(애니메이션 없이)에도 배너 유지
    qapp.processEvents()
    assert [c for c in win._right_host.findChildren(QFrame) if c.objectName() == "ahaCard"]
    # persist: 같은 settings 로 새 창 → 배너 상태 복원(랜딩 스킵과 결합해도 정의 노출 0회 방지)
    win2 = _make_window(qapp, temp_settings)
    assert win2._aha_revealed is True


def test_aha_not_triggered_by_meaningless_toggle(qapp, temp_settings):
    win = _make_window(qapp, temp_settings, preset="speed")  # allow 규칙뿐
    allow = next(c for c in win.state.ir.components if c.kind == "permission-rule")
    win._on_rule_toggle(allow.id)  # 결과 불변 토글
    qapp.processEvents()
    assert win._aha_revealed is False  # 거짓 인과 배너 금지


def test_example_lifecycle_edit_and_duplicate(qapp, temp_settings):
    win = _make_window(qapp, temp_settings)
    win._enter_builder()
    assert win._example_ids  # safety-first 시드 = 예시

    # ① 편집 → 예시 해제
    rw = win._rows[0]
    rw._patch("heading", "내 제목")
    assert rw._row.id not in win._example_ids

    # ② 예시 복제(위젯 버튼 경로 = _do_duplicate → 윈도 콜백) → 사본도 예시 승계
    win.state.set_selected_layer("guardrails")
    qapp.processEvents()
    hook_rw = next(r for r in win._rows if r._row.kind == "hook")
    assert hook_rw._row.id in win._example_ids
    before_ids = {c.id for c in win.state.ir.components}
    hook_rw._do_duplicate()  # UI 배선 관통(직접 _duplicate_component 호출 금지 — 배선 회귀 감지)
    qapp.processEvents()
    new_ids = {c.id for c in win.state.ir.components} - before_ids
    assert new_ids and new_ids <= win._example_ids


def test_import_clears_example_marks_real_path(qapp, temp_settings, tmp_path, monkeypatch):
    """_on_import 실경로(다이얼로그 모킹) — 예시 클리어가 load_ir 통지 '이전'인지 회귀 감지."""
    from harness_app.qt_shell import app as appmod
    from harness_app.state import BuilderState
    from harness_core.export.assemble_project import assemble_project
    from harness_fs.policy import MergeStrategy
    from harness_fs.writer import write_tree

    # 실제 프로젝트 폴더 생성(mvp 프리셋 export) → 역import 대상
    src = BuilderState("demo", preset="mvp")
    write_tree(assemble_project(src.ir, "minimal"), tmp_path, strategy=MergeStrategy.SKIP_EXISTING)

    win = _make_window(qapp, temp_settings)
    win._enter_builder()
    assert win._example_ids
    monkeypatch.setattr(
        appmod.QFileDialog,
        "getExistingDirectory",
        staticmethod(lambda *a, **k: str(tmp_path / "demo")),
    )
    monkeypatch.setattr(
        appmod.QMessageBox,
        "question",
        staticmethod(lambda *a, **k: appmod.QMessageBox.StandardButton.Yes),
    )
    win._on_import()
    qapp.processEvents()
    assert win._example_ids == set()  # 가져온 구성은 예시 아님
    assert win.state.ir.components  # 실제로 교체됨


def test_rule_toggle_widget_invokes_callback(qapp, temp_settings):
    from harness_app.qt_shell.app import LIGHT, RuleToggle

    got = []
    t = RuleToggle("규칙", True, LIGHT, lambda on: got.append(on))
    t.mousePressEvent(None)
    assert got == [False]  # 체크 해제 콜백
    t.mousePressEvent(None)
    assert got == [False, True]


def test_jump_switches_layer_and_opens_row(qapp, temp_settings):
    win = _make_window(qapp, temp_settings)
    win._enter_builder()
    assert win.state.selected_layer == "context"
    hook = next(c for c in win.state.ir.components if c.kind == "hook")
    win._jump_to_component(hook.id)
    qapp.processEvents()
    assert win.state.selected_layer == "guardrails"
    assert any(rw._row.id == hook.id and rw._open for rw in win._rows)


def test_invalid_matcher_regex_does_not_break_right_panel(qapp, temp_settings):
    win = _make_window(qapp, temp_settings)
    win._enter_builder()
    hook = next(c for c in win.state.ir.components if c.kind == "hook")
    win.state.patch(hook.id, {"matcher_tool": "Bash("})  # 미완성 괄호 → 이전엔 re.error 붕괴
    qapp.processEvents()
    # 우패널이 살아있음: export 버튼(primaryBtn)이 여전히 존재
    from PySide6.QtWidgets import QPushButton

    btns = [b for b in win._right_host.findChildren(QPushButton) if b.objectName() == "primaryBtn"]
    assert btns, "regex 오류 시 우패널이 반쪽으로 무너지면 안 된다"


def test_involvement_change_keeps_row_open(qapp, temp_settings):
    win = _make_window(qapp, temp_settings)
    win._enter_builder()
    rw = win._rows[0]
    rw.set_open(True)
    rw._patch("involvement", "auto")  # 이전엔 signature 변화 → 중앙 재빌드 → 행 파괴
    qapp.processEvents()
    assert rw._open is True  # 같은 위젯이 살아서 열려 있음(파괴되지 않음)
    assert win._rows[0] is rw  # 재빌드로 교체되지 않음


def test_matcher_field_visual_warning_and_tip_restore(qapp, temp_settings):
    """matcher 잘못된 패턴 → 붉은 테두리, 유효 복귀 → 테두리 제거 + 2단 풀이 툴팁 복원."""
    from PySide6.QtWidgets import QLineEdit

    win = _make_window(qapp, temp_settings)
    win._enter_builder()
    win.state.set_selected_layer("guardrails")
    qapp.processEvents()
    hook_rw = next(r for r in win._rows if r._row.kind == "hook")
    le = next(w for w in hook_rw.findChildren(QLineEdit) if w.placeholderText() == "Write|Edit")
    le.setText("Bash(")
    assert "C9362B" in le.styleSheet()  # 오류 테두리
    le.setText("Write|Edit")
    assert le.styleSheet() == ""
    assert "검사할 도구" in le.toolTip()  # spec.tip 복원(빈 문자열 소거 회귀 감지)
