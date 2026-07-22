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
from harness_core.ir.schema import McpServer

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
