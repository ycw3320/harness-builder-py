import pytest

from harness_core.ir.factory import create_component
from harness_core.ir.registry import kind_registry
from harness_core.ir.schema import parse_component


@pytest.mark.parametrize("kind", list(kind_registry.keys()))
def test_create_component(kind):
    c = create_component(kind, kind_registry[kind]["defaultLayer"])
    assert c.kind == kind
    assert c.enabled is True
    parse_component(c.model_dump())  # 재검증: 생성물이 schema 통과
