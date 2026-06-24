# IR 명세 (계약)

> **진실원: `harness_core/ir/schema.py`.** 이 문서는 계약 요약이며, 필드 상세는 코드가 정본이다(값 복붙 금지).

## HarnessIR
- `meta`: `{ ir_version, target_tool="claude-code", preset, project_name }`
- `components`: `list[component]`

## 공통 필드 (모든 component)
`id` · `layer` · `title` · `involvement`(auto|assisted|manual-gate) · `enabled` · `intent?`{ raw, compiled_by, confidence }

## kind 6종 (판별자 `kind`)
| kind | 핵심 필드 | 산출 |
|---|---|---|
| `prose-guideline` | scope(global\|project), heading, body | CLAUDE.md |
| `permission-rule` | action(allow\|ask\|deny), pattern | settings.json#permissions |
| `mcp-server` | server_name, command, args[], env{} | .mcp.json |
| `hook` | event, matcher_tool, path_glob?, action(deny\|warn\|allow), script_name, script_body | settings.json#hooks + hooks/ |
| `policy-doc` | doc_name, body | .claude/rules/ |
| `sub-agent` | name, description, tools[], model?, system_prompt | .claude/agents/ |

## 검증
- `Annotated[Union[...], Field(discriminator="kind")]` 판별 유니온. 진입점 `parse_*`/`safe_parse_*`.
- 필드명 snake_case + camelCase alias + `populate_by_name`(ADR-0002).
- `layer`별 추가 가능 kind·기본/고급은 `harness_core/ir/registry.py`(진실원).
