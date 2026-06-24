"""역import 디스크 어댑터 — 폴더 → 파일트리 dict → core.import_ir (export_ir 산출과 대칭)."""

from __future__ import annotations

from pathlib import Path

from harness_core.export.import_ir import import_ir
from harness_core.ir.schema import HarnessIR

_TOP = ["CLAUDE.md", "_global/CLAUDE.md", ".mcp.json", ".claude/settings.json"]
_DIRS = [".claude/rules", ".claude/hooks", ".claude/agents"]


def read_tree(root: Path) -> dict[str, str]:
    """관심 파일만 UTF-8 로 읽어 path→content dict (export_ir 산출 경로와 대칭)."""
    root = Path(root)
    files: dict[str, str] = {}
    for rel in _TOP:
        p = root / rel
        if p.is_file():
            files[rel] = p.read_text(encoding="utf-8")
    for d in _DIRS:
        base = root / d
        if base.is_dir():
            for p in sorted(base.iterdir()):
                if p.is_file():
                    files[f"{d}/{p.name}"] = p.read_text(encoding="utf-8")
    return files


def import_project(root: Path | str, project_name: str | None = None) -> HarnessIR:
    root = Path(root)
    name = project_name or root.name or "imported-project"
    return import_ir(read_tree(root), name)
