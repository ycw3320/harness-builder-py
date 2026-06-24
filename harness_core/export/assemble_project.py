"""exportIR 결과를 '즉시 진행 가능한 폴더 트리'로 조립 (TS assembleProject.ts 포팅).

minimal: <projectName>/ 루트 + 골격 + _APPLY/. harness-only: 루트 + _APPLY/.
전역 지침(_global/CLAUDE.md)은 항상 _APPLY/ 로 분리.
"""

from __future__ import annotations

from ..ir.schema import HarnessIR
from .export_ir import VirtualFile, export_ir
from .scaffold_templates import (
    apply_md_template,
    gitignore_template,
    readme_template,
    settings_local_template,
)


def assemble_project(ir: HarnessIR, scaffold: str = "minimal") -> list[VirtualFile]:
    project_name = ir.meta.project_name or "my-project"
    minimal = scaffold == "minimal"
    prefix = f"{project_name}/" if minimal else ""

    files: list[VirtualFile] = []
    apply_files: list[VirtualFile] = [
        VirtualFile("_APPLY/APPLY.md", apply_md_template(project_name, scaffold))
    ]

    for f in export_ir(ir):
        if f.path == "_global/CLAUDE.md":
            apply_files.append(VirtualFile("_APPLY/global-CLAUDE.md", f.content))
            continue
        files.append(VirtualFile(prefix + f.path, f.content))

    if minimal:
        files.append(VirtualFile(f"{prefix}README.md", readme_template(project_name)))
        files.append(VirtualFile(f"{prefix}.gitignore", gitignore_template()))
        files.append(VirtualFile(f"{prefix}.claude/settings.local.json", settings_local_template()))
        for d in ("commands", "skills", "output-styles"):
            files.append(VirtualFile(f"{prefix}.claude/{d}/.gitkeep", ""))

    return sorted([*files, *apply_files], key=lambda f: f.path)
