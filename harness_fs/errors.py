"""harness_fs 예외 — UI는 타입으로 분기 (FS_SPEC A4)."""

from __future__ import annotations


class HarnessFsError(Exception):
    """harness_fs 공통 예외 베이스."""


class PathTraversalError(HarnessFsError):
    """대상 폴더를 벗어나는 경로 (보안 차단)."""


class DestNotEmptyError(HarnessFsError):
    """대상 폴더가 비어있지 않음 (정책상 차단 시 — PM3 병합)."""
