"""훅(가드레일) 카탈로그 픽커 — 검증된 보호 훅을 고르면 스크립트까지 자동 채움.

'차단(deny)'과 '경고(warn)'를 배지로 구분해, 무엇이 실제로 막히고 무엇이 경고만인지
고르기 전에 보이게 한다. result_entry(선택 훅) 또는 result_manual(직접 입력).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..catalog import HOOK_CATALOG, HookCatalogEntry
from .widgets import help_chip, make_btn


class HookCatalogDialog(QDialog):
    """모달 픽커 — result_entry(선택 훅) 또는 result_manual(직접 입력)."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.result_entry: HookCatalogEntry | None = None
        self.result_manual = False
        self.setWindowTitle("보호 훅 추가 — 검증된 가드레일 고르기")
        self.setMinimumSize(600, 640)

        v = QVBoxLayout(self)
        v.setSpacing(8)
        intro = QLabel(
            "실행 직전에 위험한 동작을 가로채는 '훅'을 고르면 스크립트까지 자동으로 만들어집니다. "
            "🛑 차단은 그 동작을 실제로 막고, ⚠️ 경고는 막지 않고 주의만 띄웁니다."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        v.addWidget(intro)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        lst = QVBoxLayout(holder)
        lst.setContentsMargins(0, 0, 0, 0)
        lst.setSpacing(8)
        # 차단(deny) 먼저, 경고(warn) 나중 — 강한 보호가 위에 오도록
        for entry in sorted(HOOK_CATALOG, key=lambda e: 0 if e.is_block else 1):
            lst.addWidget(self._hook_card(entry))
        lst.addStretch(1)
        scroll.setWidget(holder)
        v.addWidget(scroll, 1)

        foot = QHBoxLayout()
        foot.addWidget(
            make_btn(
                "목록에 없어요 — 직접 작성",
                "addBtn",
                self._pick_manual,
                tip="카탈로그에 없는 훅은 빈 카드에서 스크립트를 직접 작성합니다(전문가용).",
            )
        )
        foot.addStretch(1)
        foot.addWidget(make_btn("취소", "addBtn", self.reject))
        fw = QWidget()
        fw.setLayout(foot)
        v.addWidget(fw)

    def _hook_card(self, entry: HookCatalogEntry) -> QFrame:
        card = QFrame()
        card.setObjectName("rowCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(4)

        top = QHBoxLayout()
        name = QLabel(entry.display_name)
        name.setObjectName("h1")
        top.addWidget(name)
        top.addStretch(1)
        badge = QLabel("🛑 차단" if entry.is_block else "⚠️ 경고")
        # 차단=심각(lintErr), 경고=주의(lintWarn) 색으로 강도 시각화
        badge.setObjectName("lintErr" if entry.is_block else "lintWarn")
        top.addWidget(badge)
        if entry.note:
            top.addWidget(help_chip(entry.note))
        tw = QWidget()
        tw.setLayout(top)
        cl.addWidget(tw)

        purpose = QLabel(entry.purpose)
        purpose.setObjectName("muted")
        purpose.setWordWrap(True)
        cl.addWidget(purpose)

        protects = QLabel("지키는 것: " + entry.protects)
        protects.setObjectName("faint")
        protects.setWordWrap(True)
        cl.addWidget(protects)

        verb = "차단 훅 추가" if entry.is_block else "경고 훅 추가"
        add = make_btn(verb, "primaryBtn", lambda _c=False, en=entry: self._pick(en))
        cl.addWidget(add)
        return card

    def _pick(self, entry: HookCatalogEntry) -> None:
        self.result_entry = entry
        self.accept()

    def _pick_manual(self) -> None:
        self.result_manual = True
        self.accept()
