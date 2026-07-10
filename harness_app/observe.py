"""라이브 관측(PM9-P1) — Claude Code 공식 hooks 를 관측 채널로 써서 하네스 여정을 기록·해석 (순수).

원리: 관측 전용 hook(항상 exit 0 — 판정 무간섭)이 세션 이벤트를 프로젝트 로컬
`.claude/hb-live.jsonl` 에 한 줄씩 기록하고, 앱이 tail 해 "어느 규칙 카드를 지나는지"를
기존 결정론 매칭(_safe_simulate)으로 재현한다. 네트워크 0·LLM 0회.

정직 원칙: 매칭 표시는 '앱의 현재 구성 기준 재현'이며 실제 판정 주체는 Claude Code 다.
모델 내부(어느 문장을 참고 중인지)는 관측 불가 — 컨텍스트는 로드 시점(SessionStart)으로 표시.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness_core.ir.schema import HarnessIR

from .view_model import _OUTCOME_LABEL, _safe_simulate

LIVE_LOG = ".claude/hb-live.jsonl"
OBSERVER_SCRIPT = ".claude/hooks/hb-observer.ps1"
# 관측 대상 이벤트(공식 hooks) — 여정의 마디들
OBSERVE_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "SubagentStop",
    "Stop",
)

_PS1 = r"""param([string]$Event = "unknown")
# 버클(하네스 빌더) 라이브 관측 훅 — 판정에 간섭하지 않음(항상 exit 0). 로컬 기록 전용.
# stdin 은 UTF-8 스트림으로 직접 읽는다 — [Console]::In 은 시스템 로케일(CP949)로 읽어
# 한글 프롬프트·경로가 깨졌음(실측 발견). 리다이렉트된 stdin 에서도 안전한 방식.
$stdin = [Console]::OpenStandardInput()
$reader = New-Object System.IO.StreamReader($stdin, [System.Text.Encoding]::UTF8)
$raw = $reader.ReadToEnd()
try {
    $payload = ($raw | ConvertFrom-Json | ConvertTo-Json -Compress -Depth 12)
} catch { $payload = $null }
if (-not $payload) { $payload = "null" }
$ts = Get-Date -Format o
$line = '{"hbEvent":"' + $Event + '","ts":"' + $ts + '","payload":' + $payload + '}'
Add-Content -LiteralPath ".claude/hb-live.jsonl" -Value $line -Encoding utf8
exit 0
"""


def _observer_command(event: str) -> str:
    return (
        "powershell -NoProfile -ExecutionPolicy Bypass "
        f"-File .claude/hooks/hb-observer.ps1 -Event {event}"
    )


def install_observer(project_root: str) -> str:
    """관측 훅 설치 — 스크립트 생성 + settings.local.json hooks 병합(멱등) + 로그 gitignore.

    settings.local.json 은 개인 로컬 설정(공유 안 됨)이라 팀 하네스를 오염시키지 않는다.
    반환: 사용자 안내 문자열.
    """
    root = Path(project_root)
    hooks_dir = root / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "hb-observer.ps1").write_text(_PS1, encoding="utf-8", newline="\n")

    settings_path = root / ".claude" / "settings.local.json"
    data: dict = {}
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            return f"설치 중단: {settings_path} 가 올바른 JSON 이 아닙니다 — 직접 확인해주세요."
    hooks = data.setdefault("hooks", {})
    for event in OBSERVE_EVENTS:
        entries = hooks.setdefault(event, [])
        cmd = _observer_command(event)
        if not any(cmd in json.dumps(e, ensure_ascii=False) for e in entries):
            entry: dict = {"hooks": [{"type": "command", "command": cmd}]}
            if event in ("PreToolUse", "PostToolUse"):
                entry["matcher"] = ""  # 전체 도구 관측
            entries.append(entry)
    settings_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    gi = root / ".gitignore"
    line = ".claude/hb-live.jsonl"
    if gi.exists():
        text = gi.read_text(encoding="utf-8")
        if line not in text:
            gi.write_text(text.rstrip("\n") + f"\n{line}\n", encoding="utf-8", newline="\n")

    return (
        "관측을 켰습니다. 이 폴더에서 Claude Code 세션을 시작하면 여정이 아래에 나타납니다.\n"
        "(개인 설정 settings.local.json 에만 등록 — 팀 하네스에 영향 없음)"
    )


def remove_observer(project_root: str) -> str:
    """관측 훅 제거 — settings.local.json 에서 hb-observer 항목만 필터링."""
    root = Path(project_root)
    settings_path = root / ".claude" / "settings.local.json"
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            return "settings.local.json 파싱 실패 — 직접 확인해주세요."
        hooks = data.get("hooks", {})
        for event in list(hooks):
            hooks[event] = [
                e for e in hooks[event] if "hb-observer" not in json.dumps(e, ensure_ascii=False)
            ]
            if not hooks[event]:
                del hooks[event]
        if not hooks:
            data.pop("hooks", None)
        settings_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
        )
    script = root / OBSERVER_SCRIPT
    if script.exists():
        script.unlink()
    return "관측을 껐습니다(hb-observer 등록·스크립트 제거)."


@dataclass(frozen=True)
class LiveEvent:
    hb_event: str
    ts: str
    payload: dict | None


def parse_live_line(line: str) -> LiveEvent | None:
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "hbEvent" not in data:
        return None
    payload = data.get("payload")
    return LiveEvent(
        hb_event=str(data["hbEvent"]),
        ts=str(data.get("ts", "")),
        payload=payload if isinstance(payload, dict) else None,
    )


def _tool_action(payload: dict) -> dict | None:
    """hook payload(tool_name·tool_input) → 시뮬 action dict.

    실측 발견: 실제 payload 의 file_path 는 Windows 절대경로(백슬래시)인데 시뮬 glob 은
    슬래시 기준이라 '.env 쓰기 차단'이 "매칭 없음"으로 오표시됐다(실행은 차단됐는데 재현만 어긋남).
    → 슬래시 정규화 + payload.cwd 기준 상대화로 시뮬 시나리오와 같은 좌표계로 맞춘다.
    """
    tool = payload.get("tool_name")
    if not tool:
        return None
    ti = payload.get("tool_input") or {}
    action: dict = {"tool": str(tool)}
    if isinstance(ti, dict):
        if ti.get("command"):
            action["command"] = str(ti["command"])
        if ti.get("file_path"):
            path = str(ti["file_path"]).replace("\\", "/")
            cwd = str(payload.get("cwd") or "").replace("\\", "/").rstrip("/")
            if cwd and path.lower().startswith(cwd.lower() + "/"):
                path = path[len(cwd) + 1 :]  # 프로젝트 루트 기준 상대경로(원본 대소문자 유지)
            action["path"] = path
    return action


def describe_event(ir: HarnessIR, ev: LiveEvent) -> tuple[str, str | None]:
    """이벤트 → (타임라인 문구, 매칭 컴포넌트 id|None). 매칭은 결정론 재현(현재 구성 기준)."""
    p = ev.payload or {}
    if ev.hb_event == "SessionStart":
        return ("세션 시작 — 컨텍스트(CLAUDE.md·설정) 로드", None)
    if ev.hb_event == "UserPromptSubmit":
        prompt = str(p.get("prompt", ""))[:60]
        return (f"요청 수신: “{prompt}…”" if prompt else "요청 수신", None)
    if ev.hb_event in ("PreToolUse", "PostToolUse"):
        action = _tool_action(p)
        stage = "도구 실행 전" if ev.hb_event == "PreToolUse" else "도구 실행 완료"
        if action is None:
            return (f"{stage}", None)
        subject = action.get("command") or action.get("path") or ""
        head = f"{stage} {action['tool']}" + (f": {subject[:48]}" if subject else "")
        if ev.hb_event == "PostToolUse":
            return (head, None)
        r = _safe_simulate(ir, action)
        outcome = _OUTCOME_LABEL.get(r["outcome"], r["outcome"])
        blocked_by = r.get("blockedBy")
        if blocked_by:
            comp = next((c for c in ir.components if c.id == blocked_by), None)
            name = comp.title if comp else blocked_by
            return (f"{head} → 매칭 '{name}' ({outcome})", blocked_by)
        return (f"{head} → 매칭 규칙 없음 ({outcome})", None)
    if ev.hb_event == "SubagentStop":
        return ("서브에이전트 작업 종료", None)
    if ev.hb_event == "Stop":
        return ("응답 종료", None)
    return (f"{ev.hb_event}", None)
