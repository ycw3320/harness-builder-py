import json
import os
import pathlib

import pytest

_GOLDEN = pathlib.Path(__file__).parent / "golden"
# 2계층 골든(ADR-0012):
# frozen=TS 기원 박제(영구 불변) / extended=Python 자체 박제(신규 코어 ADD 전용)
_GOLDEN_TIERS = (_GOLDEN / "frozen", _GOLDEN / "extended")


@pytest.fixture
def golden():
    def _load(name: str):
        for tier in _GOLDEN_TIERS:
            p = tier / f"{name}.json"
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"golden fixture 없음: {name} (frozen/extended 모두)")

    return _load


@pytest.fixture(scope="session")
def qapp():
    """오프스크린 QApplication (세션 1회) — Qt 셸 상태기계 테스트용.

    지연 import: 이 픽스처를 쓰는 테스트에서만 PySide6 를 로드한다(순수 테스트 무영향).
    """
    # setdefault: CI 가 다른 플랫폼 플러그인을 강제할 수 있게 기존 값 존중
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.pop("HB_THEME", None)  # 개발 머신 테마 env 가 테스트를 오염시키지 않게 스크럽
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def temp_settings(tmp_path):
    """파일 기반 QSettings — 사용자 레지스트리(QSettings 기본)와 격리."""
    from PySide6.QtCore import QSettings

    return QSettings(str(tmp_path / "test-settings.ini"), QSettings.Format.IniFormat)
