"""PyInstaller 빌드 — Windows 단일 실행본(.exe). 실행: python packaging/build_exe.py

산출: dist/HarnessBuilder.exe. anthropic·keyring(인앱 LLM)은 지연 import 라 명시 수집.
spec/build 산출물은 .gitignore(build/·dist/·*.spec) 대상.
"""

import os
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "packaging" / "app_entry.py"
FONTS = ROOT / "harness_app" / "qt_shell" / "fonts"  # 번들 Pretendard

PyInstaller.__main__.run(
    [
        str(ENTRY),
        "--name",
        "HarnessBuilder",
        "--noconfirm",
        "--windowed",
        "--onefile",
        # 번들 폰트를 런타임 __file__ 기준 경로(harness_app/qt_shell/fonts)에 동일 배치
        "--add-data",
        f"{FONTS}{os.pathsep}harness_app/qt_shell/fonts",
        "--collect-all",
        "anthropic",
        "--collect-all",
        "keyring",
        "--collect-submodules",
        "pydantic",
        "--collect-submodules",
        "pydantic_core",
        # 리포 루트를 모듈 탐색 경로에 명시 — cwd·편집설치(PEP 660 finder) 무관하게
        # harness_app/harness_core 수집 보장(누락 시 windowed exe 가 부팅 즉사).
        "--paths",
        str(ROOT),
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT / "build"),
    ]
)
