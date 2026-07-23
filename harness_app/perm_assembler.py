"""권한 패턴 조립기 (앱 계층 순수 로직) — 문법 없이 권한 규칙 만들기.

사용자 피드백: 권한 '대상 패턴' 칸에 `Bash(rm -rf:*)` 같은 걸 손으로 타이핑해야 함
(문법 모르면 못 씀). → 도구 고르기 + 평문 입력 + 동작 선택 → 올바른 패턴 문자열을 자동 조립.

코어 무수정: 산출은 parse_pattern(lint.py)·_permission_matches(simulate.py)가 이미 받는 기존
`pattern: str` 문자열뿐. 앱의 매칭은 접두(startswith) 기반이라 조립기는 중간 glob(`*`)을 피하고
끝의 `:*` 접두 시맨틱만 쓴다. 내보낸 패턴은 실제 Claude Code 문법으로도 유효.

정확도: 다중 에이전트 조사 + 적대 검증(2026-07-23)으로 확인. 검증이 잡은 함정 반영 —
`Bash(curl * | bash)`류(복합명령 분해로 발화 불가)·`Read(**/.env)` 단독(변형 미커버) 등은
시드에서 교정.
"""

from __future__ import annotations

from dataclasses import dataclass

from harness_core.ir.factory import create_component
from harness_core.ir.schema import PermissionRule


@dataclass(frozen=True)
class ToolSpec:
    tool: str  # 패턴에 쓰이는 도구명(Bash, Read, Edit, Write, WebFetch, PowerShell)
    label: str  # 콤보 표시(한국어)
    input_label: str  # 입력칸 라벨(명령어/경로/도메인)
    placeholder: str
    purpose: str  # 콤보 선택 시 힌트
    examples: tuple[str, ...]
    kind: str  # "command" | "path" | "domain" — 조립 방식·토글 결정


TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "Bash",
        "Bash — 셸 명령",
        "명령어",
        "예: git push --force  또는  rm -rf",
        "터미널 명령 실행을 통제합니다.",
        ("git push --force", "rm -rf", "npm run test", "sudo"),
        "command",
    ),
    ToolSpec(
        "Read",
        "Read — 파일 읽기",
        "경로",
        "예: **/.env  또는  ~/.ssh/**",
        "파일 읽기를 통제합니다. gitignore 식 경로(** = 하위 폴더 포함).",
        ("**/.env", "**/.env.*", "~/.ssh/**", "src/**"),
        "path",
    ),
    ToolSpec(
        "Edit",
        "Edit/Write — 파일 쓰기·수정",
        "경로",
        "예: .claude/**  또는  src/**",
        "파일 쓰기·수정을 통제합니다. (금지 시 Write·수정 함께 막으려면 아래 안내 참고)",
        (".claude/**", ".git/**", "src/**", "docs/*"),
        "path",
    ),
    ToolSpec(
        "WebFetch",
        "WebFetch — 웹 요청",
        "도메인",
        "예: github.com  또는  api.example.com",
        "HTTP 요청 도메인을 통제합니다.",
        ("github.com", "api.github.com", "internal.company.com"),
        "domain",
    ),
    ToolSpec(
        "PowerShell",
        "PowerShell — PS 명령",
        "명령어",
        "예: Remove-Item  또는  Get-ChildItem",
        "PowerShell 명령을 통제합니다(Windows).",
        ("Remove-Item", "Get-ChildItem"),
        "command",
    ),
)

_BY_TOOL: dict[str, ToolSpec] = {t.tool: t for t in TOOL_SPECS}

# 동작별 한국어 라벨·의미
ACTIONS = (
    ("allow", "허용", "자유 실행"),
    ("ask", "질문", "실행 전 물어봄"),
    ("deny", "금지", "차단"),
)


def compose_pattern(tool: str, text: str, prefix: bool, subdomain: bool = False) -> str:
    """도구·평문 입력 → 권한 패턴 문자열.

    command: prefix=True 면 `Tool(명령:*)`(이 명령으로 시작하는 모두), False 면 `Tool(명령)`(정확).
    path:    `Tool(경로)` 그대로(경로는 ** 로 범위 표현).
    domain:  `WebFetch(domain:호스트)` — subdomain 이면 `*.` 선두.
    빈 입력: `Tool`(도구 전체).
    """
    text = text.strip()
    if not text:
        return tool  # 도구 전면
    spec = _BY_TOOL.get(tool)
    kind = spec.kind if spec else "command"
    if kind == "domain":
        host = text.lstrip(".")
        if subdomain and not host.startswith("*."):
            host = "*." + host
        return f"WebFetch(domain:{host})"
    if kind == "path":
        return f"{tool}({text})"
    # command
    inner = f"{text}:*" if prefix else text
    return f"{tool}({inner})"


def match_explanation(tool: str, text: str, prefix: bool, subdomain: bool = False) -> str:
    """조립된 패턴이 '무엇에 걸리는지' 평문 설명(미리보기)."""
    text = text.strip()
    spec = _BY_TOOL.get(tool)
    kind = spec.kind if spec else "command"
    if not text:
        return f"{tool} 도구 전체"
    if kind == "domain":
        host = text.lstrip(".")
        if subdomain:
            return f"{host} 와 그 하위 도메인 전부에 대한 웹 요청"
        return f"정확히 {host} 도메인에 대한 웹 요청"
    if kind == "path":
        return f"경로가 '{text}' 에 해당하는 파일 (** = 하위 폴더 포함, .env 등 gitignore 식)"
    if prefix:
        return f"'{text}' 로 시작하는 모든 {tool} 명령"
    return f"정확히 '{text}' 명령만"


def _derive_title(action: str, tool: str, text: str) -> str:
    act = {"allow": "허용", "ask": "확인", "deny": "차단"}.get(action, action)
    subject = (text.strip() or f"{tool} 전체")[:40]
    return f"{subject} {act}"


def build_permission(
    action: str,
    tool: str,
    text: str,
    prefix: bool,
    subdomain: bool = False,
    layer: str = "permissions",
) -> PermissionRule:
    """조립 결과 → 검증된 PermissionRule(factory 기본값 + 조립 값)."""
    pattern = compose_pattern(tool, text, prefix, subdomain)
    base = create_component("permission-rule", layer)
    return base.model_copy(
        update={"action": action, "pattern": pattern, "title": _derive_title(action, tool, text)}
    )
