"""프로젝트 스택 자동 감지 — 마커 파일로 스택·빌드/테스트 명령 추정 (순수, 프레임워크 무의존).

PM8 QuickStart: '최소 입력' 흐름의 원료 — 사용자가 폴더만 고르면 컨텍스트(스택·명령)를
자동으로 채운다. 결정론(파일 존재·JSON 파싱만, LLM 0회). 감지 실패는 None(흐름은 계속).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DetectedProject:
    stack: str  # 예: "Node.js(npm)", "Python"
    build_cmd: str  # 추정 빌드 명령("" 가능)
    test_cmd: str  # 추정 테스트 명령("" 가능)
    evidence: str  # 근거 파일명(사용자 신뢰용)

    def summary(self) -> str:
        parts = [f"{self.stack} 프로젝트"]
        if self.build_cmd:
            parts.append(f"빌드: {self.build_cmd}")
        if self.test_cmd:
            parts.append(f"테스트: {self.test_cmd}")
        return " · ".join(parts)

    def prose_body(self) -> str:
        """컨텍스트 prose 프리필 본문 — 필드가이드의 '구체 스택·명령' 원칙을 따른다."""
        lines = [f"이 프로젝트는 {self.stack} 기반이다."]
        if self.build_cmd:
            lines.append(f"빌드는 `{self.build_cmd}` 로 한다.")
        if self.test_cmd:
            lines.append(f"테스트는 `{self.test_cmd}` 로 한다.")
        return " ".join(lines)


def _detect_node(root: Path) -> DetectedProject | None:
    pkg = root / "package.json"
    if not pkg.exists():
        return None
    runner = "npm"
    if (root / "pnpm-lock.yaml").exists():
        runner = "pnpm"
    elif (root / "yarn.lock").exists():
        runner = "yarn"
    build_cmd, test_cmd = "", ""
    try:
        scripts = json.loads(pkg.read_text(encoding="utf-8")).get("scripts", {}) or {}
        if "build" in scripts:
            build_cmd = f"{runner} run build"
        if "test" in scripts:
            test_cmd = f"{runner} test" if runner == "npm" else f"{runner} run test"
    except (json.JSONDecodeError, OSError):
        pass  # scripts 없이도 스택 감지는 유효
    return DetectedProject(f"Node.js({runner})", build_cmd, test_cmd, "package.json")


def _detect_python(root: Path) -> DetectedProject | None:
    if (root / "pyproject.toml").exists():
        test = "pytest" if (root / "tests").exists() else ""
        return DetectedProject("Python", "", test, "pyproject.toml")
    if (root / "requirements.txt").exists():
        return DetectedProject("Python", "", "", "requirements.txt")
    return None


_SIMPLE_MARKERS = [
    ("pom.xml", "Java(Maven)", "mvn package", "mvn test"),
    ("build.gradle", "Java(Gradle)", "gradle build", "gradle test"),
    ("build.gradle.kts", "Kotlin(Gradle)", "gradle build", "gradle test"),
    ("go.mod", "Go", "go build ./...", "go test ./..."),
    ("Cargo.toml", "Rust", "cargo build", "cargo test"),
    ("Gemfile", "Ruby", "", "bundle exec rspec"),
    ("composer.json", "PHP", "", ""),
]


def detect_project(root_path: str) -> DetectedProject | None:
    """폴더 루트의 마커 파일로 스택 감지 — 우선순위: Node → Python → 기타 마커."""
    root = Path(root_path)
    if not root.is_dir():
        return None
    for probe in (_detect_node, _detect_python):
        found = probe(root)
        if found:
            return found
    for marker, stack, build, test in _SIMPLE_MARKERS:
        if (root / marker).exists():
            return DetectedProject(stack, build, test, marker)
    return None
