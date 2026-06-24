# 산출 명세 (계약)

> **진실원: `harness_core/export/export_ir.py` · `assemble_project.py` · `scaffold_templates.py`.**

## export_ir(ir) → VirtualFile[]
enabled=true component만. 경로 매핑:
| kind | 파일 |
|---|---|
| prose(project) | `CLAUDE.md` |
| prose(global) | `_global/CLAUDE.md` |
| permission-rule | `.claude/settings.json` #permissions (action별 dedupe+sort) |
| hook | `.claude/settings.json` #hooks + `.claude/hooks/<script>` |
| policy-doc | `.claude/rules/<doc>` |
| mcp-server | `.mcp.json` (env `${VAR}` 플레이스홀더 유지) |
| sub-agent | `.claude/agents/<name>.md` |
| (mcp env가 `${VAR}` 참조) | `.env.example` |

## assemble_project(ir, scaffold) → VirtualFile[]
- `minimal`: `<project_name>/` 루트 + README·.gitignore·.claude/settings.local.json·빈 표준폴더(.gitkeep) + `_APPLY/`
- `harness-only`: 루트에 `.claude/` 등만 + `_APPLY/`
- 전역 prose(`_global/CLAUDE.md`)는 항상 `_APPLY/global-CLAUDE.md`로 분리

## 불변
- JSON = `json.dumps(x, indent=2, ensure_ascii=False)` + trailing `\n`. 한국어 보존.
- 정렬 = Python 결정론(`sorted(key=path)`).
- **골든 바이트-동일 게이트(ADR-0003)** 가 위 전부를 회귀 보장. 변경 시 골든은 의도 변경일 때만 갱신.
