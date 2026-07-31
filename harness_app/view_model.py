"""표시용 view-model — 상태·코어에서 화면 데이터를 파생 (프레임워크 무의존).

두 셸(Flet/Qt)이 동일하게 소비한다 → 위젯 배선만 갈리고 로직은 공유(M6 LOC 공정).
PM3-B: 전 6계층 interactive, kind별 field_specs(데이터 구동 폼), 행별 필드 가이드.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from harness_core.export.assemble_project import assemble_project
from harness_core.ir.enforcement import can_promote, enforcement_level
from harness_core.ir.schema import HarnessIR
from harness_core.lint.lint import lint_ir
from harness_core.sim.simulate import default_scenarios, simulate

from .guides import guidance_for, involvement_meta, layer_intros, layer_meta, layer_order
from .runtime_check import check_hook_runtimes
from .state import BuilderState

# 결정방식(involvement) 콤보 옵션 — (라벨, 키)
INVOLVEMENT_OPTIONS = [(meta["label"], key) for key, meta in involvement_meta.items()]


@dataclass(frozen=True)
class NavItemVM:
    layer: str
    label: str
    hint: str
    interactive: bool  # 클릭 가능 여부(PM3-B: 전 계층 True)
    selected: bool
    count: int  # enabled component 수
    dot_color: str  # 내용 있음(녹)/없음(회)


@dataclass(frozen=True)
class FieldSpec:
    """kind별 편집 필드 1개 — 위젯 종류로 데이터 구동 렌더(서브클래스 6종 회피)."""

    name: str  # 스키마 필드명(snake_case)
    label: str
    widget: str  # line | textarea | combo | list | dict
    options: tuple[str, ...] = ()  # combo 용(원시 값)
    placeholder: str = ""
    tip: str = ""  # PM6-S5: 호버 시 보여줄 개발자용 풀이(2단 톤의 둘째 단)
    option_labels: tuple[
        str, ...
    ] = ()  # PM6-S5: combo 표시 라벨(options 와 같은 순서, 빈값=원시 사용)


@dataclass(frozen=True)
class RowVM:
    id: str
    title: str
    kind: str
    involvement: str
    involvement_label: str
    color: str
    enabled: bool
    values: dict = field(default_factory=dict)  # 편집 필드 현재값(model_dump)
    guide: dict | None = None  # {purpose, produces, ask, examples}
    enforcement: str | None = None  # 강제수준 라벨(권고/문서/자동 차단)
    promotable: bool = False  # 강제수준 한 단계 승격 가능 여부


@dataclass(frozen=True)
class LintVM:
    level: str
    code: str
    message: str


@dataclass(frozen=True)
class SimVM:
    label: str
    outcome: str
    reason: str


@dataclass(frozen=True)
class SimCompareVM:
    """before/after 대비 — 빈 IR(규칙 없음) vs 현재 IR(지금 구성). 초심자 가치 시연용.

    before 는 항상 '규칙 없으면'(빈 IR)이라 거의 통과 — 과장 없이 정직하게 대비한다.
    """

    label: str
    before_outcome: str  # 표시 라벨(규칙 없으면)
    before_raw: str  # 원시 outcome 키(색·아이콘 분기용)
    after_outcome: str  # 표시 라벨(지금)
    after_raw: str
    after_reason: str  # 왜 그 결과인지 한 줄(차단/확인 시)
    after_blocked_by: str | None  # 차단·확인을 만든 컴포넌트 id (점프용)
    changed: bool  # before≠after (대비 강조용)


@dataclass(frozen=True)
class SimRuleVM:
    """규칙 on/off 토글 — affects_sim=True 면 끄면 차단이 풀림(인과 체감).

    False(allow 권한·비차단 hook)여도 목록엔 남는다 — enabled 는 export 포함 여부를
    좌우하는 실기능이라 토글 수단을 없애면 안 됨(대신 '시뮬 영향 없음' 배지).
    """

    id: str
    title: str
    kind: str
    enabled: bool
    affects_sim: bool


@dataclass(frozen=True)
class CompletionVM:
    filled: int
    total: int
    percent: int
    next_layer: str | None  # 비어 있는 다음 추천 계층
    next_label: str | None


@dataclass(frozen=True)
class MaturityVM:
    """PM7-S4 성숙도 — '몇 칸 채웠나'(양)가 아니라 '얼마나 지켜지나'(질)를 결정론 산식으로.

    Lv0 무방비 → Lv1 약속(prose만) → Lv2 규칙(권한·정책) → Lv3 강제(차단 hook)
    → Lv4 검증됨(오류 0·보안경고 0·차단 시연·핵심 시나리오 커버). 산식은 detail 로 공개.
    """

    level: int  # 0~4
    label: str  # 예: "Lv3 강제"
    detail: str  # 산식 공개(툴팁)
    next_hint: str | None  # 다음 레벨로 가는 최소 행동(없으면 최고 레벨)
    meaning: str = ""  # 이 레벨이 실제로 뜻하는 것(한 줄 평문)
    covered: tuple[str, ...] = ()  # 지금 하네스가 막는/확인하는 시나리오(구체 표시)
    caveat: str = ""  # '검증됨'의 한계(Lv4에서만) — 과장 오독 방지
    # 1-C: 이 PC 에 훅 실행기(bash 등)가 없어 Lv4 를 보류했는가(거짓 안전 방지).
    runtime_blocked: bool = False
    runtime_note: str = ""  # 보류 사유(사람 말) — 상태 카드에 경고로 표시


# 완성도 집계: 핵심 계층(항상 채워야 함) + 선택 계층(프로젝트별 — 비어 있으면 N/A로 분모 제외).
# verification 은 내보내기 전용이라 제외. 선택 계층(mcp·workflow)을 안 쓰면 분모에서 빼 '100% 도달
# 가능'을 보장한다 — layer_intros 가 이들을 '선택'으로 안내하는데 5계층 고정 분모는 안내를 따르면
# 100%가 불가능한 자기모순이었다(신호 정합화).
_CORE_LAYERS = ["context", "permissions", "guardrails"]
_OPTIONAL_LAYERS = ["mcp", "workflow"]


def completion(state: BuilderState) -> CompletionVM:
    """§0.6 완성도 미터 — 핵심 계층 충족률(선택 계층은 쓸 때만 분모 포함) + 다음 추천 영역."""
    counts = {
        layer: sum(1 for c in state.ir.components if c.layer == layer and c.enabled)
        for layer in _CORE_LAYERS + _OPTIONAL_LAYERS
    }
    core_filled = sum(1 for layer in _CORE_LAYERS if counts[layer] > 0)
    optional_used = sum(1 for layer in _OPTIONAL_LAYERS if counts[layer] > 0)
    filled = core_filled + optional_used
    total = len(_CORE_LAYERS) + optional_used  # 안 쓴 선택 계층은 N/A(분모 제외)
    # 다음 추천: 비어 있는 핵심 계층 우선, 없으면 비어 있는 선택 계층(발견용 — 100% 도달을 막지 않음).
    nxt = next((layer for layer in _CORE_LAYERS if counts[layer] == 0), None) or next(
        (layer for layer in _OPTIONAL_LAYERS if counts[layer] == 0), None
    )
    return CompletionVM(
        filled=filled,
        total=total,
        percent=round(filled / total * 100) if total else 0,
        next_layer=nxt,
        next_label=layer_meta[nxt]["label"] if nxt else None,
    )


@dataclass(frozen=True)
class NextActionVM:
    """'지금 할 일 1개' — 화면 전체에서 단 하나의 다음 행동(직관성 재설계의 축).

    결정론 우선순위: 정합성 오류 해결 > 성숙도 다음 단계 > 빈 핵심 영역 채우기 > 내보내기.
    """

    label: str  # 버튼 문구(행동형)
    action: str  # "fix-lint" | "jump" | "export"
    target_layer: str | None  # jump 대상 계층(없으면 None)


def next_action(state: BuilderState) -> NextActionVM:
    errors = [f for f in lint_ir(state.ir, rulesets=("core", "security")) if f["level"] == "error"]
    if errors:
        return NextActionVM(
            label=f"정합성 오류 {len(errors)}개 해결하기", action="fix-lint", target_layer=None
        )
    mat = maturity(state)
    if mat.next_hint:
        if "오류" in mat.next_hint or "경고" in mat.next_hint:  # Lv3 변형: 검사 결과 해결
            return NextActionVM(label=mat.next_hint, action="fix-lint", target_layer=None)
        target = {0: "permissions", 1: "permissions", 2: "guardrails", 3: "guardrails"}.get(
            mat.level
        )
        return NextActionVM(label=mat.next_hint, action="jump", target_layer=target)
    comp = completion(state)
    if comp.next_layer in _CORE_LAYERS:
        return NextActionVM(
            label=f"'{comp.next_label}' 영역 채우기 →", action="jump", target_layer=comp.next_layer
        )
    return NextActionVM(label="폴더 선택 → 하네스 생성", action="export", target_layer=None)


_OUTCOME_LABEL = {
    "blocked-by-hook": "hook 차단",
    "blocked-by-permission": "권한 차단",
    "ask": "사용자 확인",
    "allowed": "통과",
    "invalid": "평가 불가(패턴 오류)",
}


def _safe_simulate(ir, scenario: dict) -> dict:
    """simulate 를 re.error 로부터 보호 — hook '대상 도구'는 자유 입력 regex 라
    미완성 괄호('Bash(') 하나로 우패널 재빌드가 통째로 무너지던 결함 방어(코어 무수정).

    오류를 낸 hook 을 특정해 blockedBy 에 실어 — 붉은 줄 클릭→해당 규칙 점프(수정 유도)가 되게 한다.
    """
    try:
        return simulate(ir, scenario)
    except re.error:
        bad_id, bad_title = None, ""
        for c in ir.components:
            if c.kind == "hook" and c.enabled:
                try:
                    re.compile(c.matcher_tool)
                except re.error:
                    bad_id, bad_title = c.id, c.title
                    break
        reason = (
            f'hook "{bad_title}" 의 대상 도구 패턴이 올바르지 않아 평가할 수 없어요 — 클릭해 수정하세요'
            if bad_id
            else "hook '대상 도구' 패턴이 올바르지 않아 평가할 수 없어요 — 해당 규칙을 수정하세요"
        )
        return {"action": scenario, "outcome": "invalid", "reasons": [reason], "blockedBy": bad_id}


# kind별 편집 필드 스펙 (스키마 필드와 1:1). id/layer/involvement/enabled/title 은 공통 처리.
_SPECS: dict[str, list[FieldSpec]] = {
    "prose-guideline": [
        FieldSpec(
            "scope",
            "적용 범위",
            "combo",
            ("project", "global"),
            option_labels=("이 프로젝트만", "모든 프로젝트"),
            tip="이 프로젝트에만(.claude/CLAUDE.md) 또는 내 모든 프로젝트에(~/.claude/CLAUDE.md) 적용.",
        ),
        FieldSpec("heading", "섹션 제목", "line", placeholder="예: 프로젝트 개요"),
        FieldSpec(
            "body",
            "본문",
            "textarea",
            placeholder=(
                "이 프로젝트에 대해 Claude 가 늘 알아야 할 것을 평범한 문장으로 적으세요.\n"
                "예: React + FastAPI 프로젝트. 빌드: npm run build · 테스트: pytest.\n"
                "예: 모든 답변은 한국어로. 커밋 전 반드시 테스트 실행."
            ),
        ),
    ],
    "permission-rule": [
        FieldSpec(
            "action",
            "동작",
            "combo",
            ("allow", "ask", "deny"),
            option_labels=("허용", "질문", "금지"),
            tip="허용=자유 실행 / 질문=실행 전 물어봄 / 금지=차단. 평가 순서는 금지>질문>허용.",
        ),
        FieldSpec(
            "pattern",
            "대상 패턴",
            "line",
            placeholder="Bash(rm -rf:*)",
            tip="무엇에 적용할지. 예: Bash(rm -rf:*) = 'rm -rf'로 시작하는 명령 / Read(./secret) = 특정 파일 읽기. MCP 도구는 mcp__서버__도구 형식(예: mcp__github__create_issue). 넓게보다 좁게.",
        ),
    ],
    "mcp-server": [
        FieldSpec(
            "server_name",
            "서버 이름(별칭)",
            "line",
            placeholder="예: github, filesystem",
            tip="이 서버를 부를 별칭 — .mcp.json 의 키가 됩니다. '+ 외부 도구'로 카탈로그에서 고르면 자동 입력.",
        ),
        FieldSpec(
            "command",
            "실행 명령",
            "line",
            placeholder="npx / uvx / docker",
            tip="서버를 띄우는 실행기. npx=Node · uvx=Python(uv) · docker=컨테이너. 카탈로그에서 고르면 자동.",
        ),
        FieldSpec(
            "args",
            "인자",
            "list",
            placeholder="예: -y  @scope/server-name  <경로>",
            tip="실행 인자(한 줄에 하나). <각괄호>로 표시된 자리표시자는 실제 경로로 바꾸세요. 카탈로그 선택 시 자동.",
        ),
        FieldSpec(
            "env",
            "환경변수(비밀키)",
            "dict",
            tip="비밀키는 값에 실제 키 대신 ${VAR} 만(예: ${GITHUB_TOKEN}). 실제 값은 생성되는 .env 에 넣습니다 — 설정 파일엔 안 박힘.",
        ),
    ],
    "hook": [
        FieldSpec(
            "event",
            "검사 시점",
            "combo",
            ("PreToolUse", "PostToolUse", "SessionStart", "Stop"),
            option_labels=("도구 실행 전", "도구 실행 후", "세션 시작", "세션 종료"),
            tip="언제 검사할지. '도구 실행 전'이면 위험한 작업을 실행되기 전에 막을 수 있습니다.",
        ),
        FieldSpec(
            "matcher_tool",
            "대상 도구",
            "line",
            placeholder="Write|Edit",
            tip="검사할 도구. 예: Write|Edit = 파일 쓰기 또는 수정( | 은 '또는').",
        ),
        FieldSpec(
            "path_glob",
            "경로 패턴(선택)",
            "line",
            placeholder="**/.env*",
            tip="경로 조건. 예: **/.env* = 모든 폴더의 .env 파일. *=아무 글자, **=하위 폴더 포함.",
        ),
        FieldSpec(
            "action",
            "동작",
            "combo",
            ("deny", "allow", "warn"),
            option_labels=("금지", "허용", "경고"),
            tip="금지=차단 / 허용=통과 / 경고=메시지만.",
        ),
        FieldSpec("script_name", "스크립트 파일", "line", placeholder="block-secrets.sh"),
        FieldSpec(
            "script_body",
            "검사 스크립트",
            "textarea",
            tip="검사 로직(bash). exit 2 = 차단(작업 취소), exit 0 = 통과. 도구 입력은 stdin 으로 들어옵니다.",
        ),
    ],
    "policy-doc": [
        FieldSpec("doc_name", "문서 파일", "line", placeholder="secrets.md"),
        FieldSpec("body", "본문", "textarea"),
    ],
    "sub-agent": [
        FieldSpec("name", "이름", "line", placeholder="code-reviewer"),
        FieldSpec("description", "설명(언제 부르는지)", "line"),
        FieldSpec(
            "tools",
            "도구",
            "list",
            tip="이 역할이 쓸 도구만 적으세요. 예: Read, Grep, Write. 적게 줄수록 안전합니다.",
        ),
        FieldSpec(
            "model",
            "모델(선택)",
            "line",
            placeholder="sonnet",
            tip="이 서브에이전트가 쓸 모델. 비우면 메인 세션 모델을 상속합니다. "
            "가벼운 일=haiku(빠름·저비용), 균형=sonnet, 복잡한 추론=opus.",
        ),
        FieldSpec("system_prompt", "시스템 프롬프트", "textarea"),
    ],
}


def field_specs(kind: str) -> list[FieldSpec]:
    return _SPECS.get(kind, [])


def nav_items(state: BuilderState) -> list[NavItemVM]:
    items: list[NavItemVM] = []
    for layer in layer_order:
        meta = layer_meta[layer]
        count = sum(1 for c in state.ir.components if c.layer == layer and c.enabled)
        items.append(
            NavItemVM(
                layer=layer,
                label=meta["label"],
                hint=meta["hint"],
                interactive=True,
                selected=(layer == state.selected_layer),
                count=count,
                dot_color="#1a7f37" if count else "#8c959f",
            )
        )
    return items


def rows_for_selected(state: BuilderState) -> list[RowVM]:
    rows: list[RowVM] = []
    for c in state.ir.components:
        if c.layer != state.selected_layer:
            continue
        inv = involvement_meta[c.involvement]
        g = guidance_for(c)
        guide = None
        if g is not None:
            guide = {
                "purpose": g.purpose,
                "produces": g.produces_file,
                "ask": g.ask_llm_template,
                "examples": list(g.good_examples),
            }
        rows.append(
            RowVM(
                id=c.id,
                title=c.title,
                kind=c.kind,
                involvement=c.involvement,
                involvement_label=inv["label"],
                color=inv["color"],
                enabled=c.enabled,
                values=c.model_dump(by_alias=False),
                guide=guide,
                enforcement=enforcement_level(c.kind),
                promotable=can_promote(c.kind),
            )
        )
    return rows


def layer_meta_label(state: BuilderState) -> str:
    return layer_meta[state.selected_layer]["label"]


def layer_intro(state: BuilderState) -> dict[str, str]:
    intro = layer_intros[state.selected_layer]
    return {
        "what": intro.what_it_controls,
        "minimum": intro.minimum_to_do,
        "if_unsure": intro.if_unsure,
    }


_MATURITY_NAMES = {0: "무방비", 1: "약속", 2: "규칙", 3: "강제", 4: "검증됨"}
_MATURITY_MEANING = {
    0: "아직 아무 보호도 없어요.",
    1: "지침(약속)만 있어요 — 어겨도 막지는 못합니다.",
    2: "규칙은 있지만, 실행 전 자동 차단은 아직이에요.",
    3: "위험한 작업을 실행 전에 자동으로 막아요.",
    4: "대표 위험을 실제로 막고 검사도 깨끗해요.",
}
# 성숙도는 '결정방식(직접/추천/자동)'·'입력량'이 아니라 lint+시뮬 결과의 함수 — 오독 방지 문구.
_MATURITY_CAVEAT = (
    "'검증됨'은 완성이 아니라 기본 안전 기준(.env 유출·되돌릴 수 없는 삭제·강제 push) 통과예요. "
    "내 프로젝트 고유의 위험·팀 규칙은 직접 더 추가해야 진짜 완성입니다."
)
_MATURITY_DETAIL = (
    "산식(결정론, 입력량·결정방식 무관): Lv1=지침 존재 · Lv2=권한/정책 규칙 존재 · "
    "Lv3=차단 hook(도구 실행 전+금지) 존재 · "
    "Lv4=오류 0 + 보안 경고 0 + 차단 시연 ≥1 + 핵심 시나리오(.env 차단·강제 push 확인) 커버"
)


def maturity(state: BuilderState) -> MaturityVM:
    """§PM7-S4 성숙도 판정 — lint+simulate 결과의 함수(해자가 심판, LLM 0회)."""
    enabled = [c for c in state.ir.components if c.enabled]
    has_rule = any(c.kind in ("permission-rule", "policy-doc") for c in enabled)
    has_block_hook = any(
        c.kind == "hook" and c.event == "PreToolUse" and c.action == "deny" for c in enabled
    )

    covered_labels: tuple[str, ...] = ()
    runtime_blocked = False
    runtime_note = ""
    if not enabled:
        level, hint = 0, "컨텍스트 영역에서 프로젝트 개요 한 줄부터 시작하세요"
    elif not has_rule and not has_block_hook:
        level, hint = 1, "도구·권한 영역에서 위험 명령 금지 규칙 1개를 추가하세요"
    elif not has_block_hook:
        level, hint = 2, "가드레일 영역에서 차단 hook(도구 실행 전+금지) 1개를 추가하세요"
    else:
        findings = lint_ir(state.ir, rulesets=("core", "security"))
        errors = [f for f in findings if f["level"] == "error"]
        sec_warns = [f for f in findings if f["code"].startswith("sec-")]
        compare = sim_compare_ir(state.ir)
        # 지금 하네스가 '무언가 하는'(차단·확인) 시나리오 = 구체적 커버 목록(상태 카드 표시).
        covered_labels = tuple(
            r.label.replace(" 시도", "") for r in compare if r.after_raw != "allowed"
        )
        by_label = {r.label: r for r in compare}
        env = by_label.get(".env 파일에 쓰기 시도")
        push = by_label.get("강제 push 시도")
        covered = (
            env is not None
            and env.after_raw.startswith("blocked")
            and push is not None
            and push.after_raw in ("ask", "blocked-by-hook", "blocked-by-permission")
        )
        changed = any(r.changed for r in compare)
        # 1-C 크로스플랫폼 precheck(발견 B): 훅 스크립트의 실행기(bash 등)가 이 PC 에 없으면
        # 훅은 조용히 미실행된다 — 시뮬이 '차단'이라 해도 실제로는 안 막힌다. 그 상태로 Lv4
        # '검증됨'을 주면 도구가 없는 안전을 있다고 말하게 되므로 Lv3 로 보류한다.
        rt = check_hook_runtimes(state.ir)
        if rt.blocking_affected:
            runtime_blocked = True
            runtime_note = (
                f"이 PC 에 {rt.runtime_names} 이(가) 없어 차단 훅이 실행되지 않습니다 — "
                "지금 상태로는 실제로 막히지 않아요. " + (rt.notes[0] if rt.notes else "")
            ).strip()
        if not errors and not sec_warns and changed and covered and not runtime_blocked:
            level, hint = 4, None
        else:
            level = 3
            if runtime_blocked:
                hint = f"{rt.runtime_names} 설치 후 다시 확인하세요(없으면 차단 훅이 실행되지 않음)"
            elif errors or sec_warns:
                hint = "정합성 오류·보안 경고를 해결하세요(우측 검사 결과 참조)"
            else:
                hint = ".env 쓰기 차단과 강제 push 확인 규칙을 켜세요(핵심 시나리오 커버)"

    return MaturityVM(
        level=level,
        label=f"Lv{level} {_MATURITY_NAMES[level]}",
        detail=_MATURITY_DETAIL,
        next_hint=hint,
        meaning=_MATURITY_MEANING[level],
        covered=covered_labels,
        caveat=_MATURITY_CAVEAT if level == 4 else "",
        runtime_blocked=runtime_blocked,
        runtime_note=runtime_note,
    )


def lint_items(state: BuilderState) -> list[LintVM]:
    # PM7-S3: 앱 표시는 core+security — 실행 전 보안 검증(전부 warning, export 미차단)
    return [
        LintVM(level=f["level"], code=f["code"], message=f["message"])
        for f in lint_ir(state.ir, rulesets=("core", "security"))
    ]


def export_paths(state: BuilderState) -> list[str]:
    """산출 파일 경로 목록 (생성될 트리 미리보기)."""
    tree = assemble_project(state.ir, state.scaffold)
    return [vf.path for vf in tree]


def assembled_files(state: BuilderState) -> list[tuple[str, str]]:
    """생성될 산출물 (경로, 내용) — 미리보기(1-A)의 본체.

    발견 C 대응: prose/CLAUDE.md 는 시뮬 효과가 0이라 지침만 쓴 초심자는 빈 시뮬 화면을 봤다.
    assemble 된 실제 파일 내용을 그대로 노출해 '무엇이 만들어지나'를 조립 중에 보게 한다.
    """
    return [(vf.path, vf.content) for vf in assemble_project(state.ir, state.scaffold)]


@dataclass(frozen=True)
class ApplicabilityVM:
    title: str
    layer: str
    when: str  # 이 규칙이 '언제' 적용되나(정직한 타이밍 모델)
    always_on: bool  # 상시 적용(맥락) vs 조건부 발동


def _applies_when(c) -> tuple[str, bool]:
    """kind 기반 결정론 타이밍 설명 — 휴리스틱 텍스트 매칭이 아니라 규칙 종류가 정하는 사실.

    prose 는 매 요청에 항상 주입되는 맥락, hook/permission 은 조건이 맞을 때만 발동한다는
    초심자 멘탈모델을 심는다. policy-doc 은 CC 가 자동 로드하지 않음을 정직히 표기(수동 참조).
    """
    k = c.kind
    if k == "prose-guideline":
        return "항상 — 매 요청에 맥락(CLAUDE.md)으로 주입", True
    if k == "policy-doc":
        return "참고 문서(.claude/rules) — Claude 가 자동 로드하진 않음(수동 참조)", False
    if k == "permission-rule":
        return (
            f"도구 호출이 '{getattr(c, 'pattern', '')}' 과 일치할 때 → {getattr(c, 'action', '')}",
            False,
        )
    if k == "hook":
        return (
            f"{getattr(c, 'event', '')} + '{getattr(c, 'matcher_tool', '')}' 일치 시 스크립트 실행",
            False,
        )
    if k == "mcp-server":
        return "연결된 외부 도구 — 세션 내내 사용 가능", True
    if k == "sub-agent":
        return f"'{getattr(c, 'name', '')}' 역할로 위임될 때", False
    return "—", False


def applicability(state: BuilderState) -> list[ApplicabilityVM]:
    """각 활성 규칙이 '언제' 적용되나 — 미리보기의 정직한 규칙-타이밍 뷰(1-A)."""
    out: list[ApplicabilityVM] = []
    for c in state.ir.components:
        if not c.enabled:
            continue
        when, always = _applies_when(c)
        out.append(ApplicabilityVM(title=c.title, layer=c.layer, when=when, always_on=always))
    return out


def sim_items(state: BuilderState) -> list[SimVM]:
    """라이브 결정론 시뮬레이터 (LLM 0회) — 기본 시나리오 평가."""
    out: list[SimVM] = []
    for scenario in default_scenarios:
        r = _safe_simulate(state.ir, scenario)
        out.append(
            SimVM(
                label=scenario["label"],
                outcome=_OUTCOME_LABEL.get(r["outcome"], r["outcome"]),
                reason=r["reasons"][-1] if r["reasons"] else "",
            )
        )
    return out


def sim_compare(state: BuilderState) -> list[SimCompareVM]:
    """before/after 시연(현재 상태) — sim_compare_ir 위임."""
    return sim_compare_ir(state.ir)


def sim_compare_ir(ir: HarnessIR) -> list[SimCompareVM]:
    """before/after 시연 — 빈 IR(규칙 0개)과 대상 IR을 같은 시나리오로 평가해 대비.

    '하네스 없으면 vs 지금'을 한 화면에서 보여주는 초심자 아하 엔진. 코어 무수정 —
    결정론 simulate 를 빈 IR 로 한 번 더 호출할 뿐(LLM 0회 유지). before 는 정직하게
    '규칙 없으면'(빈 IR) 기준. PM7: 수신 검증(받은 .harness.json 미리보기)도 재사용.
    """
    empty = HarnessIR(meta=ir.meta, components=[])
    out: list[SimCompareVM] = []
    for sc in default_scenarios:
        before = _safe_simulate(empty, sc)
        after = _safe_simulate(ir, sc)
        out.append(
            SimCompareVM(
                label=sc["label"],
                before_outcome=_OUTCOME_LABEL.get(before["outcome"], before["outcome"]),
                before_raw=before["outcome"],
                after_outcome=_OUTCOME_LABEL.get(after["outcome"], after["outcome"]),
                after_raw=after["outcome"],
                after_reason=after["reasons"][-1] if after["reasons"] else "",
                after_blocked_by=after.get("blockedBy"),
                changed=before["outcome"] != after["outcome"],
            )
        )
    return out


def _rule_affects_sim(c) -> bool:
    """simulate 가 실제로 반영하는 규칙만 — allow 권한·비차단 hook 은 토글해도 결과 불변이라
    '꺼보세요—차단이 풀립니다' 서사가 거짓 인과가 되므로 목록에서 제외한다."""
    if c.kind == "hook":
        return c.event == "PreToolUse" and c.action == "deny"
    if c.kind == "permission-rule":
        return c.action in ("deny", "ask")
    return False


def sim_rules(state: BuilderState) -> list[SimRuleVM]:
    """규칙 on/off 토글 목록(hook·permission 전체) — affects_sim 으로 시연 가능 여부 구분."""
    return [
        SimRuleVM(
            id=c.id,
            title=c.title,
            kind=c.kind,
            enabled=c.enabled,
            affects_sim=_rule_affects_sim(c),
        )
        for c in state.ir.components
        if c.kind in ("hook", "permission-rule")
    ]


def toggle_changes_sim(state: BuilderState, comp_id: str) -> bool:
    """이 컴포넌트를 토글하면 시뮬 결과가 실제로 바뀌는지 — 통지 없이 가상 평가.

    아하 배너('방금 본 게 하네스예요')를 결과가 진짜 변한 토글에만 붙이기 위한 판정.
    """
    cur = [_safe_simulate(state.ir, sc)["outcome"] for sc in default_scenarios]
    comps = [
        c.model_copy(update={"enabled": not c.enabled}) if c.id == comp_id else c
        for c in state.ir.components
    ]
    hyp = HarnessIR(meta=state.ir.meta, components=comps)
    new = [_safe_simulate(hyp, sc)["outcome"] for sc in default_scenarios]
    return cur != new
