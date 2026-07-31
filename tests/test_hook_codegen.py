"""3-A 정합 실증 — "시뮬에서 막힌 것 = 산출물에서 막힘 = 런타임에서 막힘".

이 파일의 핵심은 test_parity_* — 한 케이스(sub/dir/.env)로 3자를 **동시에** 확인한다.
발견 A(hook 의 action·path_glob 미직렬화) 이전에는 시뮬만 차단이고 산출물엔 근거가 없었다.

opt-in 계약(ADR-0012): export_ir 기본 호출은 바이트 불변 — 그것도 여기서 고정한다.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from harness_core.export.export_ir import export_ir
from harness_core.export.hook_codegen import GUARD_MARK, needs_guard, with_guard
from harness_core.ir.factory import create_component
from harness_core.ir.presets import safety_first_preset
from harness_core.ir.schema import HarnessIR
from harness_core.sim.simulate import simulate

_BASH = shutil.which("bash")


def _script_of(ir: HarnessIR, *, enforce: bool) -> str:
    return next(f for f in export_ir(ir, enforce_hooks=enforce) if f.path.endswith(".sh")).content


def _run(script: str, path: str, tmp_path) -> int:
    p = tmp_path / "hook.sh"
    p.write_text(script, encoding="utf-8", newline="\n")
    payload = {"tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}}
    proc = subprocess.run(
        [_BASH, str(p)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
    )
    return proc.returncode


# --- opt-in 계약 (frozen 골든 보호) -------------------------------------------------


def test_default_export_bytes_unchanged():
    ir = safety_first_preset("demo")
    assert export_ir(ir) == export_ir(ir, enforce_hooks=False)
    assert GUARD_MARK not in _script_of(ir, enforce=False)  # 기본 경로엔 가드 없음


def test_enforced_export_adds_guard():
    ir = safety_first_preset("demo")
    assert GUARD_MARK in _script_of(ir, enforce=True)


def test_guard_is_not_duplicated_on_reexport():
    """이미 가드가 있는 본문에 또 씌우면 stdin 을 두 번 삼켜 훅이 망가진다."""
    ir = safety_first_preset("demo")
    hook = next(c for c in ir.components if c.kind == "hook")
    once = with_guard(hook)
    twice = with_guard(hook.model_copy(update={"script_body": once}))
    assert once == twice


def test_needs_guard_scope():
    ir = safety_first_preset("demo")
    hook = next(c for c in ir.components if c.kind == "hook")
    assert needs_guard(hook)  # deny + path_glob
    assert not needs_guard(hook.model_copy(update={"action": "warn"}))
    assert not needs_guard(hook.model_copy(update={"path_glob": None}))


# --- 정합 실증 (시뮬 = 산출물 = 런타임) ---------------------------------------------


@pytest.mark.skipif(_BASH is None, reason="bash 미존재")
@pytest.mark.parametrize(
    "path,blocked",
    [
        (".env", True),
        ("sub/dir/.env", True),  # ★ 결함 케이스: 예전엔 시뮬만 통과(과소 매칭)
        ("a/b/c/.env.local", True),
        ("src/app.js", False),
        ("environment.ts", False),  # 오탐 방지
    ],
)
def test_parity_sim_export_runtime(path, blocked, tmp_path):
    ir = safety_first_preset("demo")

    # ① 시뮬 판정
    sim = simulate(ir, {"tool": "Write", "path": path, "label": path})
    assert (sim["outcome"] == "blocked-by-hook") is blocked, ("시뮬", path, sim["outcome"])

    # ② 산출물: 가드가 실제로 들어있다
    script = _script_of(ir, enforce=True)
    assert GUARD_MARK in script

    # ③ 런타임: 그 스크립트를 실제로 실행한 종료코드
    code = _run(script, path, tmp_path)
    assert (code == 2) is blocked, ("런타임", path, code)


@pytest.mark.skipif(_BASH is None, reason="bash 미존재")
def test_user_body_still_receives_stdin(tmp_path):
    """가드가 stdin 을 삼켜 사용자 본문의 $(cat) 이 비면 기존 훅이 통째로 무력화된다.

    본문만으로 차단되는 경로(가드 정규식엔 안 걸리는)를 써서 되먹임이 실제로 되는지 본다.
    """
    base = safety_first_preset("demo")
    hook = create_component("hook", "guardrails").model_copy(
        update={
            "action": "deny",
            "path_glob": "**/never-match-me*",  # 가드는 통과시킴
            "script_name": "body.sh",
            "script_body": (
                "#!/usr/bin/env bash\n"
                "input=$(cat)\n"
                'if [ -z "$input" ]; then exit 9; fi\n'  # stdin 이 비면 9
                'case "$input" in *secret.txt*) exit 2;; esac\n'
                "exit 0\n"
            ),
        }
    )
    ir = HarnessIR(meta=base.meta, components=[hook])
    script = _script_of(ir, enforce=True)
    assert _run(script, "docs/readme.md", tmp_path) == 0  # 통과(9 면 stdin 유실)
    assert _run(script, "secret.txt", tmp_path) == 2  # 본문 판정이 살아있다


@pytest.mark.skipif(_BASH is None, reason="bash 미존재")
def test_generated_scripts_are_syntactically_valid(tmp_path):
    """전 프리셋 x enforce → bash -n 문법 검사(생성 코드가 깨지면 훅 전체가 죽는다)."""
    from harness_core.ir.presets import PRESETS

    for name, factory in PRESETS.items():
        for f in export_ir(factory("demo"), enforce_hooks=True):
            if not f.path.endswith(".sh"):
                continue
            p = tmp_path / f"{name}-{f.path.replace('/', '_')}"
            p.write_text(f.content, encoding="utf-8", newline="\n")
            proc = subprocess.run([_BASH, "-n", str(p)], capture_output=True)
            assert proc.returncode == 0, (name, f.path, proc.stderr.decode("utf-8", "replace"))
