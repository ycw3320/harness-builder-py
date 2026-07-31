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

from ..sim.simulate import glob_to_pattern

GUARD_MARK = "# [버클 자동 생성 가드]"


def needs_guard(hook) -> bool:
    """가드 대상 = 금지(deny)면서 경로 조건(path_glob)이 있는 훅."""
    return getattr(hook, "action", "") == "deny" and bool(getattr(hook, "path_glob", None))


def _sh_single_quote(value: str) -> str:
    """작은따옴표 문자열로 안전하게 감싸기 — 내부 ' 는 '\\'' 로 탈출."""
    return "'" + value.replace("'", "'\\''") + "'"


def guard_lines(path_glob: str) -> list[str]:
    """path_glob → exit-2 가드 코드(줄 목록). 정규식은 시뮬과 동일 소스."""
    pattern = glob_to_pattern(path_glob)
    return [
        f"{GUARD_MARK} 경로 조건: {path_glob}",
        "# 시뮬레이터와 똑같은 규칙으로 검사합니다 — 이 부분은 버클이 만들었습니다.",
        "__buckle_input=$(cat)",
        "__buckle_path=$(printf '%s' \"$__buckle_input\" "
        '| grep -oE \'"file_path"[[:space:]]*:[[:space:]]*"[^"]*"\' '
        "| head -1 | grep -oE '\"[^\"]*\"$' | tr -d '\"')",
        # Windows 경로(백슬래시)를 슬래시로 정규화 — glob 은 슬래시 기준.
        r'__buckle_path="${__buckle_path//\\\\//}"',
        r'__buckle_path="${__buckle_path//\\//}"',
        f"if printf '%s' \"$__buckle_path\" | grep -qE {_sh_single_quote(pattern)}; then",
        f'  echo "차단: {path_glob} 에 해당하는 경로에는 쓸 수 없습니다" >&2',
        "  exit 2",
        "fi",
    ]


def with_guard(hook) -> str:
    """훅 → 가드가 앞에 붙은 스크립트 본문. 대상이 아니면 원본 그대로.

    사용자 본문은 **한 글자도 바꾸지 않고** 블록 안에 그대로 두고 payload 를 되먹인다
    (카탈로그·프리셋처럼 이미 완결된 스크립트를 덮어쓰지 않기 위함).
    """
    body = hook.script_body or ""
    if not needs_guard(hook) or GUARD_MARK in body:  # 이미 가드가 있으면 중복 생성 금지
        return body

    lines = body.splitlines()
    shebang = "#!/usr/bin/env bash"
    if lines and lines[0].startswith("#!"):
        shebang, lines = lines[0], lines[1:]

    out = [shebang, *guard_lines(hook.path_glob)]
    if any(line.strip() for line in lines):  # 본문이 있을 때만 되먹임 블록 생성
        out.append("# ↓ 사용자가 작성한 본문 — 표준입력으로 payload 를 그대로 받습니다.")
        out.append("printf '%s' \"$__buckle_input\" | {")
        out.extend(lines)
        out.append("}")
    else:
        out.append("exit 0")
    return "\n".join(out)
