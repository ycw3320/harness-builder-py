"""훅 실행환경 precheck (앱 계층 순수 로직) — 발견 B '크로스플랫폼 거짓 안전' 제거.

문제: 프리셋·카탈로그 훅은 전부 `#!/usr/bin/env bash` 인데 주 타깃은 Windows.
git-bash/WSL 이 없으면 훅이 **조용히 미실행**되는데도 시뮬은 '차단'을 표시하고
성숙도는 Lv4 '검증됨' 까지 도달한다 → 도구가 없는 안전을 있다고 말하는 상태.

해법(티어1·앱 전용·코어 무수정): 산출될 훅 스크립트의 shebang 이 요구하는 인터프리터가
이 PC 에서 실행 가능한지 검사하고, 미충족이면 ①완료 문구를 단정→조건부로 강등
②성숙도 Lv4 를 보류(Lv3)한다. 검사 대상은 '지금 이 PC'이므로 결과는 환경 의존 —
코어(결정론 IR 함수)가 아니라 앱 계층에 두는 이유다.

정직 원칙: 실행 가능해도 '훅이 옳게 동작한다'는 보증이 아니다(그건 스크립트 내용의 문제).
여기서 판정하는 것은 오직 '인터프리터 부재로 훅이 통째로 미실행될 위험'뿐이다.
"""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass, field

# shebang 첫 줄 → 필요한 실행기 키. `#!/usr/bin/env bash`·`#!/bin/bash` 모두 bash.
# 주의: 부분문자열 매칭이면 'pwsh'·'zsh' 가 'sh' 로, 'python3' 가 'python' 뒤 숫자까지
# 뭉개진다 → 실행기 토큰을 단어 경계로 뽑아 정확히 대응시킨다.
_SHEBANG_KEYS: tuple[tuple[str, str], ...] = (
    ("bash", "bash"),
    ("zsh", "zsh"),
    ("pwsh", "pwsh"),
    ("powershell", "powershell"),
    ("python", "python"),
    ("node", "node"),
    ("sh", "sh"),  # 가장 느슨 — 위 항목이 모두 빗나갔을 때만
)

# 실행기별 한국어 이름·설치 안내(초심자용 — 화면에 보이는 말로).
_RUNTIME_INFO: dict[str, tuple[str, str]] = {
    "bash": ("bash", "Windows 라면 Git for Windows(Git Bash)를 설치하면 함께 설치됩니다."),
    "sh": ("sh", "Windows 라면 Git for Windows(Git Bash)를 설치하면 함께 설치됩니다."),
    "zsh": ("zsh", "macOS 는 기본 포함. Windows 는 별도 설치가 필요합니다."),
    "pwsh": ("PowerShell 7", "PowerShell 7(pwsh)을 설치하면 사용할 수 있습니다."),
    "powershell": ("Windows PowerShell", "Windows 에 기본 포함되어 있습니다."),
    "python": ("Python", "python.org 에서 설치할 수 있습니다."),
    "node": ("Node.js", "nodejs.org 에서 설치할 수 있습니다."),
}


def required_runtime(script_body: str) -> str | None:
    """스크립트 첫 줄(shebang) → 필요한 실행기 키. shebang 없으면 None."""
    first = (script_body or "").splitlines()[0] if script_body else ""
    if not first.startswith("#!"):
        return None
    line = first.lower()
    for token, key in _SHEBANG_KEYS:
        # 경로·인자 구분자로 둘러싸인 토큰만(예: /usr/bin/env bash, /bin/bash, pwsh -File).
        # python3.11 처럼 버전 접미사와 Windows 의 .exe 확장자도 실행기명으로 허용.
        if re.search(rf"(^|[/\\\s]){re.escape(token)}[0-9.]*(\.exe)?($|[\s\-])", line):
            return key
    return None


def runtime_available(key: str) -> bool:
    """이 PC 에서 해당 실행기를 실제로 찾을 수 있는가(PATH 조회)."""
    if key == "powershell" and sys.platform == "win32":
        return True  # Windows 기본 탑재
    if key == "python":
        return True  # 이 앱이 Python 으로 돌고 있음
    return shutil.which(key) is not None


@dataclass(frozen=True)
class HookRuntimeVM:
    """훅 실행환경 precheck 결과 — UI 문구·성숙도 판정의 입력."""

    missing: tuple[str, ...] = ()  # 부재 실행기 키(예: ("bash",))
    affected_titles: tuple[str, ...] = ()  # 그 때문에 미실행될 훅 제목
    blocking_affected: bool = False  # 그중 '차단(deny)' 훅이 포함되는가
    checked: int = 0  # 검사한 훅 수
    notes: tuple[str, ...] = field(default=())  # 설치 안내(사람 말)

    @property
    def ok(self) -> bool:
        """모든 훅의 실행기가 이 PC 에 존재."""
        return not self.missing

    @property
    def runtime_names(self) -> str:
        return ", ".join(_RUNTIME_INFO.get(k, (k, ""))[0] for k in self.missing)


def check_hook_runtimes(ir, available=runtime_available) -> HookRuntimeVM:
    """활성 훅의 shebang 실행기가 이 PC 에 있는지 검사.

    available 은 테스트에서 주입 가능(환경 비의존 회귀 확보).
    """
    hooks = [c for c in ir.components if c.enabled and c.kind == "hook"]
    missing: list[str] = []
    titles: list[str] = []
    blocking = False
    for h in hooks:
        key = required_runtime(getattr(h, "script_body", ""))
        if key is None or available(key):
            continue
        if key not in missing:
            missing.append(key)
        titles.append(h.title)
        if getattr(h, "action", "") == "deny":
            blocking = True
    notes = tuple(_RUNTIME_INFO.get(k, (k, ""))[1] for k in missing)
    return HookRuntimeVM(
        missing=tuple(missing),
        affected_titles=tuple(titles),
        blocking_affected=blocking,
        checked=len(hooks),
        notes=notes,
    )
