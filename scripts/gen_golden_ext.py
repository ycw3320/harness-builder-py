"""extended 골든 재생성 — 신규 코어 ADD 전용 (ADR-0012).

frozen/ 은 TS 기원 박제라 이 스크립트가 절대 건드리지 않는다.
규율: 생성 커밋(이 스크립트 실행)과 검증 커밋(코어 변경)을 분리 — 같은 커밋에서
코어와 extended 골든을 함께 바꾸면 게이트가 무력화된다.

사용: python scripts/gen_golden_ext.py
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

EXT = Path(__file__).resolve().parent.parent / "tests" / "golden" / "extended"

# name → 생성 함수. 신규 코어 ADD 가 골든을 요구하면 여기에 등록한다.
# 예: "lint_security_preset":
#     lambda: lint_ir(safety_first_preset("golden"), rulesets=("core", "security"))
GENERATORS: dict[str, Callable[[], object]] = {}


def main() -> None:
    EXT.mkdir(parents=True, exist_ok=True)
    if not GENERATORS:
        print("등록된 extended 생성기가 없습니다 — 신규 코어 ADD 시 GENERATORS 에 등록하세요.")
        return
    for name, gen in GENERATORS.items():
        out = EXT / f"{name}.json"
        out.write_text(
            json.dumps(gen(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        print("생성:", out)


if __name__ == "__main__":
    main()
