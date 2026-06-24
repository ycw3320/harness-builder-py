"""가상 파일트리 → 디스크 안전 쓰기 (FS_SPEC A1).

불변식: 전수검증(traversal 차단)→부분쓰기 금지 · UTF-8/LF 보존·BOM 금지 · dry_run 무변경 · 멱등.
"""

from __future__ import annotations

from pathlib import Path

from harness_core.export.export_ir import VirtualFile

from .errors import PathTraversalError
from .policy import Conflict, MergeStrategy, WriteReport


def _resolve_inside(dest_resolved: Path, rel: str) -> Path:
    """rel 을 dest 하위 절대경로로 해석 — 벗어나면 PathTraversalError."""
    try:
        resolved = (dest_resolved / rel).resolve()
    except (OSError, RuntimeError) as e:  # pragma: no cover - 비정상 경로
        raise PathTraversalError(f"경로 해석 실패: {rel}") from e
    if not resolved.is_relative_to(dest_resolved):
        raise PathTraversalError(f"대상 폴더를 벗어나는 경로 차단: {rel}")
    return resolved


def write_tree(
    tree: list[VirtualFile],
    dest: Path | str,
    *,
    strategy: MergeStrategy = MergeStrategy.SKIP_EXISTING,
    dry_run: bool = False,
    make_dest: bool = True,
) -> WriteReport:
    """tree 를 dest 폴더에 안전하게 기록. 기본 비파괴(SKIP_EXISTING)·dry_run 미리보기."""
    dest = Path(dest)
    dest_resolved = dest.resolve()

    # 1. 전수검증 우선 — 하나라도 위반 시 0건 기록(부분쓰기 금지)
    planned: list[tuple[VirtualFile, Path]] = [
        (vf, _resolve_inside(dest_resolved, vf.path)) for vf in tree
    ]

    report = WriteReport()
    if make_dest and not dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    for vf, target in planned:
        exists = target.exists()
        if exists and strategy is MergeStrategy.SKIP_EXISTING:
            report.skipped.append(target)
            report.conflicts.append(Conflict(path=target, reason="exists"))
            continue
        if exists:
            report.overwritten.append(target)
            if strategy is MergeStrategy.BACKUP and not dry_run:
                bak = target.with_name(target.name + ".bak")
                bak.write_bytes(target.read_bytes())
        else:
            report.created.append(target)
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            # UTF-8 고정 · newline="" 로 코어가 만든 LF 그대로 · BOM 금지
            with target.open("w", encoding="utf-8", newline="") as f:
                f.write(vf.content)
    return report
