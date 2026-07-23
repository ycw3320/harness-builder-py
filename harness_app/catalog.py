"""MCP 서버 카탈로그 (앱 계층 순수 데이터) — '빈 칸에 뭘 넣을지 모름' 해소.

유명 MCP 서버를 고르면 command·args·env 가 자동 채워지고, 사용자는 (a)경로형 인자와
(b).env 의 실제 비밀값만 넣으면 된다. 문법·패키지명을 몰라도 됨.

코어 무수정: McpServer 스키마(server_name/command/args/env, extra=forbid)와 .mcp.json 산출
바이트는 frozen 골든이라, 카탈로그는 그 4필드만 채우는 값만 만든다. 원격(http/sse·OAuth)
방식은 frozen export 가 표현 못 하므로 이번 범위 밖(로드맵 3-C).

정확도: 2026-07 다중 에이전트 조사 + 적대 검증으로 확인한 10종만 시드(아카이브된 구
@modelcontextprotocol/server-* 는 벤더/공식 후속으로 정정). postgres·slack 등 서드파티·
스쿼팅 위험 서버는 '직접 입력' 경로로 남김.
"""

from __future__ import annotations

from dataclasses import dataclass

from harness_core.ir.factory import create_component
from harness_core.ir.schema import Hook, McpServer

CATALOG_LAST_VERIFIED = "2026-07"


@dataclass(frozen=True)
class CatalogEnv:
    key: str  # 환경변수 이름(대문자) — export 시 값은 ${KEY}, 실제 값은 .env
    hint: str  # 이 값을 어디서 얻는지(한국어)
    required: bool  # True 만 자동 프리필(선택 키는 미리 넣지 않아 .env.example 정확 유지)


@dataclass(frozen=True)
class CatalogEntry:
    key: str  # 서버 별칭 = .mcp.json 의 키
    display_name: str
    purpose: str  # 한국어 한 줄
    command: str
    args: tuple[str, ...]
    env: tuple[CatalogEnv, ...] = ()
    note: str = ""  # 설치 요건·주의(예: Docker 필요)
    cost_note: str = ""  # 과금 안내(있을 때만)

    @property
    def required_keys(self) -> tuple[str, ...]:
        return tuple(e.key for e in self.env if e.required)


# 경로형 인자 자리표시자 — 사용자가 실값으로 바꿔야 함이 한눈에 보이게(각괄호 유지).
_PATH_DIR = "<허용할 폴더 경로 — 예: C:\\projects\\my-app>"
_PATH_REPO = "<Git 저장소 경로 — 예: C:\\projects\\my-app>"

MCP_CATALOG: tuple[CatalogEntry, ...] = (
    CatalogEntry(
        key="filesystem",
        display_name="Filesystem — 로컬 파일",
        purpose="허용한 폴더 안의 파일을 읽고 쓰고 검색합니다.",
        command="npx",
        args=("-y", "@modelcontextprotocol/server-filesystem", _PATH_DIR),
        note="Node 필요(npx). 마지막 인자에 접근을 허용할 폴더 경로를 넣으세요 — 그 밖은 차단됩니다.",
    ),
    CatalogEntry(
        key="git",
        display_name="Git — 로컬 저장소",
        purpose="로컬 Git 저장소의 상태·diff·로그·커밋을 다룹니다.",
        command="uvx",
        args=("mcp-server-git", "--repository", _PATH_REPO),
        note="Python 실행기 uv 필요(uvx). --repository 뒤에 저장소 경로를 넣으세요.",
    ),
    CatalogEntry(
        key="fetch",
        display_name="Fetch — 웹 페이지 읽기",
        purpose="URL 을 가져와 마크다운으로 변환해 읽기 좋게 돌려줍니다.",
        command="uvx",
        args=("mcp-server-fetch",),
        note="uv 필요. 키·설정 없이 바로 동작(robots.txt 존중).",
    ),
    CatalogEntry(
        key="github",
        display_name="GitHub — 이슈·PR·코드",
        purpose="이슈·PR·리포지토리·코드 검색 등 GitHub 작업을 수행합니다.",
        command="docker",
        args=(
            "run",
            "-i",
            "--rm",
            "-e",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server",
        ),
        env=(
            CatalogEnv(
                "GITHUB_PERSONAL_ACCESS_TOKEN",
                "GitHub > Settings > Developer settings > Personal access tokens 에서 발급(fine-grained 권장).",
                True,
            ),
        ),
        note="Docker 필요(공식 github/github-mcp-server 이미지). 구 server-github 는 2025 아카이브됨.",
    ),
    CatalogEntry(
        key="context7",
        display_name="Context7 — 최신 라이브러리 문서",
        purpose="라이브러리·프레임워크의 버전별 공식 문서·예제를 실시간 주입합니다.",
        command="npx",
        args=("-y", "@upstash/context7-mcp"),
        note="Node 필요. 키 없이 동작(요청 한도만 낮음). 키를 쓰려면 args 에 --api-key ${CONTEXT7_API_KEY} 추가.",
    ),
    CatalogEntry(
        key="playwright",
        display_name="Playwright — 브라우저 자동화",
        purpose="실제 브라우저로 페이지 탐색·클릭·폼입력해 프론트엔드를 검증합니다.",
        command="npx",
        args=("@playwright/mcp@latest",),
        note="Node 필요(Microsoft 공식). 언스코프드 playwright-mcp 는 사칭 위험 — @playwright/mcp 를 쓰세요.",
    ),
    CatalogEntry(
        key="brave-search",
        display_name="Brave Search — 웹 검색",
        purpose="Brave 검색 API 로 웹·뉴스·이미지·지역 검색을 수행합니다.",
        command="npx",
        args=("-y", "@brave/brave-search-mcp-server"),
        env=(CatalogEnv("BRAVE_API_KEY", "brave.com/search/api 대시보드에서 발급.", True),),
        cost_note="2026-02 무료티어 폐지 — 월 $5 크레딧(약 1천 쿼리) 후 종량제 과금 발생 가능.",
    ),
    CatalogEntry(
        key="memory",
        display_name="Memory — 장기 기억",
        purpose="지식그래프에 정보를 저장/조회해 세션 간 장기 메모리를 제공합니다.",
        command="npx",
        args=("-y", "@modelcontextprotocol/server-memory"),
        note="Node 필요. 키 불필요. 로컬 JSON 파일에 그래프를 영속화.",
    ),
    CatalogEntry(
        key="sequential-thinking",
        display_name="Sequential Thinking — 단계 추론",
        purpose="복잡한 문제를 단계별 사고로 분해·수정·분기하도록 돕습니다.",
        command="npx",
        args=("-y", "@modelcontextprotocol/server-sequential-thinking"),
        note="Node 필요. 외부 자격증명 불필요.",
    ),
    CatalogEntry(
        key="time",
        display_name="Time — 시간·타임존",
        purpose="현재 시각 조회와 타임존 간 시간 변환을 제공합니다.",
        command="uvx",
        args=("mcp-server-time", "--local-timezone", "Asia/Seoul"),
        note="uv 필요. --local-timezone 미지정 시 시스템 타임존 자동 감지.",
    ),
)

_BY_KEY: dict[str, CatalogEntry] = {e.key: e for e in MCP_CATALOG}


def catalog_entry(server_key: str) -> CatalogEntry | None:
    """카드의 server_name 으로 카탈로그 항목 역참조(자동채움 카드 인식용)."""
    return _BY_KEY.get(server_key)


def build_mcp(entry: CatalogEntry, layer: str = "mcp") -> McpServer:
    """카탈로그 항목 → 검증된 McpServer(factory 기본값 + 카탈로그 값 채움).

    필수 env 키만 ${KEY} 로 프리필(선택 키는 제외해 .env.example 이 정확). 실제 비밀값은
    카드가 아니라 생성되는 .env 에 넣는다.
    """
    base = create_component("mcp-server", layer)
    return base.model_copy(
        update={
            "title": entry.display_name,
            "server_name": entry.key,
            "command": entry.command,
            "args": list(entry.args),
            "env": {e.key: f"${{{e.key}}}" for e in entry.env if e.required},
        }
    )


# =====================================================================================
# 훅(가드레일) 카탈로그 — 검증된 보호 훅을 한 번에 추가('빈 스크립트에 뭘 쓸지 모름' 해소)
# =====================================================================================
#
# 모든 스크립트는 **jq 없이 grep 기반**(Windows Git Bash 에 jq 미설치 → jq 의존 훅은 exit 127
# 로 fail-OPEN 하는 함정을 회피). 프리셋 block-secrets.sh 와 동일 계열. 각 스크립트는 가짜
# tool_input payload 로 exit code 계약을 로컬 검증했고(tests/test_hook_catalog.py 가 동일
# 검증을 회귀로 고정), 적대 검증(2026-07-23)이 통과시킨 것만 시드.
#
# **시뮬레이터 정합(해자 sim≡실제):** 코어 simulate 는 훅을 matcher_tool(도구명) + path_glob
# (경로) 로만 판정하고 '명령어 내용'은 못 본다. 따라서:
#   - 경로 기반 위험(.env/.git/.ssh 쓰기) → action="deny" + path_glob → sim 이 정확히 차단 재현.
#   - 명령어 내용 위험(rm -rf/force push/curl|sh/sudo) → deny 로 하면 matcher=Bash 라 sim 이
#     '모든 Bash 차단'으로 오표시됨. 그래서 action="warn"(sim 은 warn 을 무시 → '허용'으로 정직
#     표시, 실제 CC 는 stderr 경고 후 진행). 완전 차단이 필요하면 권한 규칙 Bash(...) 금지로 유도.


@dataclass(frozen=True)
class HookCatalogEntry:
    key: str
    display_name: str
    purpose: str  # 한 줄 한국어
    protects: str  # 무엇을 지키나(평문)
    matcher_tool: str  # sim·export 공용 도구 regex(예: "Write|Edit|MultiEdit", "Bash")
    action: str  # "deny"(차단) | "warn"(경고만, 비차단)
    path_glob: str | None  # deny 경로훅만 설정 — sim 이 이 glob 로 차단 재현
    script_name: str
    script_body: str
    event: str = "PreToolUse"
    note: str = ""

    @property
    def is_block(self) -> bool:
        return self.action == "deny"


# --- 스크립트 본문(로컬 exit-code 검증 완료본과 바이트 동일) ---

_HOOK_ENV_WRITE = "\n".join(
    [
        "#!/usr/bin/env bash",
        "# .env* 파일 쓰기 차단 — 시크릿 보호",
        "input=$(cat)",
        'path=$(printf \'%s\' "$input" | grep -oE \'"file_path"[[:space:]]*:[[:space:]]*"[^"]*"\' | head -1)',
        'case "$path" in',
        '  *.env*) echo "차단: .env 파일에는 쓸 수 없습니다 (시크릿 보호). 값은 이미 만들어진 .env 에 직접 넣으세요." >&2; exit 2;;',
        "esac",
        "exit 0",
    ]
)

# .git/·.ssh/ 훅은 파일경로 '값'만 뽑아(백슬래시→슬래시 정규화) 디렉터리 경계로 정확 판정
# — .gitignore/.github 등 유사 이름 오탐 방지.
_EXTRACT_PATH_VALUE = (
    'val=$(printf \'%s\' "$input" | grep -oE \'"file_path"[[:space:]]*:[[:space:]]*"[^"]*"\''
    " | head -1 | grep -oE '\"[^\"]*\"$' | tr -d '\"')"
)

_HOOK_GIT_DIR = "\n".join(
    [
        "#!/usr/bin/env bash",
        "# .git/ 내부 파일 쓰기 차단 — 저장소 무결성 보호(.gitignore 등 일반 파일은 허용)",
        "input=$(cat)",
        _EXTRACT_PATH_VALUE,
        r'path="${val//\\\\//}"',
        r'path="${path//\\//}"',
        'case "/$path" in',
        '  */.git/*) echo "차단: .git 내부 파일은 직접 수정할 수 없습니다 (git 명령을 사용하세요)." >&2; exit 2;;',
        "esac",
        "exit 0",
    ]
)

_HOOK_SSH_KEY = "\n".join(
    [
        "#!/usr/bin/env bash",
        "# .ssh/ 개인키·설정 쓰기 차단 — 자격증명 보호",
        "input=$(cat)",
        _EXTRACT_PATH_VALUE,
        r'path="${val//\\\\//}"',
        r'path="${path//\\//}"',
        'case "/$path" in',
        '  */.ssh/*) echo "차단: ~/.ssh 안의 키·설정은 수정할 수 없습니다 (자격증명 보호)." >&2; exit 2;;',
        "esac",
        "exit 0",
    ]
)

_EXTRACT_COMMAND = 'cmd=$(printf \'%s\' "$input" | grep -oE \'"command"[[:space:]]*:[[:space:]]*"[^"]*"\' | head -1)'

_HOOK_RM_RF = "\n".join(
    [
        "#!/usr/bin/env bash",
        "# 재귀·강제 삭제(rm -rf 등) 경고 — 차단하지 않고 주의만(비가역 삭제 재고 유도)",
        "input=$(cat)",
        _EXTRACT_COMMAND,
        'case "$cmd" in',
        '  *"rm "*|*"rm -"*)',
        "    if printf '%s' \"$cmd\" | grep -qE 'rm[[:space:]]+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|-r[[:space:]]+-f|-f[[:space:]]+-r|--recursive|--force)'; then",
        '      echo "경고: 재귀·강제 삭제(rm -rf)는 비가역입니다. 대상 경로를 다시 확인하세요." >&2',
        "      exit 1",
        "    fi",
        "    ;;",
        "esac",
        "exit 0",
    ]
)

_HOOK_FORCE_PUSH = "\n".join(
    [
        "#!/usr/bin/env bash",
        "# git 강제 푸시 경고 — 원격 히스토리 덮어쓰기 위험을 알림(차단 안 함)",
        "input=$(cat)",
        _EXTRACT_COMMAND,
        "if printf '%s' \"$cmd\" | grep -qE 'git[[:space:]]+push'; then",
        "  if printf '%s' \"$cmd\" | grep -qE '(--force|[[:space:]]-f([[:space:]]|$))'; then",
        '    echo "경고: 강제 푸시는 원격 히스토리를 덮어씁니다. --force-with-lease 를 쓰거나 팀과 확인하세요." >&2',
        "    exit 1",
        "  fi",
        "fi",
        "exit 0",
    ]
)

_HOOK_CURL_PIPE = "\n".join(
    [
        "#!/usr/bin/env bash",
        "# 원격 스크립트 즉시 실행(curl|sh) 경고 — 검증 없는 코드 실행 위험 알림",
        "input=$(cat)",
        _EXTRACT_COMMAND,
        "if printf '%s' \"$cmd\" | grep -qE '(curl|wget)[^|]*\\|[[:space:]]*(sudo[[:space:]]+)?(sh|bash|zsh)'; then",
        '  echo "경고: 내려받은 스크립트를 곧바로 셸에 파이프하고 있습니다. 내용을 먼저 저장·검토하세요." >&2',
        "  exit 1",
        "fi",
        "exit 0",
    ]
)

_HOOK_SUDO = "\n".join(
    [
        "#!/usr/bin/env bash",
        "# sudo 권한 상승 경고 — 시스템 전역 변경 주의 알림(차단 안 함)",
        "input=$(cat)",
        _EXTRACT_COMMAND,
        "if printf '%s' \"$cmd\" | grep -qE '(^|[;&|[:space:]\"])sudo[[:space:]]'; then",
        '  echo "경고: sudo 는 시스템 전역을 바꿉니다. 이 명령이 꼭 관리자 권한이어야 하는지 확인하세요." >&2',
        "  exit 1",
        "fi",
        "exit 0",
    ]
)


HOOK_CATALOG: tuple[HookCatalogEntry, ...] = (
    HookCatalogEntry(
        key="env-write-block",
        display_name=".env 시크릿 쓰기 차단",
        purpose=".env·.env.* 파일에 대한 쓰기를 실제로 막습니다.",
        protects="API 키·토큰·비밀번호가 담기는 .env 파일 보호",
        matcher_tool="Write|Edit|MultiEdit",
        action="deny",
        path_glob="**/.env*",
        script_name="block-env-write.sh",
        script_body=_HOOK_ENV_WRITE,
        note="시뮬레이터 시연에서 즉시 차단으로 확인됩니다.",
    ),
    HookCatalogEntry(
        key="git-dir-protect",
        display_name=".git/ 저장소 내부 보호",
        purpose=".git 폴더 내부 파일 수정을 막습니다(.gitignore 등 일반 파일은 허용).",
        protects="git 명령을 우회한 저장소 무결성 훼손 방지",
        matcher_tool="Write|Edit|MultiEdit",
        action="deny",
        path_glob="**/.git/**",
        script_name="protect-git-dir.sh",
        script_body=_HOOK_GIT_DIR,
    ),
    HookCatalogEntry(
        key="ssh-key-protect",
        display_name="~/.ssh 키·설정 보호",
        purpose="~/.ssh 안의 개인키·설정 파일 쓰기를 막습니다.",
        protects="SSH 개인키·known_hosts·config 등 자격증명 보호",
        matcher_tool="Write|Edit|MultiEdit",
        action="deny",
        path_glob="**/.ssh/**",
        script_name="protect-ssh-keys.sh",
        script_body=_HOOK_SSH_KEY,
    ),
    HookCatalogEntry(
        key="rm-rf-warn",
        display_name="rm -rf 위험 삭제 경고",
        purpose="재귀·강제 삭제 명령에 경고를 띄웁니다(차단은 하지 않음).",
        protects="비가역 대량 삭제 전 재고 유도",
        matcher_tool="Bash",
        action="warn",
        path_glob=None,
        script_name="warn-rm-rf.sh",
        script_body=_HOOK_RM_RF,
        note="경고만 하고 진행합니다. 완전 차단은 권한 규칙 Bash(rm:*) 금지로 설정하세요.",
    ),
    HookCatalogEntry(
        key="force-push-warn",
        display_name="git 강제 푸시 경고",
        purpose="git push --force / -f 에 경고를 띄웁니다(차단은 하지 않음).",
        protects="원격 히스토리 덮어쓰기 사고 예방",
        matcher_tool="Bash",
        action="warn",
        path_glob=None,
        script_name="warn-force-push.sh",
        script_body=_HOOK_FORCE_PUSH,
        note="경고만 하고 진행합니다. 완전 차단은 권한 규칙 Bash(git push --force:*) 금지로 설정하세요.",
    ),
    HookCatalogEntry(
        key="curl-pipe-sh-warn",
        display_name="curl | sh 원격 실행 경고",
        purpose="내려받은 스크립트를 곧바로 셸에 파이프하는 명령에 경고합니다.",
        protects="검증 없는 원격 코드 실행 위험 인지",
        matcher_tool="Bash",
        action="warn",
        path_glob=None,
        script_name="warn-curl-pipe-sh.sh",
        script_body=_HOOK_CURL_PIPE,
        note="경고만 하고 진행합니다.",
    ),
    HookCatalogEntry(
        key="sudo-warn",
        display_name="sudo 권한 상승 경고",
        purpose="sudo 명령에 경고를 띄웁니다(차단은 하지 않음).",
        protects="시스템 전역 변경 전 주의 환기",
        matcher_tool="Bash",
        action="warn",
        path_glob=None,
        script_name="warn-sudo.sh",
        script_body=_HOOK_SUDO,
        note="경고만 하고 진행합니다.",
    ),
)

_HOOK_BY_KEY: dict[str, HookCatalogEntry] = {e.key: e for e in HOOK_CATALOG}


def hook_catalog_entry(key: str) -> HookCatalogEntry | None:
    return _HOOK_BY_KEY.get(key)


def build_hook(entry: HookCatalogEntry, layer: str = "guardrails") -> Hook:
    """훅 카탈로그 항목 → 검증된 Hook(factory 기본값 + 카탈로그 값 채움)."""
    base = create_component("hook", layer)
    return base.model_copy(
        update={
            "title": entry.display_name,
            "event": entry.event,
            "matcher_tool": entry.matcher_tool,
            "action": entry.action,
            "path_glob": entry.path_glob,
            "script_name": entry.script_name,
            "script_body": entry.script_body,
        }
    )
