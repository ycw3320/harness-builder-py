"""생성 대상 선택 — '새 프로젝트' vs '이미 있는 프로젝트에 적용'(1-D 여정 완결).

기존에는 우패널의 '생성 방식' 콤보(minimal/harness-only)를 **미리 이해하고** 골라야
기존 레포에 바로 적용할 수 있었다. 초심자는 그 차이를 모르므로, 생성 버튼을 누른 순간
용도를 묻고 결과(하위 폴더가 생기는지)를 그 자리에서 보여준다.

result_scaffold: "minimal"(새 프로젝트 폴더 생성) | "harness-only"(고른 폴더에 바로 적용)
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .widgets import make_btn


class ExportTargetDialog(QDialog):
    def __init__(self, parent, project_name: str, current: str = "minimal") -> None:
        super().__init__(parent)
        self.result_scaffold: str | None = None
        self._choice = current if current in ("minimal", "harness-only") else "minimal"
        self._project = project_name or "my-project"
        self.setWindowTitle("어디에 만들까요?")
        self.setMinimumWidth(560)

        v = QVBoxLayout(self)
        v.setSpacing(10)
        intro = QLabel("이 하네스를 어떻게 쓸지 고르면, 그에 맞게 파일을 만들어 드려요.")
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        v.addWidget(intro)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for key, title, desc in (
            (
                "minimal",
                "새 프로젝트 만들기",
                f"고른 폴더 안에 '{self._project}' 폴더를 새로 만들고 README·.gitignore 까지 함께 넣어요.",
            ),
            (
                "harness-only",
                "이미 있는 프로젝트에 적용",
                "고른 폴더에 .claude/ 와 CLAUDE.md 만 바로 넣어요 — 기존 파일은 덮어쓰지 않아요.",
            ),
        ):
            b = QPushButton(title)
            b.setObjectName("choiceBtn")
            b.setCheckable(True)
            b.setChecked(key == self._choice)
            b.clicked.connect(lambda _c=False, k=key: self._pick(k))
            self._group.addButton(b)
            v.addWidget(b)
            d = QLabel(desc)
            d.setObjectName("faint")
            d.setWordWrap(True)
            v.addWidget(d)

        self._result = QLabel("")
        self._result.setObjectName("muted")
        self._result.setWordWrap(True)
        v.addWidget(self._result)

        foot = QHBoxLayout()
        foot.addStretch(1)
        foot.addWidget(make_btn("취소", "addBtn", self.reject))
        foot.addWidget(make_btn("폴더 고르기 →", "primaryBtn", self._confirm))
        fw = QWidget()
        fw.setLayout(foot)
        v.addWidget(fw)
        self._update()

    def _pick(self, key: str) -> None:
        self._choice = key
        self._update()

    def _update(self) -> None:
        if self._choice == "minimal":
            self._result.setText(f"→ 고른 폴더 아래에 {self._project}/ 가 새로 생깁니다.")
        else:
            self._result.setText("→ 고른 폴더에 바로 .claude/ 와 CLAUDE.md 가 생깁니다.")

    def _confirm(self) -> None:
        self.result_scaffold = self._choice
        self.accept()
