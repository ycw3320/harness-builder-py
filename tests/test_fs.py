"""write_tree 안전 쓰기 검증 — 비파괴·traversal 차단·dry_run·LF 보존 (FS_SPEC A1)."""

import pytest

from harness_core.export.export_ir import VirtualFile, export_ir
from harness_core.ir.presets import safety_first_preset
from harness_fs.errors import PathTraversalError
from harness_fs.policy import MergeStrategy
from harness_fs.writer import write_tree


def test_write_creates_all_files(tmp_path):
    tree = export_ir(safety_first_preset("demo"))
    report = write_tree(tree, tmp_path)
    assert len(report.created) == len(tree)
    for vf in tree:
        assert (tmp_path / vf.path).read_text(encoding="utf-8") == vf.content


def test_dry_run_no_disk_change(tmp_path):
    tree = export_ir(safety_first_preset("demo"))
    report = write_tree(tree, tmp_path, dry_run=True)
    assert len(report.created) == len(tree)  # 리포트는 실제와 동일
    assert list(tmp_path.iterdir()) == []  # 디스크 무변경


def test_idempotent_skip_existing(tmp_path):
    tree = export_ir(safety_first_preset("demo"))
    write_tree(tree, tmp_path)
    report2 = write_tree(tree, tmp_path)  # 재적용
    assert report2.created == []
    assert len(report2.skipped) == len(tree)


def test_overwrite_strategy(tmp_path):
    write_tree([VirtualFile("a.txt", "v1\n")], tmp_path)
    report = write_tree([VirtualFile("a.txt", "v2\n")], tmp_path, strategy=MergeStrategy.OVERWRITE)
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "v2\n"
    assert len(report.overwritten) == 1


def test_backup_strategy_preserves_original(tmp_path):
    write_tree([VirtualFile("a.txt", "v1\n")], tmp_path)
    write_tree([VirtualFile("a.txt", "v2\n")], tmp_path, strategy=MergeStrategy.BACKUP)
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "v2\n"
    assert (tmp_path / "a.txt.bak").read_text(encoding="utf-8") == "v1\n"


def test_traversal_blocked_no_partial_write(tmp_path):
    tree = [VirtualFile("ok.txt", "x\n"), VirtualFile("../evil.txt", "bad\n")]
    with pytest.raises(PathTraversalError):
        write_tree(tree, tmp_path)
    assert not (tmp_path / "ok.txt").exists()  # 0건 기록(부분쓰기 금지)


def test_lf_preserved_no_crlf(tmp_path):
    write_tree([VirtualFile("a.txt", "line1\nline2\n")], tmp_path)
    raw = (tmp_path / "a.txt").read_bytes()
    assert b"\r\n" not in raw


def test_empty_content_created(tmp_path):
    write_tree([VirtualFile(".claude/.gitkeep", "")], tmp_path)
    assert (tmp_path / ".claude" / ".gitkeep").exists()


def test_nested_dirs_created(tmp_path):
    write_tree([VirtualFile(".claude/hooks/x.sh", "#!/bin/sh\n")], tmp_path)
    assert (tmp_path / ".claude" / "hooks" / "x.sh").read_text(encoding="utf-8") == "#!/bin/sh\n"
