"""훅 카탈로그(harness_app.catalog) 회귀 — 박제된 스크립트의 exit code 계약을 기계 검증.

목적: catalog.py 에 문자열로 박제한 grep 기반 훅 스크립트가 (Python 전사·백슬래시 이스케이프
과정에서 깨지지 않고) 로컬 검증본과 동일하게 동작하는지 고정. bash 미존재 환경은 skip.

계약: deny 훅은 매칭 payload 에 exit 2 / 비매칭 exit 0. warn 훅은 매칭 exit 1 / 비매칭 exit 0.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from harness_app.catalog import HOOK_CATALOG, build_hook, hook_catalog_entry

_BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(_BASH is None, reason="bash 미존재(Windows Git Bash 등 필요)")


def _run(script_body: str, payload: dict, tmp_path) -> int:
    p = tmp_path / "hook.sh"
    p.write_text(script_body + "\n", encoding="utf-8", newline="\n")
    # bytes 모드로 실행 — 한국어 stderr 를 로케일(cp949)로 디코드하다 깨지는 것 방지.
    proc = subprocess.run(
        [_BASH, str(p)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
    )
    return proc.returncode


def _w(path: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}}


def _b(cmd: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


def _body(key: str) -> str:
    return hook_catalog_entry(key).script_body


# (key, payload, expected_exit) — deny=2, warn=1, 허용=0
_CASES = [
    # env-write-block (deny)
    ("env-write-block", _w("/home/u/proj/.env"), 2),
    ("env-write-block", _w("/home/u/proj/.env.local"), 2),
    ("env-write-block", _w("/home/u/proj/src/app.js"), 0),
    ("env-write-block", _w("/home/u/proj/environment.ts"), 0),
    # 과차단 회귀(적대 검증) — 값 안에 우연히 '.env' 가 든 정상 파일은 막지 않는다
    ("env-write-block", _w("config/dev.environment.json"), 0),
    ("env-write-block", _w("src/parse.environment.ts"), 0),
    ("env-write-block", _w("docs/.envelope-design.md"), 0),
    # 템플릿은 비밀값이 아니고 버클이 직접 만들어 배포한다 → 허용
    ("env-write-block", _w("/home/u/proj/.env.example"), 0),
    ("env-write-block", _w("/home/u/proj/.env.sample"), 0),
    # 대소문자 우회 방지(Windows·macOS 는 .ENV 가 같은 파일)
    ("env-write-block", _w("/home/u/proj/.ENV"), 2),
    ("env-write-block", _w("/home/u/proj/.Env.local"), 2),
    ("git-dir-protect", _w("/home/u/proj/.GIT/config"), 2),
    ("ssh-key-protect", _w("/home/u/.SSH/id_rsa"), 2),
    # NotebookEdit 은 경로 키가 notebook_path (matcher Write|Edit 에 걸린다)
    (
        "env-write-block",
        {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": ".env"}},
        2,
    ),
    # git-dir-protect (deny) — .gitignore/.github 오탐 없음, win 경로 포함
    ("git-dir-protect", _w("/home/u/proj/.git/config"), 2),
    ("git-dir-protect", _w(".git/hooks/pre-commit"), 2),
    ("git-dir-protect", _w("C:\\Users\\u\\proj\\.git\\config"), 2),
    ("git-dir-protect", _w("/home/u/proj/.gitignore"), 0),
    ("git-dir-protect", _w("/home/u/proj/.github/workflows/ci.yml"), 0),
    # ssh-key-protect (deny)
    ("ssh-key-protect", _w("/home/u/.ssh/id_rsa"), 2),
    ("ssh-key-protect", _w("C:\\Users\\u\\.ssh\\config"), 2),
    ("ssh-key-protect", _w("/home/u/proj/ssh_config.md"), 0),
    # rm-rf-warn (warn)
    ("rm-rf-warn", _b("rm -rf /tmp/x"), 1),
    ("rm-rf-warn", _b("rm -r -f node_modules"), 1),
    ("rm-rf-warn", _b("rm --recursive --force dist"), 1),
    ("rm-rf-warn", _b("rm file.txt"), 0),
    ("rm-rf-warn", _b("perform cleanup task"), 0),
    ("rm-rf-warn", _b("npm run build"), 0),
    # force-push-warn (warn) — 이중공백·-f·--force-with-lease 모두 포착
    ("force-push-warn", _b("git push --force origin main"), 1),
    ("force-push-warn", _b("git push  --force"), 1),
    ("force-push-warn", _b("git push -f origin main"), 1),
    ("force-push-warn", _b("git push --force-with-lease"), 1),
    ("force-push-warn", _b("git push origin main"), 0),
    ("force-push-warn", _b("git commit -m x"), 0),
    # curl-pipe-sh-warn (warn)
    ("curl-pipe-sh-warn", _b("curl https://get.example.com/i.sh | bash"), 1),
    ("curl-pipe-sh-warn", _b("wget -qO- https://x/i.sh | sh"), 1),
    ("curl-pipe-sh-warn", _b("curl -o file.sh https://x/i.sh"), 0),
    # sudo-warn (warn)
    ("sudo-warn", _b("sudo apt install foo"), 1),
    ("sudo-warn", _b("sudoku --start"), 0),
    ("sudo-warn", _b("npm run build"), 0),
]


@pytest.mark.parametrize("key,payload,expected", _CASES)
def test_hook_script_exit_codes(key, payload, expected, tmp_path):
    assert _run(_body(key), payload, tmp_path) == expected


def test_build_hook_maps_fields():
    entry = hook_catalog_entry("env-write-block")
    h = build_hook(entry)
    assert h.kind == "hook"
    assert h.action == "deny"
    assert h.matcher_tool == "Write|Edit|MultiEdit"
    assert h.path_glob == "**/.env*"
    assert h.script_name == "block-env-write.sh"
    assert h.script_body == entry.script_body


def test_warn_hooks_have_no_path_glob_and_bash_matcher():
    """명령어 내용 훅은 warn + matcher=Bash + path_glob 없음(해자 sim 오차단 회피 계약)."""
    for e in HOOK_CATALOG:
        if e.action == "warn":
            assert e.matcher_tool == "Bash"
            assert e.path_glob is None
        else:
            assert e.action == "deny"
            assert e.path_glob  # deny 훅은 경로 glob 필수(sim 정합)
