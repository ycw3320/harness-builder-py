"""qt_shell 공용 위젯 — 행 카드(RowWidget)·소형 편집기(List/Dict)·토글·버튼 헬퍼.

편집(콘텐츠 patch)은 RowWidget 이 헤더를 in-place 갱신(재빌드 없이) — 편집 포커스 보존 설계.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from .. import view_model as vm
from ..state import BuilderState
from .theme import _INV_KEY, _rgba

_FIELD_H = {"textarea": 120, "list": 104, "dict": 104}  # 펼침 높이 추정용(위젯별)
_TITLE_FIELD = {  # AI 생성 후 제목으로 쓸 대표 필드
    "prose-guideline": "heading",
    "permission-rule": "pattern",
    "mcp-server": "server_name",
    "hook": "script_name",
    "policy-doc": "doc_name",
    "sub-agent": "name",
}


def brand_pixmap(size: int) -> QPixmap:
    """버클 브랜드 마크 — 안전벨트 버클 클래스프(클립이 꽂힌 본체 + 빨간 해제 버튼).

    제품명('버클')과 앱의 핵심 비유(안전벨트)를 시각으로 직결(사용자 확정안 A).
    단일 소스: 창/트레이 아이콘(app), 랜딩 히어로, exe .ico 생성(packaging/gen_icon.py)이
    전부 이 함수를 쓴다. 크기별 재드로잉으로 어느 해상도에서도 선명(비트맵 축소 금지).
    트레이·탐색기 배경(밝음/어두움)과 무관하게 식별되도록 테마 무관 고정색.
    """
    k = size / 32.0
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    # 본체
    p.setBrush(QColor("#0A6FD6"))
    p.drawRoundedRect(QRectF(5 * k, 11 * k, 22 * k, 20 * k), 6 * k, 6 * k)
    # 슬롯(흰 홈) — 클립이 꽂히는 자리
    p.setBrush(QColor("#FFFFFF"))
    p.drawRoundedRect(QRectF(10.5 * k, 13 * k, 11 * k, 4.5 * k), 2 * k, 2 * k)
    # 클립(텅) — 슬롯 안으로 삽입(흰 테가 양옆·아래로 남아 '꽂힘'이 읽힘)
    p.setBrush(QColor("#0A6FD6"))
    p.drawRoundedRect(QRectF(12.5 * k, 1.5 * k, 7 * k, 14 * k), 2.5 * k, 2.5 * k)
    # 빨간 해제 버튼(PRESS) — 소형에서도 식별점
    p.setBrush(QColor("#E5484D"))
    p.drawEllipse(QRectF(12.5 * k, 20.5 * k, 7 * k, 7 * k))
    p.end()
    return pm


def help_chip(tip: str) -> QLabel:
    """'?' 도움말 칩 — 올리면 풀이 툴팁, 클릭하면 즉시 풀이 표시.

    기존 텍스트 '(?)' 접미는 '값이 미정'처럼 읽혀 오해를 낳았음(사용자 피드백) —
    칩 모양+클릭 지원으로 '도움말' 어포던스를 명확히 한다.
    """
    chip = ClickableLabel("?", lambda: QToolTip.showText(QCursor.pos(), tip))
    chip.setObjectName("helpChip")
    chip.setToolTip(tip)
    return chip


def make_btn(label: str, object_name: str, on_click, tip: str = "") -> QPushButton:
    """버튼 5줄 보일러플레이트 축약 — objectName·커서·툴팁·클릭을 한 번에."""
    b = QPushButton(label)
    b.setObjectName(object_name)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if tip:
        b.setToolTip(tip)
    b.clicked.connect(on_click)
    return b


def _dot(color: str, size: int = 10) -> QLabel:
    d = QLabel()
    d.setFixedSize(size, size)
    d.setStyleSheet(f"background: {color}; border-radius: {size // 2}px;")
    return d


class ClickableLabel(QLabel):
    """클릭 가능한 라벨 — 시뮬레이터 차단 줄 → 원인 항목 점프용.

    PySide6 에서 인스턴스 속성으로 mousePressEvent 를 덮어쓰면 가상함수 디스패치가
    누락되므로, 서브클래스로 안전하게 오버라이드한다.
    """

    def __init__(self, text: str, on_click) -> None:
        super().__init__(text)
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, _ev) -> None:  # noqa: N802 (Qt 가상함수명)
        self._on_click()


class RuleToggle(QWidget):
    """테마 일치 규칙 on/off 토글 — QSS 체크 이미지가 렌더 안 되는 문제를 피해 QPainter 로 직접 그림.

    체크: 옅은 틴트(selected_bg) + accent 테두리·체크표시(진한 파란 채움 회피로 크림 톤과 조화).
    행 어디를 눌러도 토글된다.
    """

    def __init__(self, title: str, checked: bool, tokens: dict, on_toggle) -> None:
        super().__init__()
        self._checked = checked
        self._t = tokens
        self._on_toggle = on_toggle
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 3, 0, 3)
        h.setSpacing(9)
        self._ind = QLabel()
        self._ind.setFixedSize(18, 18)
        h.addWidget(self._ind)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {tokens['text']}; font-size: 13px;")
        lbl.setWordWrap(True)
        h.addWidget(lbl, 1)
        self._render_indicator()

    def _render_indicator(self) -> None:
        t = self._t
        pm = QPixmap(18, 18)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1, 1, 16, 16)
        if self._checked:
            p.setBrush(QColor(t["selected_bg"]))
            p.setPen(QPen(QColor(t["accent"]), 1.4))
        else:
            p.setBrush(QColor(t["surface"]))
            p.setPen(QPen(QColor(t["border"]), 1.2))
        p.drawRoundedRect(rect, 5, 5)
        if self._checked:
            pen = QPen(QColor(t["accent"]), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            path = QPainterPath()
            path.moveTo(5, 9.2)
            path.lineTo(8, 12.2)
            path.lineTo(13, 5.8)
            p.drawPath(path)
        p.end()
        self._ind.setPixmap(pm)

    def mousePressEvent(self, _ev) -> None:  # noqa: N802 (Qt 가상함수명)
        self._checked = not self._checked
        self._render_indicator()
        self._on_toggle(self._checked)


class ListEditor(QWidget):
    """문자열 리스트 편집(인자·도구) — 변경 시 on_change(list) 콜백. 초기 로드 중엔 미통지."""

    def __init__(self, values: list, on_change) -> None:
        super().__init__()
        self._on_change = on_change
        self._loading = True
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        self._rows_box = QVBoxLayout()
        self._rows_box.setContentsMargins(0, 0, 0, 0)
        self._rows_box.setSpacing(4)
        outer.addLayout(self._rows_box)
        self._edits: list[QLineEdit] = []
        for v in values or []:
            self._add_row(str(v))
        add = make_btn("+ 항목 추가", "addBtn", lambda: self._add_row(""))
        outer.addWidget(add)
        self._loading = False

    def _add_row(self, value: str) -> None:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        le = QLineEdit(value)
        le.textChanged.connect(self._emit)
        rm = make_btn("삭제", "crudBtn", lambda: self._remove(row, le))
        h.addWidget(le)
        h.addWidget(rm)
        self._edits.append(le)
        self._rows_box.addWidget(row)
        self._emit()

    def _remove(self, row: QWidget, le: QLineEdit) -> None:
        if le in self._edits:
            self._edits.remove(le)
        row.setParent(None)
        row.deleteLater()
        self._emit()

    def _emit(self) -> None:
        if not self._loading:
            self._on_change([e.text() for e in self._edits if e.text().strip()])


class DictEditor(QWidget):
    """문자열 dict 편집(env) — 변경 시 on_change(dict) 콜백. 초기 로드 중엔 미통지."""

    def __init__(self, values: dict, on_change) -> None:
        super().__init__()
        self._on_change = on_change
        self._loading = True
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        self._rows_box = QVBoxLayout()
        self._rows_box.setContentsMargins(0, 0, 0, 0)
        self._rows_box.setSpacing(4)
        outer.addLayout(self._rows_box)
        self._pairs: list[tuple[QLineEdit, QLineEdit]] = []
        for k, val in (values or {}).items():
            self._add_row(str(k), str(val))
        add = make_btn("+ 변수 추가", "addBtn", lambda: self._add_row("", ""))
        outer.addWidget(add)
        self._loading = False

    def _add_row(self, key: str, val: str) -> None:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        k_le = QLineEdit(key)
        k_le.setPlaceholderText("KEY")
        v_le = QLineEdit(val)
        v_le.setPlaceholderText("${VAR}")
        k_le.textChanged.connect(self._emit)
        v_le.textChanged.connect(self._emit)
        rm = make_btn("삭제", "crudBtn", lambda: self._remove(row, (k_le, v_le)))
        h.addWidget(k_le)
        h.addWidget(v_le)
        h.addWidget(rm)
        self._pairs.append((k_le, v_le))
        self._rows_box.addWidget(row)
        self._emit()

    def _remove(self, row: QWidget, pair: tuple) -> None:
        if pair in self._pairs:
            self._pairs.remove(pair)
        row.setParent(None)
        row.deleteLater()
        self._emit()

    def _emit(self) -> None:
        if self._loading:
            return
        d: dict[str, str] = {}
        for k_le, v_le in self._pairs:
            k = k_le.text().strip()
            if k:
                d[k] = v_le.text()
        self._on_change(d)


class RowWidget(QFrame):
    """컴팩트 행 — 클릭 시 펼쳐 kind별 폼 편집(field_specs 구동). 접힘 시 편집부 숨김."""

    HEADER_H = 34
    COLLAPSED = 44

    def __init__(
        self,
        row: vm.RowVM,
        state: BuilderState,
        tokens: dict,
        is_dark: bool,
        llm_fill=None,
        promote_fn=None,
        is_example: bool = False,
        on_example_edit=None,
        on_duplicate=None,
    ) -> None:
        super().__init__()
        self.setObjectName("rowCard")
        self._row = row
        self._state = state
        self._tokens = tokens  # involvement/제목 in-place 갱신용(재빌드 없이 헤더만 갱신)
        self._is_dark = is_dark
        self._llm_fill = llm_fill  # (kind, comp_id) 콜백 — 키 있을 때만 전달
        self._promote = promote_fn  # (comp_id) 콜백 — 강제수준 승격
        self._on_duplicate = on_duplicate  # (comp_id) — 예시 표식 승계를 위해 윈도 경유
        # PM6-S5: 프리셋이 넣어준 '예시' 표식 — 편집 시 in-place 로 숨겨 포커스 보존.
        self._is_example = is_example
        self._on_example_edit = on_example_edit
        self._example_tag: QLabel | None = None
        self._example_banner: QWidget | None = None
        self._open = False
        self.setMinimumHeight(self.COLLAPSED)
        self.setMaximumHeight(self.COLLAPSED)

        inv = tokens[_INV_KEY[row.involvement]]
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 5, 14, 5)
        outer.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._header_w = QWidget()
        self._header_w.setFixedHeight(self.HEADER_H)
        self._header_w.setLayout(header)
        self._dot_lbl = _dot(inv)
        header.addWidget(self._dot_lbl)
        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet(f"font-weight: 600; color: {tokens['text']};")
        self._update_title(row.title)  # 말줄임+툴팁(제목 편집 시 in-place 재갱신)
        header.addWidget(self._title_lbl)
        header.addStretch(1)
        self._pill = QLabel(row.involvement_label)
        self._pill.setStyleSheet(
            f"background: {_rgba(inv, 0.24 if is_dark else 0.14)}; color: {inv};"
            f"border-radius: 9px; padding: 1px 9px; font-size: 11px; font-weight: 600;"
        )
        header.addWidget(self._pill)
        # PM6: collapsed 헤더에서 kind(hook·policy-doc 등 개발 전문용어) 라벨 제거 —
        # 강제수준 배지(권고/문서/자동 차단)가 사용자 언어로 이미 종류를 구분하고, 헤더 폭도 확보.
        if row.enforcement:
            enf = QLabel(f"· {row.enforcement}")
            enf.setObjectName("faint")
            enf.setToolTip(
                f"종류: {row.kind} · 강제수준: 프로즈(권고) < 정책문서(문서) < hook(자동 차단)"
            )
            header.addWidget(enf)
        if is_example:
            self._example_tag = QLabel("예시")
            self._example_tag.setStyleSheet(
                f"background: {_rgba(tokens['warn'], 0.22 if is_dark else 0.14)};"
                f"color: {tokens['warn']}; border-radius: 8px; padding: 1px 8px; font-size: 11px;"
            )
            self._example_tag.setToolTip(
                "프리셋이 넣어준 예시 — 그대로 두면 함께 생성됩니다. 바꾸거나 지워도 됩니다."
            )
            header.addWidget(self._example_tag)
        for label, tip, fixed, fn in (
            ("↑", "위로", True, lambda: self._state.move(self._row.id, "up")),
            ("↓", "아래로", True, lambda: self._state.move(self._row.id, "down")),
            ("복제", "복제", False, lambda: self._do_duplicate()),
            ("삭제", "삭제", False, lambda: self._state.remove(self._row.id)),
        ):
            b = make_btn(label, "crudBtn", lambda _checked, f=fn: f(), tip)
            if fixed:
                b.setFixedSize(24, 24)
            header.addWidget(b)
        outer.addWidget(self._header_w)

        specs = vm.field_specs(row.kind)
        self._editor = self._build_editor(row, specs)
        self._editor.setVisible(False)
        outer.addWidget(self._editor)

        exp = self.HEADER_H + 100  # 제목 + 결정방식 + 여백
        for s in specs:
            exp += _FIELD_H.get(s.widget, 44)
        if row.guide:
            exp += 116
        self._expanded = min(740, exp)

        self._anim = QPropertyAnimation(self, b"maximumHeight")
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(self._on_anim_done)

    @property
    def row_id(self) -> str:
        """행의 컴포넌트 id(읽기 전용) — 외부(BuilderWindow)가 사적 _row 를 직접 읽던 경계 위반 해소."""
        return self._row.id

    # 편집 폼 구성 (값 설정 후 시그널 연결 → 초기 patch 폭주 방지) ---
    def _build_editor(self, row: vm.RowVM, specs: list) -> QWidget:
        editor = QWidget()
        ed = QVBoxLayout(editor)
        ed.setContentsMargins(0, 0, 0, 0)
        ed.setSpacing(6)

        if self._is_example:  # PM6-S5: 안심 배너 — 편집하면 _patch 에서 숨김
            self._example_banner = QLabel(
                "예시예요 — 그대로 두면 이 규칙이 함께 생성됩니다. 바꾸거나, 필요 없으면 삭제하세요."
            )
            self._example_banner.setObjectName("muted")
            self._example_banner.setWordWrap(True)
            ed.addWidget(self._example_banner)

        title_le = QLineEdit(row.title)
        title_le.setPlaceholderText("제목")
        # 제목은 _signature 미추적(타이핑마다 재빌드=포커스 파괴 방지) → 헤더 라벨을 in-place 갱신
        title_le.textChanged.connect(lambda t: (self._patch("title", t), self._update_title(t)))
        ed.addWidget(self._labeled("제목", title_le))

        inv_combo = QComboBox()
        inv_keys = []
        for lab, key in vm.INVOLVEMENT_OPTIONS:
            inv_combo.addItem(lab)
            inv_keys.append(key)
        inv_combo.setCurrentIndex(inv_keys.index(row.involvement))
        # 결정방식도 in-place(색점·pill) — 구조 재빌드로 라우팅하면 편집 중 행이 접혀버림
        inv_combo.currentIndexChanged.connect(
            lambda i: (
                self._patch("involvement", inv_keys[i]),
                self._update_involvement(inv_keys[i]),
            )
        )
        ed.addWidget(self._labeled("결정방식", inv_combo))

        for s in specs:
            ed.addWidget(
                self._labeled(s.label, self._field_widget(s, row.values.get(s.name)), s.tip)
            )

        if row.guide:
            ed.addWidget(self._guide_box(row.guide))
        return editor

    def _labeled(self, label: str, widget: QWidget, tip: str = "") -> QWidget:
        # PM6-S5: 2단 풀이 — 라벨은 쉬운 말, dev 설명은 '?' 칩(올리면/클릭하면 풀이).
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        lab = QLabel(label)
        lab.setObjectName("faint")
        if tip:
            head = QHBoxLayout()
            head.setContentsMargins(0, 0, 0, 0)
            head.setSpacing(5)
            head.addWidget(lab)
            head.addWidget(help_chip(tip))
            head.addStretch(1)
            hw = QWidget()
            hw.setLayout(head)
            v.addWidget(hw)
            widget.setToolTip(tip)  # 입력창 자체에 올려도 같은 풀이
        else:
            v.addWidget(lab)
        v.addWidget(widget)
        return box

    def _field_widget(self, spec, value) -> QWidget:
        name = spec.name
        if spec.widget == "textarea":
            te = QPlainTextEdit(value or "")
            te.setPlaceholderText(spec.placeholder)
            te.setMinimumHeight(84)
            te.textChanged.connect(lambda: self._patch(name, te.toPlainText()))
            return te
        if spec.widget == "combo":
            # PM6-S5: 표시는 한글 라벨, patch 는 원시 값(itemData) — 표시/값 분리.
            cb = QComboBox()
            labels = spec.option_labels or spec.options
            for raw, lab in zip(spec.options, labels, strict=False):
                cb.addItem(lab, raw)
            if value in spec.options:
                cb.setCurrentIndex(list(spec.options).index(value))
            cb.currentIndexChanged.connect(lambda i, c=cb: self._patch(name, c.itemData(i)))
            return cb
        if spec.widget == "list":
            return ListEditor(value or [], lambda v: self._patch(name, v))
        if spec.widget == "dict":
            return DictEditor(value or {}, lambda v: self._patch(name, v))
        le = QLineEdit("" if value is None else str(value))
        le.setPlaceholderText(spec.placeholder)
        if (
            name == "matcher_tool"
        ):  # 자유 입력 regex — 잘못된 패턴은 시각 경고(시뮬은 '평가 불가'로 강등됨)
            self._apply_matcher_style(le, le.text(), spec.tip)  # 초기값도 검증(재빌드 후 경고 유지)
            le.textChanged.connect(
                lambda t, w=le, tip=spec.tip: self._patch_matcher(name, t, w, tip)
            )
        else:
            le.textChanged.connect(lambda t: self._patch(name, t))
        return le

    @staticmethod
    def _apply_matcher_style(widget: QLineEdit, text: str, tip: str) -> None:
        try:
            re.compile(text)
            widget.setStyleSheet("")  # QSS 복원
            widget.setToolTip(tip)  # 2단 풀이 툴팁 복원(빈 문자열로 소거 금지)
        except re.error as e:
            widget.setStyleSheet("border: 1px solid #C9362B;")
            widget.setToolTip(f"패턴 오류: {e} — 예: Write|Edit ( | 은 '또는')")

    def _patch_matcher(self, name: str, text: str, widget: QLineEdit, tip: str) -> None:
        self._apply_matcher_style(widget, text, tip)
        self._patch(name, text)  # 상태는 항상 반영(시뮬이 '평가 불가'로 정직하게 표시)

    def _guide_box(self, guide: dict) -> QWidget:
        box = QFrame()
        box.setObjectName("guideBox")
        v = QVBoxLayout(box)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)
        purpose = QLabel(f"무엇 · {guide['purpose']}")
        purpose.setObjectName("muted")
        purpose.setWordWrap(True)
        v.addWidget(purpose)
        head = QHBoxLayout()
        lab = QLabel("외부 LLM에 이렇게 요청")
        lab.setObjectName("section")
        head.addWidget(lab)
        head.addStretch(1)
        if self._llm_fill is not None:
            ai = make_btn(
                "AI로 채우기", "primaryBtn", lambda: self._llm_fill(self._row.kind, self._row.id)
            )
            head.addWidget(ai)
        if self._promote is not None and self._row.promotable:
            up = make_btn(
                "강제수준 ↑",
                "addBtn",
                lambda: self._promote(self._row.id),
                tip="같은 의도를 더 강하게 집행(프로즈→정책문서→hook)",
            )
            head.addWidget(up)
        copy = make_btn(
            "프롬프트 복사", "addBtn", lambda: QApplication.clipboard().setText(guide["ask"])
        )
        head.addWidget(copy)
        head_w = QWidget()
        head_w.setLayout(head)
        v.addWidget(head_w)
        ask = QLabel(guide["ask"])
        ask.setObjectName("faint")
        ask.setWordWrap(True)
        v.addWidget(ask)
        return box

    def _update_title(self, text: str) -> None:
        """헤더 제목 라벨 in-place 갱신(말줄임+툴팁) — 중앙 재빌드 없이 제목 편집 즉시 반영."""
        fm = self._title_lbl.fontMetrics()
        self._title_lbl.setText(fm.elidedText(text, Qt.TextElideMode.ElideRight, 240))
        self._title_lbl.setToolTip(text if text else "")

    def _update_involvement(self, key: str) -> None:
        """헤더 색점·pill in-place 갱신 — involvement 변경이 행을 파괴(접힘)하지 않게."""
        inv = self._tokens[_INV_KEY[key]]
        self._dot_lbl.setStyleSheet(f"background: {inv}; border-radius: 5px;")
        label = next((lab for lab, k in vm.INVOLVEMENT_OPTIONS if k == key), key)
        self._pill.setText(label)
        self._pill.setStyleSheet(
            f"background: {_rgba(inv, 0.24 if self._is_dark else 0.14)}; color: {inv};"
            f"border-radius: 9px; padding: 1px 9px; font-size: 11px; font-weight: 600;"
        )

    def _do_duplicate(self) -> None:
        """복제 — 예시 표식 승계가 필요하므로 윈도 콜백 경유(없으면 직접)."""
        if self._on_duplicate is not None:
            self._on_duplicate(self._row.id)
        else:
            self._state.duplicate(self._row.id)

    def _patch(self, name: str, value) -> None:
        if self._is_example:  # 첫 편집 = 더 이상 '예시' 아님 — 표식 in-place 숨김(포커스 보존)
            self._is_example = False
            if self._example_tag is not None:
                self._example_tag.setVisible(False)
            if self._example_banner is not None:
                self._example_banner.setVisible(False)
            if self._on_example_edit is not None:
                self._on_example_edit(self._row.id)
        self._state.patch(self._row.id, {name: value})

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt 시그니처)
        if self._header_w.geometry().contains(event.position().toPoint()):
            self.toggle()
        super().mousePressEvent(event)

    def set_open(self, value: bool) -> None:
        self._open = value
        if value:
            self._editor.setVisible(True)
        self._anim.stop()
        self._anim.setStartValue(self.maximumHeight())
        self._anim.setEndValue(self._expanded if value else self.COLLAPSED)
        self._anim.start()

    def _on_anim_done(self) -> None:
        if not self._open:
            self._editor.setVisible(False)

    def toggle(self) -> None:
        self.set_open(not self._open)
