"""PyInstaller 빌드 — Windows 단일 실행본(.exe). 실행: python packaging/build_exe.py

산출: dist/HarnessBuilder.exe. anthropic·keyring(인앱 LLM)은 지연 import 라 명시 수집.
spec/build 산출물은 .gitignore(build/·dist/·*.spec) 대상.
"""

from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "packaging" / "app_entry.py"

PyInstaller.__main__.run(
    [
        str(ENTRY),
        "--name",
        "HarnessBuilder",
        "--noconfirm",
        "--windowed",
        "--onefile",
        "--collect-all",
        "anthropic",
        "--collect-all",
        "keyring",
        "--collect-submodules",
        "pydantic",
        "--collect-submodules",
        "pydantic_core",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT / "build"),
    ]
)
