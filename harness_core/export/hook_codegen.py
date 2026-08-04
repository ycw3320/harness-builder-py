"""deny 훅의 `path_glob` 을 실제 exit-2 가드로 코드젠 — 시뮬↔산출물 단일 생성기 (3-A).

발견 A: `export_ir` 는 `matcher`+`command` 만 settings.json 에 기록하고 `action(deny)`·
`path_glob` 은 simulate 전용 메타로 남겼다 → 화면의 "차단"이 산출물에서 보장되지 않았다
(실제 차단 여부는 오직 스크립트 exit code). Claude Code 의 settings.json 스키마에는
`path_glob` 을 담을 자리가 없으므로, 경로 조건은 **스크립트 안에서** 검사할 수밖에 없다.

단일 생성기: 가드가 쓰는 정규식은 시뮬레이터와 **같은** `glob_to_pattern` 산출물이다.
그래서 `(?:...)`(Python 전용, POSIX ERE 에 없음) 대신 `(...)` 로 생성한다 — 그렇지 않으면
grep -E 가 조용히 매칭에 실패해 새로운 거짓 안전을 만든다.

stdin 계약(실측으로 확정): 가드가 `$(cat)` 으로 payload 를 읽으면 뒤따르는 사용자 본문의
`input=$(cat)` 은 **빈 문자열**을 받는다(기존 훅이 통째로 무력화). 그래서 가드는 읽은 payload 를
사용자 본문 블록에 **되먹인다**. 파이프라인 마지막 명령의 종료코드가 스크립트 종료코드가 되므로
본문의 `exit 2` 도 그대로 전파된다.

opt-in(ADR-0012 준수): `export_ir(ir)` 기본 호출 결과는 바뀌지 않는다. 앱만
`enforce_hooks=True` 로 이 코드젠을 쓴다 → frozen 골든 바이트 불변.
"""

from __future__ import annotations

import re

from ..sim.simulate import glob_to_pattern

GUARD_MARK = "# [버클 자동 생성 가드]"


def needs_guard(hook) -> bool:
    """가드 대상 = 금지(deny)면서 경로 조건(path_glob)이 있는 훅."""
    return getattr(hook, "action", "") == "deny" and bool(getattr(hook, "path_glob", None))


def has_guard(body: str) -> bool:
    """이미 버클 가드가 붙은 본문인가 — **줄 시작**으로만 판정.

    단순 부분문자열(`GUARD_MARK in body`)이면 본문이 그 문자열을 인용·언급하기만 해도
    가드가 통째로 생략돼 '화면은 차단, 산출물은 무방비'가 된다(적대 검증 확정).
    """
    return any(line.startswith(GUARD_MARK) for line in (body or "").splitlines())


def _sh_single_quote(value: str) -> str:
    """작은따옴표 문자열로 안전하게 감싸기 — 내부 ' 는 '\\'' 로 탈출."""
    return "'" + value.replace("'", "'\\''") + "'"


# 생성 스크립트에 '사람이 읽는 텍스트'로 들어가는 값은 반드시 이걸 통과시킨다.
# 적대 검증(2026-07-24)에서 확정된 RCE 경로: path_glob 을 주석·echo 에 원문 보간하면
# 개행이 스크립트 줄로 편입돼 임의 명령이 실행됐다(공유 .harness.json 한 개로 성립,
# `bash -n` 도 통과해 문법 검사 그물을 그대로 빠져나갔다).
_TEXT_SAFE = re.compile(r"[^0-9A-Za-z_\-./*?\[\]{}가-힣 ]")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _display_safe(value: str, limit: int = 80) -> str:
    """주석·메시지에 넣어도 안전한 한 줄 문자열 — 제어문자·셸 메타문자 제거."""
    one_line = re.sub(r"\s+", " ", value or "")
    return _TEXT_SAFE.sub("", one_line)[:limit]


def guard_lines(path_glob: str) -> list[str]:
    """path_glob → exit-2 가드 코드(줄 목록). 정규식은 시뮬과 동일 소스.

    path_glob 은 **원문 그대로 코드에 들어가지 않는다** — 정규식으로 변환한 뒤
    작은따옴표로 감싸 grep 인자로만 전달하고, 사람이 읽는 자리에는 `_display_safe` 를 거친다.
    """
    # 방어 2겹(스키마 검증이 1겹): 스키마가 제어문자를 이미 막지만 `model_copy(update=...)` 는
    # 재검증을 하지 않으므로 코드젠에서 한 번 더 막는다. 조용히 제거하면 '의도와 다른 약한
    # 가드'가 만들어져 또 다른 거짓 안전이 되므로, **거부해서 소리 나게** 한다.
    if _CONTROL.search(path_glob or ""):
        raise ValueError("경로 조건에 줄바꿈·제어문자를 쓸 수 없습니다(스크립트 생성 안전 규칙)")
    pattern = glob_to_pattern(path_glob)
    shown = _display_safe(path_glob)
    return [
        f"{GUARD_MARK} 경로 조건: {shown}",
        "# 시뮬레이터와 똑같은 규칙으로 검사합니다 — 이 부분은 버클이 만들었습니다.",
        "__buckle_input=$(cat)",
        # 도구마다 경로 키가 다르다(Write/Edit=file_path, NotebookEdit=notebook_path).
        # 값 안의 이스케이프(\" 등)를 인식해 중간에 끊기지 않게 한다.
        "__buckle_path=$(printf '%s' \"$__buckle_input\" "
        '| grep -oE \'"(file_path|notebook_path)"[[:space:]]*:[[:space:]]*"([^"\\\\]|\\\\.)*"\' '
        "| head -1 | sed -E 's/^.*:[[:space:]]*\"//; s/\"$//')",
        # Windows 경로(백슬래시)를 슬래시로 정규화 — glob 은 슬래시 기준.
        r'__buckle_path="${__buckle_path//\\\\//}"',
        r'__buckle_path="${__buckle_path//\\//}"',
        # -i: Windows·macOS 기본 파일시스템은 대소문자를 구분하지 않는다. 구분해서 검사하면
        # `.ENV` 한 글자로 보호가 뚫리는데 실제로는 같은 파일이다(적대 검증 확정).
        f"if printf '%s' \"$__buckle_path\" | grep -qiE {_sh_single_quote(pattern)}; then",
        f'  echo "차단: 보호된 경로({shown})에는 쓸 수 없습니다" >&2',
        "  exit 2",
        "fi",
    ]


def with_guard(hook) -> str:
    """훅 → 가드가 앞에 붙은 스크립트 본문. 대상이 아니면 원본 그대로.

    사용자 본문은 **한 글자도 바꾸지 않고** 블록 안에 그대로 두고 payload 를 되먹인다
    (카탈로그·프리셋처럼 이미 완결된 스크립트를 덮어쓰지 않기 위함).
    """
    body = hook.script_body or ""
    if not needs_guard(hook) or has_guard(body):  # 이미 가드가 있으면 중복 생성 금지
        return body

    lines = body.splitlines()
    if lines and lines[0].startswith("#!"):
        # 본문 shebang 은 승격하지 않는다 — 가드는 bash 전용 문법(`${v//a/b}`)을 쓰므로
        # `#!/bin/sh` 를 그대로 쓰면 dash 에서 Bad substitution 으로 즉사한다(적대 검증 확정).
        # 원래 지정은 블록 안 주석으로 보존한다(본문은 파이프 서브셸에서 실행됨).
        lines[0] = f"# (원래 지정: {_display_safe(lines[0])} — 가드가 bash 를 요구해 대체됨)"

    out = ["#!/usr/bin/env bash", *guard_lines(hook.path_glob)]
    if any(line.strip() for line in lines):  # 본문이 있을 때만 되먹임 블록 생성
        out.append("# ↓ 사용자가 작성한 본문 — 표준입력으로 payload 를 그대로 받습니다.")
        out.append("printf '%s' \"$__buckle_input\" | {")
        out.extend(lines)
        out.append("}")
        # 경로 조건이 곧 이 훅의 '선언된 범위'다. 위 가드를 통과했다는 건 범위 밖이라는 뜻이므로,
        # 본문이 여기서 차단하면 화면(시뮬)의 '통과' 판정과 어긋난다 — 실제로 프리셋 본문의
        # `case "$path" in *.env*)` 가 `config/dev.environment.json` 류를 막아 정반대 판정을
        # 냈다(적대 검증 확정). 선언 범위를 권위로 삼아 범위 밖 차단은 통과시킨다.
        out.append("__buckle_rc=$?")
        out.append('if [ "$__buckle_rc" = "2" ]; then')
        out.append('  echo "참고: 경로 조건 밖이라 통과시킵니다(범위는 위 가드가 정합니다)" >&2')
        out.append("  exit 0")
        out.append("fi")
        out.append('exit "$__buckle_rc"')
    else:
        out.append("exit 0")
    return "\n".join(out)
