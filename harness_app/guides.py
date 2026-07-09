"""필드 가이드·계층 소개·UI 메타 (TS ui/fieldGuides.ts·meta.ts 포팅).

초심자가 '무엇을, 어떻게 외부 LLM에 요청하면 되는지' 알려주는 순수 데이터 — 프레임워크 무의존.
"""

from __future__ import annotations

from dataclasses import dataclass

from harness_core.ir.schema import HarnessComponent


@dataclass(frozen=True)
class AntiExample:
    text: str
    why: str


@dataclass(frozen=True)
class FieldGuidance:
    """항목별 '무엇을·왜·어떻게 LLM에 요청' 가이드."""

    purpose: str
    produces_file: str
    ask_llm_template: str
    good_examples: list[str]
    anti_example: AntiExample
    tips: list[str]
    recommended_default: str | None = None


@dataclass(frozen=True)
class LayerIntro:
    what_it_controls: str
    minimum_to_do: str
    if_unsure: str


field_guides: dict[str, FieldGuidance] = {
    "prose-guideline:project": FieldGuidance(
        purpose="이 프로젝트만의 약속(스택·도메인·빌드·명명규칙)을 모델에게 알려줍니다.",
        produces_file="CLAUDE.md",
        ask_llm_template=(
            "우리 프로젝트는 {{스택}} 기반이고, 빌드는 {{빌드명령}}으로 한다. "
            "{{도메인용어}} 같은 용어를 쓰며, {{규칙}}을 지켜라."
        ),
        good_examples=[
            "이 프로젝트는 React + TypeScript 기반이다. 빌드는 `npm run build`, "
            "테스트는 `npm test`로 한다. 컴포넌트 파일명은 PascalCase를 쓴다.",
            "백엔드는 Spring Boot 3 + Java 17이다. DB는 PostgreSQL이며 마이그레이션은 Flyway로 관리한다.",
        ],
        anti_example=AntiExample(
            text="좋은 코드를 작성해라.",
            why="너무 추상적이라 모델 행동을 바꾸지 못한다. 구체적 스택·명령·규칙을 적어야 한다.",
        ),
        tips=[
            "명령어·파일경로를 그대로 적으면 모델이 따라 한다.",
            '"항상/절대" 같은 단어로 금기를 명확히.',
            "200줄 이내 핵심만.",
        ],
        recommended_default="이 프로젝트는 ___ 기반이다. 빌드: ___, 테스트: ___.",
    ),
    "prose-guideline:global": FieldGuidance(
        purpose="모든 프로젝트에 공통 적용될 나의 기본 자세(언어·톤·보안)를 정합니다.",
        produces_file="~/.claude/CLAUDE.md (적용 시)",
        ask_llm_template="항상 {{언어}}로 답하고, {{톤}} 어조를 유지하라. {{보안원칙}}을 지켜라.",
        good_examples=[
            "항상 한국어로 답하라. 비밀키·토큰을 코드나 로그에 남기지 마라. 파일 삭제 전에는 먼저 확인하라.",
            "간결하고 기술적인 어조를 유지하고 불필요한 인사말은 생략하라.",
        ],
        anti_example=AntiExample(
            text="빌드는 npm run build로 한다.",
            why="이건 프로젝트별 내용이다. 전역에는 모든 프로젝트 공통 원칙만 적는다.",
        ),
        tips=['"어느 프로젝트에서나 참인 것"만 적는다.', "언어·톤·보안이 대표 항목."],
    ),
    "permission-rule": FieldGuidance(
        purpose="모델이 어떤 도구·명령을 자유허용/질문/금지할지 경계를 정합니다.",
        produces_file=".claude/settings.json (permissions)",
        ask_llm_template=(
            "{{도구나명령}} 은(는) {{허용/질문/금지}} 으로 하고 싶다. 알맞은 권한 패턴을 만들어줘."
        ),
        good_examples=[
            "Bash(rm -rf:*) 를 deny — 위험한 재귀 삭제 차단",
            "Bash(git push --force:*) 를 ask — 강제 push는 매번 확인",
        ],
        anti_example=AntiExample(
            text="Bash 전체를 deny",
            why="모든 셸 명령이 막혀 정상 작업까지 불가능해진다. 위험한 패턴만 좁게 막아라.",
        ),
        tips=[
            "평가 순서: deny > ask > allow.",
            "패턴 예: Bash(명령접두:*), Read(./비밀파일), WebFetch(domain:*).",
            "넓게보다 좁게 막아라.",
        ],
        recommended_default="Bash(git status:*)",
    ),
    "hook": FieldGuidance(
        purpose="특정 순간에 자동 검사해 위반을 결정론적으로 차단하는 안전장치입니다(가장 강한 강제).",
        produces_file=".claude/settings.json#hooks + .claude/hooks/<스크립트>",
        ask_llm_template=(
            "{{시점(예: 파일 쓰기 전)}} 에 {{대상(예: .env 파일)}} 을(를) 차단하는 "
            "bash hook 스크립트를 작성해줘. 차단 시 exit 2."
        ),
        good_examples=[
            "Write/Edit 전 경로가 .env* 이면 exit 2로 차단 (시크릿 보호)",
            'Bash 실행 전 명령에 "rm -rf /" 가 있으면 차단',
        ],
        anti_example=AntiExample(
            text="스크립트 본문 없이 이름만 지정",
            why="실행 로직이 없어 아무 것도 차단하지 못한다. script_body에 검사·exit 코드를 넣어라.",
        ),
        tips=[
            "exit 2 = 차단, exit 0 = 통과.",
            "stdin으로 도구 입력 JSON(file_path 등)이 들어온다.",
            "matcher는 도구명, 경로 조건은 스크립트 안에서.",
        ],
    ),
    "policy-doc": FieldGuidance(
        purpose="권고(CLAUDE.md)보다 강하고 hook보다 약한 '공식 규칙 문서'입니다.",
        produces_file=".claude/rules/<문서>.md",
        ask_llm_template="{{주제}} 에 대한 규칙을 마크다운 문서로 정리해줘. 지켜야 할 항목을 목록으로.",
        good_examples=[
            "시크릿 취급 규칙: .env에만 보관, 설정엔 ${VAR}만, 발견 시 즉시 보고",
            "API 응답 규칙: 모든 에러는 표준 형식 { code, message }로 반환",
        ],
        anti_example=AntiExample(
            text='한 줄짜리 "조심해라"',
            why="규칙 문서는 구체적 항목 목록이어야 모델이 따른다.",
        ),
        tips=["체크리스트 형태가 좋다.", "꼭 강제해야 하면 hook(3단)으로 올려라."],
    ),
    "sub-agent": FieldGuidance(
        purpose="특정 작업을 전담하는 '전문 역할' 에이전트를 정의합니다.",
        produces_file=".claude/agents/<이름>.md",
        ask_llm_template=(
            "{{역할(예: 코드 리뷰어)}} 역할의 sub-agent를 만들어줘. 담당 업무는 {{업무}}, "
            "쓸 도구는 {{도구들}}, 동작 지침은 {{지침}}."
        ),
        good_examples=[
            "code-reviewer: 변경된 코드만 읽어 보안·버그를 점검하고 수정은 하지 않는다. 도구: Read, Grep.",
            "test-writer: 실패하는 테스트를 먼저 작성한다(RED). 도구: Read, Write, Bash.",
        ],
        anti_example=AntiExample(
            text="모든 걸 다 하는 만능 에이전트",
            why="역할이 넓으면 일관성이 떨어진다. 한 가지 책임으로 좁혀라.",
        ),
        tips=[
            'description은 "언제 부르는지"를 명확히.',
            "tools는 꼭 필요한 것만(권한 deny와 충돌 주의).",
        ],
    ),
    "mcp-server": FieldGuidance(
        purpose="모델이 외부 시스템(DB·검색·사내 API)에 연결되는 통로를 정의합니다.",
        produces_file=".mcp.json",
        ask_llm_template=(
            "{{서비스}} 에 연결하는 MCP 서버 설정을 만들어줘. 실행 명령은 {{명령}}, "
            "필요한 비밀키는 {{키이름}} (값은 ${VAR} 플레이스홀더로)."
        ),
        good_examples=[
            'github: command npx, args ["-y","@modelcontextprotocol/server-github"], '
            "env GITHUB_TOKEN=${GITHUB_TOKEN}",
            "postgres: command npx, env DATABASE_URL=${DATABASE_URL}",
        ],
        anti_example=AntiExample(
            text="env에 실제 토큰 값을 직접 입력",
            why="비밀키가 산출물에 박혀 유출된다. 반드시 ${VAR} 플레이스홀더만 쓰고 .env에 실제 값을 둔다.",
        ),
        tips=["env 값은 ${VAR} 형태로만.", "필요한 서버만 연결(공격면 최소)."],
    ),
}

layer_intros: dict[str, LayerIntro] = {
    "context": LayerIntro(
        what_it_controls="모델이 받는 기본 지침 — 나와 이 프로젝트의 약속.",
        minimum_to_do="프로젝트 개요 한 단락만 채워도 충분합니다.",
        if_unsure="스택과 빌드 명령만 적어두세요.",
    ),
    "permissions": LayerIntro(
        what_it_controls="모델이 무엇을 자유롭게 하고, 무엇을 물어보고, 무엇을 금지할지.",
        minimum_to_do="위험한 명령 1~2개를 금지(deny)로 두세요.",
        if_unsure="기본 프리셋의 rm -rf 차단을 그대로 두세요.",
    ),
    "mcp": LayerIntro(
        what_it_controls="모델이 연결되는 외부 도구(DB·검색·사내 API).",
        minimum_to_do="외부 연동이 없으면 비워둬도 됩니다.",
        if_unsure="지금은 건너뛰세요. 나중에 추가할 수 있습니다.",
    ),
    "guardrails": LayerIntro(
        what_it_controls="자동으로 막아야 할 선 — 결정론적 차단 규칙.",
        minimum_to_do="시크릿 차단 hook 하나면 시작으로 충분합니다.",
        if_unsure="기본 .env 차단을 켜두세요.",
    ),
    "workflow": LayerIntro(
        what_it_controls="반복 작업의 표준 절차와 전문 역할(에이전트).",
        minimum_to_do="당장 없어도 됩니다.",
        if_unsure="자주 쓰는 작업이 생기면 그때 추가하세요.",
    ),
    "verification": LayerIntro(
        what_it_controls="완료 기준과 산출(내보내기).",
        minimum_to_do="우측 패널에서 내보내기만 하면 됩니다.",
        if_unsure="그대로 두세요.",
    ),
}

# 결정방식(involvement) 색 — 단일 출처 (auto/assisted/manual-gate)
involvement_meta: dict[str, dict[str, str]] = {
    "auto": {"label": "자동", "color": "#1a7f37"},
    "assisted": {"label": "추천", "color": "#0969da"},
    "manual-gate": {"label": "직접", "color": "#bc4c00"},
}

layer_order: list[str] = [
    "context",
    "permissions",
    "mcp",
    "guardrails",
    "workflow",
    "verification",
]

layer_meta: dict[str, dict] = {
    "context": {"label": "컨텍스트", "m1": True, "hint": "언어·톤·스택·규칙"},
    "permissions": {"label": "도구·권한", "m1": True, "hint": "허용·질문·금지 경계"},
    "mcp": {"label": "외부 도구", "m1": True, "hint": "외부 연결·비밀키"},
    "guardrails": {"label": "가드레일", "m1": True, "hint": "자동 차단 규칙"},
    "workflow": {"label": "워크플로우·역할", "m1": True, "hint": "반복 절차·전문 역할"},
    "verification": {"label": "검증·내보내기", "m1": False, "hint": "완료 기준·산출"},
}

# 강제수준 사다리 (1→3단) — PM5 강제수준 UI 데이터 (원래 의도 §5.5)
enforcement_ladder: list[dict[str, str]] = [
    {"key": "prose", "label": "프로즈 권고", "desc": "CLAUDE.md 권고 — 모델이 무시할 수 있음"},
    {"key": "policy-doc", "label": "정책 문서", "desc": "rules 규칙 — 더 명확하나 준수에 의존"},
    {"key": "hook-block", "label": "hook 자동 차단", "desc": "결정론적 차단 — 물리적으로 불가능"},
]

# PM6: 하네스 단일 정의(SSOT) — 안전벨트 비유. 환영·시연 아하·export 3곳에서 동일 노출(spaced repetition).
HARNESS_DEFINITION = (
    "하네스 = Claude Code(AI 코딩 도구)가 내 규칙대로 안전하게 움직이도록 잡아주는 설정 묶음"
    "(.claude/ 폴더 + CLAUDE.md). 빠른 말에게 채우는 안전벨트처럼, 평소엔 자유롭게 일하되 "
    "위험한 방향(.env·강제 push)으로는 못 가게 잡아줍니다."
)
HARNESS_AHA = "방금 본 게 하네스예요"
# 6영역 멘탈모델 — '왜 이 순서인가'를 한 줄로(과소일반화 '하네스=차단' 보완).
# layer_order 6개와 1:1 대응(테스트로 정합 강제): context→permissions→mcp→guardrails→workflow→verification
LAYER_FLOW_CAPTION = "아는가 → 해도 되나 → 무엇과 연결되나 → 절대 못함 → 어떻게 → 검증"


def guidance_for(c: HarnessComponent) -> FieldGuidance | None:
    """component 에 맞는 가이드 반환 (prose-guideline 은 scope variant)."""
    if c.kind == "prose-guideline":
        return field_guides.get(f"prose-guideline:{c.scope}")
    return field_guides.get(c.kind)
