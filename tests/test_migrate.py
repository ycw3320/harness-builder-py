"""PM7-S2 통합 하네스 파일 — load_ir_any/dump_ir 라운드트립·버전 마이그레이션 (ADR-0013)."""

import pytest

from harness_core.ir.migrate import CURRENT_IR_VERSION, MIGRATIONS, dump_ir, load_ir_any
from harness_core.ir.presets import safety_first_preset


def test_roundtrip_dump_load_dump_identical():
    ir = safety_first_preset("demo")
    text = dump_ir(ir)
    again = dump_ir(load_ir_any(text))
    assert text == again  # 저장→열기→저장 바이트 동일(무손실)


def test_load_accepts_frozen_golden(golden):
    # frozen 골든 preset_ir 은 이 포맷의 박제본 — 파일 열기 경로가 항상 수용해야 한다.
    import json

    ir = load_ir_any(json.dumps(golden("preset_ir")))
    assert ir.meta.ir_version == CURRENT_IR_VERSION
    assert ir.components


def test_unknown_version_raises():
    ir = safety_first_preset("demo")
    text = dump_ir(ir).replace('"irVersion": "1.0"', '"irVersion": "99.0"')
    with pytest.raises(ValueError, match="지원하지 않는 IR 버전"):
        load_ir_any(text)


def test_invalid_json_raises():
    with pytest.raises(ValueError, match="JSON"):
        load_ir_any("{ 깨진 파일")
    with pytest.raises(ValueError):
        load_ir_any("[1, 2]")  # 최상위가 객체 아님


def test_migration_chain_applies(monkeypatch):
    # 가상 구버전 0.9 → 1.0 변환기 등록 시 순차 마이그레이션이 동작하는지.
    def bump(data: dict) -> dict:
        data["meta"]["irVersion"] = "1.0"
        return data

    monkeypatch.setitem(MIGRATIONS, "0.9", bump)
    text = dump_ir(safety_first_preset("demo")).replace('"irVersion": "1.0"', '"irVersion": "0.9"')
    ir = load_ir_any(text)
    assert ir.meta.ir_version == "1.0"
