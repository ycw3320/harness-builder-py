import json
import pathlib

import pytest

_GOLDEN = pathlib.Path(__file__).parent / "golden"


@pytest.fixture
def golden():
    def _load(name: str):
        return json.loads((_GOLDEN / f"{name}.json").read_text(encoding="utf-8"))

    return _load
