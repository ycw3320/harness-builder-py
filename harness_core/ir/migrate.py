"""IR 버전 마이그레이션 — .harness.json(저장=공유) 파일의 미래 호환 단일 진입점 (ADR-0013).

코어 ADD(기존 표면 무변경): 저장/열기/공유로 디스크에 남는 IR 이 스키마 진화 후에도
열리도록, ir_version 을 읽어 순차 변환 뒤 검증 파싱한다. 현재는 1.0 단일 버전이라
MIGRATIONS 는 비어 있다 — 스키마가 버전을 올리는 커밋에서만 변환기를 등록한다.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from .schema import HarnessIR

CURRENT_IR_VERSION = "1.0"

# 구버전 문자열 → '다음 버전으로 올린 dict' 를 반환하는 순수 변환기.
MIGRATIONS: dict[str, Callable[[dict], dict]] = {}


def _read_version(data: dict) -> str:
    meta = data.get("meta") or {}
    return str(meta.get("irVersion") or meta.get("ir_version") or CURRENT_IR_VERSION)


def load_ir_any(text: str) -> HarnessIR:
    """JSON 텍스트 → (필요 시 순차 마이그레이션) → 검증된 HarnessIR.

    ValueError: JSON 오류·모르는 버전. pydantic ValidationError: 스키마 불일치.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 형식이 아닙니다: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("하네스 파일 형식이 아닙니다(최상위가 객체가 아님)")
    version = _read_version(data)
    seen: set[str] = set()
    while version != CURRENT_IR_VERSION:
        if version in seen or version not in MIGRATIONS:
            raise ValueError(f"지원하지 않는 IR 버전: {version} (현재 {CURRENT_IR_VERSION})")
        seen.add(version)
        data = MIGRATIONS[version](data)
        version = _read_version(data)
    return HarnessIR.model_validate(data)


def dump_ir(ir: HarnessIR) -> str:
    """저장/공유용 직렬화 — camelCase alias·들여쓰기 2·LF(결정론)."""
    return ir.model_dump_json(by_alias=True, indent=2) + "\n"
