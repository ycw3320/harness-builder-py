"""PM9-P1 라이브 관측 — 이벤트 파싱·결정론 매핑·설치 멱등 (순수)."""

import json

from harness_app.observe import (
    OBSERVE_EVENTS,
    LiveEvent,
    describe_event,
    install_observer,
    parse_live_line,
    remove_observer,
)
from harness_core.ir.presets import safety_first_preset


def _ev(event: str, payload: dict | None = None) -> LiveEvent:
    return LiveEvent(hb_event=event, ts="2026-06-29T12:00:00", payload=payload)


def test_parse_live_line():
    ev = parse_live_line('{"hbEvent":"PreToolUse","ts":"t","payload":{"tool_name":"Bash"}}')
    assert ev and ev.hb_event == "PreToolUse" and ev.payload["tool_name"] == "Bash"
    assert parse_live_line("깨진 줄") is None
    assert parse_live_line('{"other": 1}') is None


def test_describe_maps_to_rule_cards():
    ir = safety_first_preset("demo")
    # .env 쓰기 → hook 카드 매칭(차단)
    text, cid = describe_event(
        ir, _ev("PreToolUse", {"tool_name": "Write", "tool_input": {"file_path": ".env"}})
    )
    assert ".env 쓰기 차단" in text and "hook 차단" in text and cid
    # 강제 push → ask 규칙 매칭
    text, cid = describe_event(
        ir,
        _ev(
            "PreToolUse",
            {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}},
        ),
    )
    assert "강제 push 확인" in text and cid
    # 매칭 없음 → 정직 표기
    text, cid = describe_event(
        ir, _ev("PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
    )
    assert "매칭 규칙 없음" in text and cid is None
    # 여정 마디들
    assert "컨텍스트" in describe_event(ir, _ev("SessionStart"))[0]
    assert "요청 수신" in describe_event(ir, _ev("UserPromptSubmit", {"prompt": "hi"}))[0]
    assert "서브에이전트" in describe_event(ir, _ev("SubagentStop"))[0]


def test_describe_windows_absolute_path_matches():
    """실측 회귀: 실제 payload 는 Windows 절대경로(백슬래시)+cwd — 시뮬 glob(슬래시) 좌표계로
    정규화해야 '.env 쓰기 차단' 매칭이 재현된다(실행은 차단됐는데 재현이 '매칭 없음'이던 버그)."""
    ir = safety_first_preset("demo")
    text, cid = describe_event(
        ir,
        _ev(
            "PreToolUse",
            {
                "tool_name": "Write",
                "cwd": "C:\\Users\\pub\\proj",
                "tool_input": {"file_path": "C:\\Users\\pub\\proj\\.env"},
            },
        ),
    )
    assert ".env 쓰기 차단" in text and cid == "guard-hook-secrets"
    # cwd 밖 절대경로는 상대화 불가 → 시뮬 좌표계(상대 glob) 기준으로 매칭 없음이 정직한 재현.
    # (참고: 코어 glob_to_regexp 는 '**/'가 한 단계 디렉터리로 축소되는 잠복 결함이 있어
    #  다단 중첩 경로를 과소 매칭한다 — frozen 코어라 티어 3-A 에서 수정 예정, ROADMAP 기록.)
    _text2, cid2 = describe_event(
        ir,
        _ev(
            "PreToolUse",
            {"tool_name": "Write", "tool_input": {"file_path": "D:\\other\\place\\.env.local"}},
        ),
    )
    assert cid2 is None


def test_install_idempotent_and_remove(tmp_path):
    msg = install_observer(str(tmp_path))
    assert "관측을 켰습니다" in msg
    script = tmp_path / ".claude" / "hooks" / "hb-observer.ps1"
    settings = tmp_path / ".claude" / "settings.local.json"
    assert script.exists() and settings.exists()
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert set(OBSERVE_EVENTS) <= set(data["hooks"])
    # 멱등: 재설치해도 항목 중복 없음
    install_observer(str(tmp_path))
    data2 = json.loads(settings.read_text(encoding="utf-8"))
    assert all(len(data2["hooks"][e]) == 1 for e in OBSERVE_EVENTS)
    # 기존 사용자 훅 보존 + 제거는 관측 항목만
    data2["hooks"]["PreToolUse"].append(
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mine"}]}
    )
    settings.write_text(json.dumps(data2), encoding="utf-8")
    remove_observer(str(tmp_path))
    data3 = json.loads(settings.read_text(encoding="utf-8"))
    assert not script.exists()
    assert [e for e in data3.get("hooks", {}).get("PreToolUse", []) if "echo mine" in json.dumps(e)]
    assert "hb-observer" not in json.dumps(data3)
