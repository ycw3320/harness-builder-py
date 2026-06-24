"""프로젝트 골격 파일 템플릿 (TS scaffoldTemplates.ts 포팅) — 골든과 바이트 동일."""
from __future__ import annotations

import json


def readme_template(project_name: str) -> str:
    return "\n".join([
        f"# {project_name}",
        "",
        "이 폴더는 **하네스 빌더**로 생성된 Claude Code 하네스가 적용된 프로젝트 골격입니다.",
        "",
        "## 적용 방법",
        "",
        "```bash",
        "git init",
        "claude        # 이 폴더에서 Claude Code 실행 — .claude/ 설정이 자동 적용됩니다",
        "```",
        "",
        "## 구조",
        "",
        "- `CLAUDE.md` — 프로젝트 지침(언어·스택·규칙)",
        "- `.claude/settings.json` — 권한·가드레일(hook)",
        "- `.claude/hooks/` — 자동 차단 스크립트",
        "- `.claude/agents/` — 전문 역할(sub-agent)",
        "- `.claude/rules/` — 규칙 문서",
        "- `.mcp.json` — 외부 도구(MCP) 연결",
        "- `.env.example` — 필요한 비밀키 목록 (복사해 `.env` 로 채우세요)",
        "",
        "전역 지침은 `../_APPLY/` 의 안내를 참고하세요.",
        "",
    ])


def gitignore_template() -> str:
    return "\n".join([".env", ".env.local", ".claude/settings.local.json", "node_modules/", "dist/", ""])


def settings_local_template() -> str:
    return json.dumps({"permissions": {"allow": [], "ask": [], "deny": []}}, indent=2, ensure_ascii=False) + "\n"


def apply_md_template(project_name: str, scaffold: str) -> str:
    lines = [
        "# 하네스 적용 안내",
        "",
        "이 `_APPLY/` 폴더는 **프로젝트가 아닙니다.** 적용을 돕는 보조 파일만 들어 있습니다.",
        "",
        "## 1. 프로젝트 적용",
        "",
    ]
    if scaffold == "minimal":
        lines += [
            f"- `{project_name}/` 폴더가 곧 프로젝트 루트입니다. 원하는 위치로 옮긴 뒤:",
            "",
            "```bash",
            f"cd {project_name}",
            "git init && claude",
            "```",
            "",
        ]
    else:
        lines += [
            "- 이 트리의 파일(.claude/, CLAUDE.md, .mcp.json, .env.example)을 **기존 프로젝트 루트에 복사**하세요.",
            "- 같은 이름의 파일이 있으면 덮어쓰기 전에 내용을 비교하세요(비파괴 권장).",
            "",
        ]
    lines += [
        "## 2. 전역 지침 (선택)",
        "",
        "- `_APPLY/global-CLAUDE.md` 가 있으면, 그 내용을 `~/.claude/CLAUDE.md` 에 **병합**하세요. 모든 프로젝트 공통 지침입니다.",
        "",
        "## 3. 비밀키",
        "",
        "- `.env.example` 의 항목을 복사해 `.env` 로 만들고 실제 값을 채우세요. `.env` 는 절대 커밋하지 마세요.",
        "",
    ]
    return "\n".join(lines)
