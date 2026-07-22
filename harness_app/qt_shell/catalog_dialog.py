"""MCP 서버 카탈로그 픽커 — '고르면 자동 채움'(사용자 피드백: 빈 칸에 뭘 넣을지 모름).

유명 서버 목록에서 고르면 command·args·env 가 채워진 McpServer 를 돌려준다(result_entry).
'직접 입력'을 고르면 result_manual=True — 호출부가 기존 빈 카드 생성으로 폴백.
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

from ..catalog import MCP_CATALOG, CatalogEntry
from .widgets import help_chip, make_btn


class McpCatalogDialog(QDialog):
    """모달 픽커 — result_entry(선택 서버) 또는 result_manual(직접 입력)."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.result_entry: CatalogEntry | None = None
        self.result_manual = False
        self.setWindowTitle("외부 도구 연결 — 서버 고르기")
        self.setMinimumSize(560, 620)

        v = QVBoxLayout(self)
        v.setSpacing(8)
        intro = QLabel(
            "연결할 외부 도구(MCP 서버)를 고르면 실행 명령·인자·필요 키가 자동으로 채워집니다. "
            "고른 뒤 폴더 경로나 비밀키만 채우면 돼요."
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
        for entry in MCP_CATALOG:
            lst.addWidget(self._server_card(entry))
        lst.addStretch(1)
        scroll.setWidget(holder)
        v.addWidget(scroll, 1)

        foot = QHBoxLayout()
        foot.addWidget(
            make_btn(
                "목록에 없어요 — 직접 입력",
                "addBtn",
                self._pick_manual,
                tip="카탈로그에 없는 서버는 빈 카드에서 직접 채웁니다(전문가용).",
            )
        )
        foot.addStretch(1)
        foot.addWidget(make_btn("취소", "addBtn", self.reject))
        fw = QWidget()
        fw.setLayout(foot)
        v.addWidget(fw)

    def _server_card(self, entry: CatalogEntry) -> QFrame:
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
        # 필요 키·비용 배지(있을 때만) — 고르기 전에 '뭘 준비해야 하는지' 미리 보이게
        for badge_text in self._badges(entry):
            b = QLabel(badge_text)
            b.setObjectName("helpChip")
            top.addWidget(b)
        note = (entry.note + (" " + entry.cost_note if entry.cost_note else "")).strip()
        if note:
            top.addWidget(help_chip(note))
        tw = QWidget()
        tw.setLayout(top)
        cl.addWidget(tw)

        purpose = QLabel(entry.purpose)
        purpose.setObjectName("muted")
        purpose.setWordWrap(True)
        cl.addWidget(purpose)
        if entry.cost_note:
            cost = QLabel("비용 주의: " + entry.cost_note)
            cost.setObjectName("lintWarn")
            cost.setWordWrap(True)
            cl.addWidget(cost)

        short = entry.display_name.split(" — ")[0]
        add = make_btn(f"{short} 연결하기", "primaryBtn", lambda _c=False, en=entry: self._pick(en))
        cl.addWidget(add)
        return card

    @staticmethod
    def _badges(entry: CatalogEntry) -> list[str]:
        out: list[str] = []
        if entry.required_keys:
            out.append("키 필요")
        if entry.cost_note:
            out.append("과금")
        if "Docker" in entry.note:
            out.append("Docker")
        return out

    def _pick(self, entry: CatalogEntry) -> None:
        self.result_entry = entry
        self.accept()

    def _pick_manual(self) -> None:
        self.result_manual = True
        self.accept()
