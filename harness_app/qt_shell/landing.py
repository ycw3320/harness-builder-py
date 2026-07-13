"""첫 진입 소개 화면(LandingPage) — 하네스 엔지니어링 정의·가치 + [시작하기]."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .widgets import brand_pixmap, make_btn


class LandingPage(QWidget):
    """첫 진입 소개 화면 — 하네스 엔지니어링이 뭔지·왜 만들었는지 + [시작하기].

    PM6 측정의 잔여 약점('우측을 안 보면 정의를 놓침=경로 의존')을 보완 — 누구나 진입 전에
    정의·가치를 본다. 스타일은 전부 QSS objectName(인라인 색 금지)이라 테마 토글이 자동 반영된다.
    """

    def __init__(self, on_start, on_quick=None) -> None:
        super().__init__()
        self._on_quick = on_quick  # PM8: '30초 빠른 시작' 콜백(None 이면 버튼 숨김)
        self.setObjectName("landing")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        wrap = QHBoxLayout(body)
        wrap.addStretch(1)
        col = QVBoxLayout()
        col.setSpacing(12)
        col.setContentsMargins(0, 56, 0, 56)
        colw = QWidget()
        colw.setLayout(col)
        colw.setMaximumWidth(640)
        colw.setMinimumWidth(480)
        wrap.addWidget(colw)
        wrap.addStretch(1)

        # 히어로: 브랜드 마크 + 워드마크 — 마크(안전벨트 채움 기호)가 이름의 유래를 시각으로 설명
        hero_row = QHBoxLayout()
        hero_row.setSpacing(12)
        mark = QLabel()
        mark.setPixmap(brand_pixmap(40))
        mark.setFixedSize(40, 40)
        hero_row.addWidget(mark)
        hero = QLabel("버클")
        hero.setObjectName("heroTitle")
        hero_row.addWidget(hero)
        hero_row.addStretch(1)
        hero_w = QWidget()
        hero_w.setLayout(hero_row)
        col.addWidget(hero_w)
        tag = QLabel(
            "Claude Code 하네스 빌더 · AI 코딩 도구에게 '안전벨트'를 채우는 가장 쉬운 방법"
        )
        tag.setObjectName("tagline")
        tag.setWordWrap(True)
        col.addWidget(tag)
        col.addSpacing(10)

        col.addWidget(self._h2("하네스 엔지니어링이란?"))
        col.addWidget(
            self._body(
                "Claude Code 같은 AI 코딩 도구가 내 프로젝트 규칙대로 안전하게 움직이도록, 미리 "
                "규칙·권한·차단을 정해두는 설정(.claude/ 폴더 + CLAUDE.md)을 짜는 일입니다. 빠른 "
                "말에게 채우는 안전벨트처럼 — 평소엔 자유롭게 일하되, 위험한 방향(.env 유출·강제 "
                "push 등)으로는 못 가게 잡아줍니다."
            )
        )
        col.addSpacing(4)
        col.addWidget(self._h2("왜 만들었나요?"))
        col.addWidget(
            self._body(
                "AI 코딩 도구는 강력하지만, 시키지 않은 위험한 행동(비밀키 파일 수정, 되돌릴 수 없는 "
                "명령 실행)을 할 수 있습니다. 하네스는 그걸 미리 막아주지만 설정 문법이 어려워 초심자는 "
                "손대기 힘들었습니다. 이 앱은 그 설정을 클릭만으로 시각으로 조립하고, 실행 전에 '규칙이 "
                "있을 때와 없을 때'를 시뮬레이션으로 직접 보여줍니다 — 외부 AI 호출 없이(LLM 0회), 오프라인에서."
            )
        )
        col.addSpacing(12)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        for title, desc in (
            (
                "실행 전 시뮬레이터",
                "'하네스 없으면 ↔ 지금'을 나란히 비교. 규칙을 껐다 켜며 효과를 직접 확인합니다.",
            ),
            (
                "6영역 시각 조립",
                "컨텍스트·권한·가드레일 등 6개 영역을 클릭으로 채웁니다. 어려운 용어엔 풀이가 붙어 있어요.",
            ),
            (
                "폴더로 즉시 생성",
                ".claude/ 폴더로 내보내, 그 폴더에서 Claude Code를 실행하면 바로 적용됩니다.",
            ),
        ):
            cards.addWidget(self._value_card(title, desc))
        cards_w = QWidget()
        cards_w.setLayout(cards)
        col.addWidget(cards_w)
        col.addSpacing(18)

        btnrow = QHBoxLayout()
        # PM8: 초심자 1순위 경로 = 최소 입력(질문 3개). 직접 조립은 보조 경로로 병행.
        if on_quick is not None:
            quick = make_btn(
                "30초 빠른 시작  →",
                "startBtn",
                on_quick,
                tip="질문 3개(폴더·성향·보호)만 답하면 검증된 하네스가 완성됩니다",
            )
            btnrow.addWidget(quick)
            start = make_btn("직접 조립하며 둘러보기", "addBtn", on_start)
            btnrow.addWidget(start)
        else:
            start = make_btn("시작하기  →", "startBtn", on_start)
            btnrow.addWidget(start)
        btnrow.addStretch(1)
        brw = QWidget()
        brw.setLayout(btnrow)
        col.addWidget(brw)
        col.addStretch(1)

        scroll.setWidget(body)
        outer.addWidget(scroll)

    def _h2(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("landingH2")
        return lbl

    def _body(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("landingBody")
        lbl.setWordWrap(True)
        return lbl

    def _value_card(self, title: str, desc: str) -> QWidget:
        card = QFrame()
        card.setObjectName("valueCard")
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 11, 12, 11)
        v.setSpacing(4)
        t = QLabel(title)
        t.setObjectName("valueTitle")
        t.setWordWrap(True)
        v.addWidget(t)
        d = QLabel(desc)
        d.setObjectName("valueDesc")
        d.setWordWrap(True)
        v.addWidget(d)
        return card
