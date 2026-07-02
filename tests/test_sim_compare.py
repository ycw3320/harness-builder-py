"""PM6-S2/S3 before/after 시연 — 빈 IR(통과) vs 현재 IR(차단) 대비 + 토글 규칙·역전.

초심자 아하 엔진의 회귀 게이트: '규칙 없으면 통과 ↔ 지금 차단' 대비가 깨지면 실패한다.
"""

from harness_app import view_model as vm
from harness_app.state import BuilderState


def test_sim_compare_safety_first_shows_contrast():
    st = BuilderState("demo", preset="safety-first")
    rows = {r.label: r for r in vm.sim_compare(st)}

    env = rows[".env 파일에 쓰기 시도"]
    assert env.before_raw == "allowed"  # 규칙 없으면 통과(위험)
    assert env.after_raw == "blocked-by-hook"  # 지금은 hook 차단(안전)
    assert env.changed is True
    assert env.after_blocked_by  # 차단을 만든 컴포넌트 id(점프용)
    assert env.after_reason  # 왜 막혔는지 한 줄

    push = rows["강제 push 시도"]
    assert push.before_raw == "allowed"
    assert push.after_raw == "ask"
    assert push.changed is True

    build = rows["정상 빌드 실행"]
    assert build.before_raw == "allowed"
    assert build.after_raw == "allowed"  # 정상 작업은 그대로 통과
    assert build.changed is False


def test_sim_compare_minimal_has_no_contrast():
    # minimal(빈 시작)은 차단 규칙이 없어 대비가 0 — 첫 화면 기본으로 부적절한 이유.
    rows = vm.sim_compare(BuilderState("demo", preset="minimal"))
    assert all(r.after_raw == "allowed" for r in rows)
    assert all(r.changed is False for r in rows)


def test_sim_rules_flags_affects_sim():
    # allow 권한은 목록에 남되(=export on/off 실기능 유지) 시뮬 무영향 플래그로 구분.
    rules = vm.sim_rules(BuilderState("demo", preset="safety-first"))
    assert {r.kind for r in rules} <= {"hook", "permission-rule"}
    by_title = {r.title: r for r in rules}
    assert by_title["테스트 실행 허용"].affects_sim is False
    assert by_title[".env 쓰기 차단 (시크릿 보호)"].affects_sim is True
    assert any(r.affects_sim for r in rules)
    # speed(allow 전용): 토글은 가능하나 시연(꺼보세요) 대상은 0
    sp = vm.sim_rules(BuilderState("demo", preset="speed"))
    assert sp and all(not r.affects_sim for r in sp)


def test_invalid_matcher_identifies_offender():
    # 깨진 hook 패턴 → 전 시나리오 '평가 불가' + 오류 hook 을 blockedBy 로 특정(클릭→점프 가능).
    st = BuilderState("demo", preset="safety-first")
    hook = next(c for c in st.ir.components if c.kind == "hook")
    st.patch(hook.id, {"matcher_tool": "Bash("})
    rows = vm.sim_compare(st)
    assert all(r.after_raw == "invalid" for r in rows)
    assert all(r.after_blocked_by == hook.id for r in rows)
    assert all(hook.title in r.after_reason for r in rows)


def test_toggle_off_reverses_block():
    st = BuilderState("demo", preset="safety-first")
    env_hook = next(c for c in st.ir.components if c.kind == "hook")
    st.toggle(env_hook.id)  # .env 차단 hook 끄기
    rows = {r.label: r for r in vm.sim_compare(st)}
    assert rows[".env 파일에 쓰기 시도"].after_raw == "allowed"  # 차단이 풀림(인과)


def test_default_preset_is_safety_first():
    # 첫 화면 차단 시연을 위해 기본 프리셋은 채워진 상태여야 함(PM6-S1).
    st = BuilderState("demo")
    assert any(c.kind == "hook" for c in st.ir.components)
