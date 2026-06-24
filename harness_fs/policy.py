"""병합 전략·결과 리포트 값객체 (FS_SPEC A4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class MergeStrategy(Enum):
    """기존 파일 충돌 시 동작. 기본은 비파괴(SKIP_EXISTING)."""

    SKIP_EXISTING = "skip-existing"  # 기본 — 존재하면 건너뜀(비파괴)
    OVERWRITE = "overwrite"  # 명시 — 덮어씀
    BACKUP = "backup"  # 명시 — .bak 보존 후 덮어씀


@dataclass
class Conflict:
    """충돌 항목 — UI 표시용 데이터."""

    path: Path
    reason: str  # "exists"


@dataclass
class WriteReport:
    """write_tree 결과 — created/overwritten/skipped/conflicts."""

    created: list[Path] = field(default_factory=list)
    overwritten: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)

    @property
    def total_written(self) -> int:
        return len(self.created) + len(self.overwritten)
