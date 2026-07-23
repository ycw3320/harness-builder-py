"""권한 패턴 조립기 다이얼로그 — 문법 없이 도구·동작·평문 입력으로 권한 규칙 만들기.

result_rule(조립된 PermissionRule) 또는 result_manual(직접 입력=기존 빈 카드).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..perm_assembler import (
    ACTIONS,
    TOOL_SPECS,
    build_permission,
    compose_pattern,
    match_explanation,
)
from .widgets import make_btn


class PermissionAssemblerDialog(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.result_rule = None
        self.result_manual = False
        self._action = "deny"
        self.setWindowTitle("권한 규칙 만들기 — 문법 없이 조립")
        self.setMinimumWidth(560)

        v = QVBoxLayout(self)
        v.setSpacing(10)
        intro = QLabel(
            "도구를 고르고 명령·경로를 평범하게 적으면 올바른 권한 패턴이 자동으로 만들어집니다. "
            "아래 미리보기로 '무엇에 걸리는지' 바로 확인하세요."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        v.addWidget(intro)

        # ① 동작(허용/질문/금지)
        v.addWidget(self._section("① 어떻게 할까요?"))
        act_row = QHBoxLayout()
        self._act_group = QButtonGroup(self)
        self._act_group.setExclusive(True)
        for key, label, desc in ACTIONS:
            b = QPushButton(f"{label} — {desc}")
            b.setObjectName("choiceBtn")
            b.setCheckable(True)
            b.setChecked(key == self._action)
            b.clicked.connect(lambda _c=False, k=key: self._set_action(k))
            self._act_group.addButton(b)
            act_row.addWidget(b)
        aw = QWidget()
        aw.setLayout(act_row)
        v.addWidget(aw)

        # ② 도구
        v.addWidget(self._section("② 어떤 도구를?"))
        self._tool_combo = QComboBox()
        for spec in TOOL_SPECS:
            self._tool_combo.addItem(spec.label, spec.tool)
        self._tool_combo.currentIndexChanged.connect(self._on_tool_change)
        v.addWidget(self._tool_combo)
        self._tool_hint = QLabel("")
        self._tool_hint.setObjectName("faint")
        self._tool_hint.setWordWrap(True)
        v.addWidget(self._tool_hint)

        # ③ 평문 입력
        self._input_label = self._section("③ 무엇을?")
        v.addWidget(self._input_label)
        self._input = QLineEdit()
        self._input.textChanged.connect(self._update_preview)
        v.addWidget(self._input)
        # command 전용: 접두/정확 토글
        self._prefix_cb = QCheckBox("이 명령으로 시작하는 것 모두 (끄면 정확히 이것만)")
        self._prefix_cb.setChecked(True)
        self._prefix_cb.stateChanged.connect(self._update_preview)
        v.addWidget(self._prefix_cb)
        # domain 전용: 하위 도메인 포함
        self._subdomain_cb = QCheckBox("하위 도메인 포함 (예: *.example.com)")
        self._subdomain_cb.stateChanged.connect(self._update_preview)
        v.addWidget(self._subdomain_cb)

        # 미리보기(생성 패턴 + 무엇에 걸리나)
        v.addWidget(self._section("미리보기"))
        self._preview_pat = QLabel("")
        self._preview_pat.setObjectName("h1")
        self._preview_pat.setWordWrap(True)
        v.addWidget(self._preview_pat)
        self._preview_exp = QLabel("")
        self._preview_exp.setObjectName("muted")
        self._preview_exp.setWordWrap(True)
        v.addWidget(self._preview_exp)

        # 버튼
        foot = QHBoxLayout()
        foot.addWidget(
            make_btn(
                "직접 입력(고급)",
                "addBtn",
                self._pick_manual,
                tip="조립기 대신 빈 카드에서 패턴을 직접 타이핑",
            )
        )
        foot.addStretch(1)
        foot.addWidget(make_btn("취소", "addBtn", self.reject))
        self._make_btn = make_btn("이 규칙 추가", "primaryBtn", self._confirm)
        foot.addWidget(self._make_btn)
        fw = QWidget()
        fw.setLayout(foot)
        v.addWidget(fw)

        self._on_tool_change()  # 초기 힌트·토글 상태 세팅

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    def _cur_tool(self) -> str:
        return self._tool_combo.currentData()

    def _cur_spec(self):
        return next(s for s in TOOL_SPECS if s.tool == self._cur_tool())

    def _set_action(self, key: str) -> None:
        self._action = key
        self._update_preview()

    def _on_tool_change(self) -> None:
        spec = self._cur_spec()
        self._tool_hint.setText(spec.purpose + "  예: " + ", ".join(spec.examples[:3]))
        self._input_label.setText(f"③ 무엇을? ({spec.input_label})")
        self._input.setPlaceholderText(spec.placeholder)
        # 토글은 kind 별로만 노출
        self._prefix_cb.setVisible(spec.kind == "command")
        self._subdomain_cb.setVisible(spec.kind == "domain")
        self._update_preview()

    def _update_preview(self) -> None:
        tool = self._cur_tool()
        text = self._input.text()
        prefix = self._prefix_cb.isChecked()
        sub = self._subdomain_cb.isChecked()
        pat = compose_pattern(tool, text, prefix, sub)
        exp = match_explanation(tool, text, prefix, sub)
        act = {"allow": "허용", "ask": "질문", "deny": "금지"}[self._action]
        self._preview_pat.setText(f"{act}:  {pat}")
        self._preview_exp.setText("→ " + exp)

    def _confirm(self) -> None:
        spec = self._cur_spec()
        self.result_rule = build_permission(
            self._action,
            self._cur_tool(),
            self._input.text(),
            self._prefix_cb.isChecked(),
            self._subdomain_cb.isChecked() if spec.kind == "domain" else False,
        )
        self.accept()

    def _pick_manual(self) -> None:
        self.result_manual = True
        self.accept()
