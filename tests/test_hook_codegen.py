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

    본문이 payload 를 실제로 받았는지는 2 가 아닌 고유 종료코드로 확인한다
    (2 는 아래 test_path_glob_is_authoritative_scope 가 다루는 '범위 밖 차단'이라 강등된다).
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
                'case "$input" in *secret.txt*) exit 7;; esac\n'  # 본문이 payload 를 봤다는 신호
                "exit 0\n"
            ),
        }
    )
    ir = HarnessIR(meta=base.meta, components=[hook])
    script = _script_of(ir, enforce=True)
    assert _run(script, "docs/readme.md", tmp_path) == 0  # 통과(9 면 stdin 유실)
    assert _run(script, "secret.txt", tmp_path) == 7  # 본문이 payload 를 받았고 종료코드도 전파


@pytest.mark.skipif(_BASH is None, reason="bash 미존재")
def test_path_glob_is_authoritative_scope(tmp_path):
    """경로 조건 = 선언된 범위. 범위 밖에서 본문이 차단하면 화면(시뮬)과 어긋난다.

    실제로 프리셋 본문의 `case "$path" in *.env*)` 가 `config/dev.environment.json` 류를
    막아 시뮬(통과)과 정반대 판정을 냈다(적대 검증 확정). 범위를 권위로 삼아 통과시킨다.
    """
    ir = safety_first_preset("demo")
    script = _script_of(ir, enforce=True)
    for path in ("config/dev.environment.json", "src/parse.environment.ts", "release.env.notes.md"):
        assert _run(script, path, tmp_path) == 0, path
        assert simulate(ir, {"tool": "Write", "path": path, "label": path})["outcome"] == "allowed"
    # 범위 안은 그대로 차단
    assert _run(script, "sub/dir/.env", tmp_path) == 2


# --- 적대 검증(2026-07-24)이 확정한 공격 벡터 회귀 --------------------------------
#
# 아래는 전부 실제로 재현됐던 결함이다. `bash -n` 문법 검사는 이 중 어느 것도 잡지 못했다.


def _hook(path_glob: str, body: str = "#!/usr/bin/env bash\ninput=$(cat)\nexit 0\n"):
    return create_component("hook", "guardrails").model_copy(
        update={"action": "deny", "path_glob": path_glob, "script_body": body}
    )


def test_path_glob_control_chars_rejected_at_schema():
    """1겹: 오염된 path_glob 은 로드 자체가 거부된다(공유 .harness.json 공급망 차단)."""
    from pydantic import ValidationError

    from harness_core.ir.schema import Hook

    with pytest.raises(ValidationError):
        Hook(
            id="x",
            layer="guardrails",
            title="t",
            involvement="auto",
            enabled=True,
            event="PreToolUse",
            matcherTool="Write",
            pathGlob="**/.env*\ntouch OWNED\nexit 0\n# ",
            action="deny",
            scriptName="a.sh",
            scriptBody="#!/usr/bin/env bash\nexit 0",
        )


def test_codegen_rejects_control_chars():
    """2겹: model_copy 는 재검증을 안 하므로 코드젠에서도 막는다 — 조용히 약화 금지."""
    with pytest.raises(ValueError):
        with_guard(_hook("**/.env*\ntouch OWNED\nexit 0\n# "))


@pytest.mark.skipif(_BASH is None, reason="bash 미존재")
def test_quote_in_glob_does_not_break_script(tmp_path):
    """큰따옴표가 든 glob 이 스크립트 문법을 깨 전면 차단/전면 통과가 되면 안 된다."""
    script = with_guard(_hook('**/say"hi*'))
    assert _run(script, "src/app.js", tmp_path) == 0


@pytest.mark.skipif(_BASH is None, reason="bash 미존재")
@pytest.mark.parametrize("path", [".ENV", "sub/.Env", "SRC/.EnV.local"])
def test_case_insensitive_paths_blocked(path, tmp_path):
    """Windows·macOS 는 대소문자를 구분하지 않아 `.ENV` 쓰기가 실제 `.env` 를 덮어쓴다."""
    ir = safety_first_preset("demo")
    assert _run(_script_of(ir, enforce=True), path, tmp_path) == 2
    # 시뮬도 같은 판정이어야 정합이 유지된다
    assert simulate(ir, {"tool": "Write", "path": path, "label": path})["outcome"] == (
        "blocked-by-hook"
    )


def test_guard_mark_mention_does_not_skip_guard():
    """본문이 마커 문자열을 '언급'만 해도 가드가 생략되면 화면=차단/산출물=무방비."""
    body = '#!/usr/bin/env bash\necho "# [버클 자동 생성 가드] 형식 설명"\nexit 0\n'
    assert GUARD_MARK in body  # 부분문자열로는 이미 존재
    assert "grep -qiE" in with_guard(_hook("**/.env*", body))  # 그래도 가드는 붙는다


def test_body_shebang_is_not_promoted():
    """가드는 bash 전용 문법을 쓴다 — 본문의 `#!/bin/sh` 를 승격하면 dash 에서 즉사."""
    out = with_guard(_hook("**/.env*", "#!/bin/sh\ninput=$(cat)\nexit 0\n"))
    assert out.splitlines()[0] == "#!/usr/bin/env bash"


@pytest.mark.skipif(_BASH is None, reason="bash 미존재")
def test_notebook_path_key_is_also_checked(tmp_path):
    """matcher(Write|Edit)에는 걸리는 NotebookEdit 은 경로 키가 notebook_path 다."""
    script = _script_of(safety_first_preset("demo"), enforce=True)
    p = tmp_path / "h.sh"
    p.write_text(script, encoding="utf-8", newline="\n")
    payload = {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": ".env"}}
    proc = subprocess.run(
        [_BASH, str(p)], input=json.dumps(payload).encode("utf-8"), capture_output=True
    )
    assert proc.returncode == 2


@pytest.mark.skipif(_BASH is None, reason="bash 미존재")
@pytest.mark.parametrize(
    "path,blocked",
    [('dir"x/.env', True), ('my"docs/readme.md', False)],
)
def test_json_escaped_quotes_in_path(path, blocked, tmp_path):
    """경로 안의 따옴표에서 추출이 잘리면 과차단과 우회가 동시에 생긴다."""
    code = _run(_script_of(safety_first_preset("demo"), enforce=True), path, tmp_path)
    assert (code == 2) is blocked


def test_glob_question_mark_is_literalized():
    """glob 의 `?`(한 글자)가 정규식 `?`(0~1회)로 새면 의도보다 넓게 매칭된다."""
    from harness_core.sim.simulate import glob_to_pattern

    assert glob_to_pattern("**/secrets?.json") == r"^(.*/)?secrets\?\.json$"


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
