"""권한 패턴 조립기(harness_app.perm_assembler) 회귀 — 조립·검증·매칭 정합.

조립기 산출 패턴이 (1) 의도한 문자열이고 (2) 코어 lint.parse_pattern 이 파싱하며
(3) simulate 접두 매칭이 기대대로 걸리는지까지 확인(sim≡export 정합).
"""

from __future__ import annotations

import pytest

from harness_app.perm_assembler import (
    build_permission,
    compose_pattern,
    match_explanation,
)
from harness_core.lint.lint import parse_pattern


@pytest.mark.parametrize(
    "tool,text,prefix,sub,expected",
    [
        ("Bash", "git push --force", True, False, "Bash(git push --force:*)"),
        ("Bash", "rm -rf", False, False, "Bash(rm -rf)"),
        ("Bash", "  ", True, False, "Bash"),  # 빈 입력 → 도구 전체
        ("Read", "**/.env", False, False, "Read(**/.env)"),
        ("Edit", ".claude/**", False, False, "Edit(.claude/**)"),
        ("WebFetch", "github.com", False, False, "WebFetch(domain:github.com)"),
        ("WebFetch", "github.com", False, True, "WebFetch(domain:*.github.com)"),
        ("WebFetch", ".github.com", False, True, "WebFetch(domain:*.github.com)"),
        ("PowerShell", "Remove-Item", True, False, "PowerShell(Remove-Item:*)"),
    ],
)
def test_compose_pattern(tool, text, prefix, sub, expected):
    assert compose_pattern(tool, text, prefix, sub) == expected


def test_prefix_strips_to_expected_subject():
    """`Tool(cmd:*)` → parse_pattern 이 prefix='cmd' 로 정규화(끝 :* 제거)."""
    parsed = parse_pattern(compose_pattern("Bash", "git push", True, False))
    assert parsed["tool"] == "Bash"
    assert parsed["prefix"] == "git push"


def test_exact_pattern_keeps_full_subject():
    parsed = parse_pattern(compose_pattern("Bash", "rm -rf", False, False))
    assert parsed["tool"] == "Bash"
    assert parsed["prefix"] == "rm -rf"


def test_whole_tool_has_empty_prefix():
    parsed = parse_pattern(compose_pattern("Bash", "", True, False))
    assert parsed["tool"] == "Bash"
    assert parsed["prefix"] == ""


def test_build_permission_is_valid_rule():
    rule = build_permission("deny", "Bash", "git push --force", True)
    assert rule.kind == "permission-rule"
    assert rule.action == "deny"
    assert rule.pattern == "Bash(git push --force:*)"
    assert rule.title  # 자동 파생 제목 존재
    # 코어가 파싱 가능해야 함(정합 게이트)
    parse_pattern(rule.pattern)


def test_explanation_reflects_toggles():
    assert "시작하는" in match_explanation("Bash", "git", True)
    assert "정확히" in match_explanation("Bash", "git", False)
    assert "하위 도메인" in match_explanation("WebFetch", "x.com", False, True)
