# FS 명세 (직접쓰기 · 병합) — harness_fs

> 가상 파일트리(`VirtualFile{path, content}`)를 실제 폴더에 **안전하게** 쓰고 병합한다. 안전이 최우선(ADR-0005·북극성).

## A1 write_tree
```python
def write_tree(
    tree: list[VirtualFile], dest: Path, *,
    strategy: MergeStrategy = MergeStrategy.SKIP_EXISTING,
    dry_run: bool = False, make_dest: bool = True,
) -> WriteReport
```
**규칙(불변식):**
1. **전수검증 우선** — 모든 경로가 `dest` 안인지 확인(traversal 차단). 하나라도 위반 시 **0건 기록**(부분쓰기 금지).
2. **개행·인코딩 보존** — UTF-8 고정, `newline=""`(코어가 만든 `\n` 그대로), BOM 금지.
3. **빈 내용(.gitkeep)도 생성.**
4. **dry_run** — 디스크 무변경 + 실제와 동일한 `WriteReport` 반환(미리보기).
5. **멱등** — 같은 IR 재적용 시 SKIP_EXISTING이면 변화 없음.

## A4 정책·예외 (enum)
- `MergeStrategy`: `SKIP_EXISTING`(기본·비파괴) / `OVERWRITE`(명시) / `BACKUP`(.bak 보존)
- 예외: `HarnessFsError` · `PathTraversalError` · `DestNotEmptyError` (한국어 메시지 포함, UI는 타입으로 분기)

## WriteReport
`{ created: list[Path], overwritten: list[Path], skipped: list[Path], conflicts: list[Conflict] }`

## A2 merge (PM2말~PM3)
- 기본 **비파괴**, 충돌은 **데이터로 반환**(결정은 UI B5c).
- JSON류(settings.json/.mcp.json) 딥머지(PM3): permissions는 합집합+dedupe-sort(코어 export 규칙과 동일). CLAUDE.md는 마커 구간만 교체(멱등).

## 북극성
초심자가 실수로 기존 파일을 덮어쓰지 못하게 **비파괴 디폴트 + dry-run 미리보기 강제**.
