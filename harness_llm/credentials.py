"""API 키 보안 저장 — OS 자격증명관리자(keyring). 키는 코드/커밋/로그/QSettings에 절대 안 둔다.

keyring 미설치 시 모든 조회는 None/False(오프라인 흐름 유지). 키 값은 어디에도 로그하지 않는다.
"""

from __future__ import annotations

import contextlib

SERVICE = "harness-builder-llm"


def _keyring():
    """keyring 모듈(있으면) — optional 의존성."""
    try:
        import keyring

        return keyring
    except ImportError:
        return None


def available() -> bool:
    """keyring 사용 가능 여부."""
    return _keyring() is not None


def save_api_key(provider: str, key: str) -> None:
    kr = _keyring()
    if kr is None:
        raise RuntimeError("keyring 미설치 — pip install harness-builder[llm]")
    kr.set_password(SERVICE, provider, key)


def get_api_key(provider: str) -> str | None:
    kr = _keyring()
    if kr is None:
        return None
    return kr.get_password(SERVICE, provider)


def has_api_key(provider: str) -> bool:
    return bool(get_api_key(provider))


def delete_api_key(provider: str) -> None:
    kr = _keyring()
    if kr is None:
        return
    with contextlib.suppress(Exception):  # 없는 키 삭제 등은 무시
        kr.delete_password(SERVICE, provider)
