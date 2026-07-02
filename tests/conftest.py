import json
import os
import pathlib

import pytest

_GOLDEN = pathlib.Path(__file__).parent / "golden"


@pytest.fixture
def golden():
    def _load(name: str):
        return json.loads((_GOLDEN / f"{name}.json").read_text(encoding="utf-8"))

    return _load


@pytest.fixture(scope="session")
def qapp():
    """오프스크린 QApplication (세션 1회) — Qt 셸 상태기계 테스트용.

    지연 import: 이 픽스처를 쓰는 테스트에서만 PySide6 를 로드한다(순수 테스트 무영향).
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def temp_settings(tmp_path):
    """파일 기반 QSettings — 사용자 레지스트리(QSettings 기본)와 격리."""
    from PySide6.QtCore import QSettings

    return QSettings(str(tmp_path / "test-settings.ini"), QSettings.Format.IniFormat)
