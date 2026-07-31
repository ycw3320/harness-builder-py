"""1-C 크로스플랫폼 훅 precheck 회귀 — 발견 B '거짓 안전' 제거 계약.

계약: 훅 스크립트의 shebang 실행기가 이 PC 에 없으면
  ① check_hook_runtimes 가 그 사실을 잡고(어느 훅이 영향받는지·차단 훅 포함 여부)
  ② maturity 가 Lv4 '검증됨'을 보류하고 사유를 노출한다.
환경 의존을 없애기 위해 available 을 주입해 bash 유무를 양쪽 다 재현한다.
"""

from __future__ import annotations

from harness_app.runtime_check import check_hook_runtimes, required_runtime, runtime_available
from harness_app.state import BuilderState
from harness_app.view_model import maturity


def _no_bash(key: str) -> bool:
    return key not in ("bash", "sh", "zsh")


def _all_present(key: str) -> bool:
    return True


def test_required_runtime_reads_shebang():
    assert required_runtime("#!/usr/bin/env bash\nexit 0") == "bash"
    assert required_runtime("#!/bin/bash\nexit 0") == "bash"
    assert required_runtime("#!/bin/bash -e\n") == "bash"
    assert required_runtime("#!/bin/sh\n") == "sh"
    assert required_runtime("#!/usr/bin/env python3\n") == "python"
    assert required_runtime("#!/usr/bin/python3.11\n") == "python"
    assert required_runtime("#!/usr/bin/env node\n") == "node"
    assert required_runtime("echo hi") is None  # shebang 없음
    assert required_runtime("") is None


def test_shebang_token_boundaries_not_substring():
    """부분문자열 매칭이면 pwsh/zsh 가 sh 로 뭉개진다 — 단어 경계 매칭 회귀."""
    assert required_runtime("#!/usr/bin/env pwsh\nexit 0") == "pwsh"
    assert required_runtime("#!/usr/bin/pwsh -File\n") == "pwsh"
    assert required_runtime("#!/usr/bin/env zsh\n") == "zsh"


def test_shebang_windows_paths():
    """Windows 경로(백슬래시·.exe)도 실행기명으로 인식."""
    assert required_runtime(r"#!C:\Git\bin\bash.exe") == "bash"
    assert required_runtime("#!C:/Program Files/Git/bin/bash.exe") == "bash"


def test_python_and_windows_powershell_treated_available():
    # 앱 자체가 Python 으로 실행 중 → python 은 항상 사용 가능으로 간주.
    assert runtime_available("python") is True


def test_detects_missing_bash_and_flags_blocking():
    """safety-first 프리셋(= bash 차단 훅 포함)에서 bash 부재를 잡아야 한다."""
    st = BuilderState("demo", preset="safety-first")
    rt = check_hook_runtimes(st.ir, available=_no_bash)
    assert not rt.ok
    assert "bash" in rt.missing
    assert rt.affected_titles  # 영향받는 훅 제목 노출
    assert rt.blocking_affected is True  # 그중 deny 훅 포함 → 차단이 실제론 미실행
    assert rt.notes and "Git" in rt.notes[0]  # 설치 안내(사람 말)
    assert "bash" in rt.runtime_names


def test_ok_when_runtime_present():
    st = BuilderState("demo", preset="safety-first")
    rt = check_hook_runtimes(st.ir, available=_all_present)
    assert rt.ok
    assert rt.missing == ()
    assert rt.blocking_affected is False


def test_disabled_hooks_are_not_checked():
    """꺼진 훅은 산출물에 안 들어가므로 실행환경 판정 대상이 아니다."""
    st = BuilderState("demo", preset="safety-first")
    for c in st.ir.components:
        if c.kind == "hook":
            st.patch(c.id, {"enabled": False})
    rt = check_hook_runtimes(st.ir, available=_no_bash)
    assert rt.ok and rt.checked == 0


def test_maturity_withholds_lv4_when_runtime_missing(monkeypatch):
    """핵심 계약: bash 없는 PC 에서 Lv4 '검증됨'이 나오면 안 된다(거짓 안전)."""
    import harness_app.view_model as vmod

    st = BuilderState("demo", preset="safety-first")

    # 실행기가 모두 있는 환경 → 기존 판정 유지(Lv4 도달 가능)
    monkeypatch.setattr(vmod, "check_hook_runtimes", lambda ir: _fake_rt(ok=True))
    m_ok = maturity(st)
    assert m_ok.runtime_blocked is False

    # bash 부재 + 차단 훅 영향 → Lv4 보류
    monkeypatch.setattr(vmod, "check_hook_runtimes", lambda ir: _fake_rt(ok=False))
    m_bad = maturity(st)
    assert m_bad.runtime_blocked is True
    assert m_bad.level <= 3
    assert m_bad.caveat == ""  # Lv4 가 아니므로 '검증됨' 한계 문구도 안 나옴
    assert "bash" in m_bad.runtime_note
    assert m_bad.next_hint and "bash" in m_bad.next_hint


def test_lint_items_absorbs_portability_when_runtime_present(monkeypatch):
    """2-C ↔ 1-C 분담: 코어는 무조건 이식성 경고, 앱은 실행기가 있으면 흡수(첫 화면 깨끗).

    흡수하지 않으면 bash 가 있는 정상 환경에서도 프리셋 첫 화면이 늘 경고로 시작해
    시드 신뢰가 깎이고 진짜 위험 신호가 묻힌다.
    """
    import harness_app.view_model as vmod
    from harness_app.view_model import lint_items

    st = BuilderState("demo", preset="safety-first")

    monkeypatch.setattr(vmod, "check_hook_runtimes", lambda ir: _fake_rt(ok=True))
    assert "hook-portability" not in {i.code for i in lint_items(st)}

    monkeypatch.setattr(vmod, "check_hook_runtimes", lambda ir: _fake_rt(ok=False))
    assert "hook-portability" in {i.code for i in lint_items(st)}


def _fake_rt(ok: bool):
    from harness_app.runtime_check import HookRuntimeVM

    if ok:
        return HookRuntimeVM(checked=1)
    return HookRuntimeVM(
        missing=("bash",),
        affected_titles=("시크릿 보호",),
        blocking_affected=True,
        checked=1,
        notes=("Windows 라면 Git for Windows(Git Bash)를 설치하면 함께 설치됩니다.",),
    )
