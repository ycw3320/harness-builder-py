"""Qt 3-pane 셸 (S1~S6) — Apple 미니멀 테마(라이트 크림 ↔ 다크 Space Gray) 토글.

공유 state·view_model 소비, 위젯 배선만 Qt 고유. 테마 토큰은 LIGHT/DARK dict 단일 소스에서
build_qss 로 주입, 토글은 QApplication 스타일시트 런타임 스왑(재시작 불필요·QSettings persist).
편집(콘텐츠 patch)은 우패널만 갱신, 구조 변경 시에만 중앙/좌측 재빌드(편집 포커스 보존).
"""

from __future__ import annotations

import os
from pathlib import Path
from string import Template

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSettings, Qt
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from harness_core.export.assemble_project import assemble_project
from harness_core.ir.registry import addable_kinds_by_layer, kind_registry
from harness_fs.policy import MergeStrategy
from harness_fs.writer import write_tree
from harness_llm import credentials
from harness_llm.client import DEFAULT_MODEL, MODELS, AnthropicClient, LLMError, anthropic_available

from .. import view_model as vm
from ..guides import layer_order
from ..state import BuilderState

# ── 테마 토큰 (Apple 미니멀 — 워크플로 'Graphite Crème' 합성, WCAG AA 검증) ──
LIGHT = {
    "bg": "#FBFBF9",
    "surface": "#FFFFFF",
    "surface_alt": "#F4F4F1",
    "border": "#D9D9D2",
    "divider": "#ECECE8",
    "text": "#1D1D1F",
    "text_muted": "#6E6E73",
    "text_faint": "#8E8E93",
    "accent": "#0A6FD6",
    "accent_hover": "#085BB5",
    "on_accent": "#FFFFFF",
    "selected_bg": "#E4EFFB",
    "danger": "#C9362B",
    "warn": "#B26A00",
    "ok": "#177C3D",
    "involvement_auto": "#177C3D",
    "involvement_assisted": "#0A6FD6",
    "involvement_manual": "#AD5A08",
}
DARK = {
    "bg": "#1C1C1E",
    "surface": "#2C2C2E",
    "surface_alt": "#3A3A3C",
    "border": "#3A3A3C",
    "divider": "#48484A",
    "text": "#ECECEE",
    "text_muted": "#A0A0A6",
    "text_faint": "#8D8D93",
    "accent": "#0A84FF",
    "accent_hover": "#409CFF",
    "on_accent": "#FFFFFF",
    "selected_bg": "#0A3A66",
    "danger": "#FF6961",
    "warn": "#FFB340",
    "ok": "#30D158",
    "involvement_auto": "#30D158",
    "involvement_assisted": "#5AA9FF",
    "involvement_manual": "#FF9F0A",
}
THEMES = {"light": LIGHT, "dark": DARK}

FONT_STACK = (
    '-apple-system, "SF Pro Text", "Helvetica Neue", "Apple SD Gothic Neo", '
    '"Pretendard", "Malgun Gothic", "맑은 고딕", "Segoe UI", sans-serif'
)

_INV_KEY = {
    "auto": "involvement_auto",
    "assisted": "involvement_assisted",
    "manual-gate": "involvement_manual",
}

_QSS = Template("""
* { font-family: $font; color: $text; font-size: 13px; }
QMainWindow, QWidget#centerPane { background: $bg; }
QWidget#leftPane, QWidget#rightPane { background: $surface_alt; }
QSplitter::handle { background: $divider; width: 1px; }

QLabel#h1 { font-size: 15px; font-weight: 600; color: $text; }
QLabel#muted { color: $text_muted; font-size: 12px; }
QLabel#faint { color: $text_faint; font-size: 12px; }
QLabel#section { font-size: 11px; font-weight: 600; color: $text_muted; }
QLabel#lintErr { color: $danger; font-size: 12px; }
QLabel#lintWarn { color: $warn; font-size: 12px; }

QFrame#introCard, QFrame#rowCard { background: $surface; border: 1px solid $border; border-radius: 10px; }

QLineEdit, QPlainTextEdit {
    background: $surface_alt; border: 1px solid $border; border-radius: 7px;
    padding: 6px 8px; color: $text; selection-background-color: $accent;
    selection-color: $on_accent;
}
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid $accent; }

QComboBox {
    background: $surface; border: 1px solid $border; border-radius: 7px;
    padding: 5px 10px; color: $text;
}
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background: $surface; color: $text; border: 1px solid $border;
    selection-background-color: $selected_bg; selection-color: $text; outline: none;
}

QPushButton#primaryBtn {
    background-color: $accent; color: $on_accent; border: 1px solid $accent;
    border-radius: 8px; padding: 10px 16px; font-weight: 600; font-size: 13px;
}
QPushButton#primaryBtn:hover { background-color: $accent_hover; border-color: $accent_hover; }
QPushButton#primaryBtn:pressed { background-color: $accent_hover; }

QWidget#segTrack { background: $surface_alt; border: 1px solid $border; border-radius: 8px; }
QPushButton#segBtn {
    background: transparent; color: $text_muted; border: none; border-radius: 6px;
    padding: 4px 12px; font-size: 12px; font-weight: 600;
}
QPushButton#segBtn:checked { background: $surface; color: $text; }

QPushButton#crudBtn {
    background: transparent; color: $text_muted; border: none;
    border-radius: 5px; padding: 2px 7px; font-size: 12px;
}
QPushButton#crudBtn:hover { background: $surface_alt; color: $text; }
QPushButton#addBtn {
    background: $surface_alt; color: $text; border: 1px solid $border;
    border-radius: 7px; padding: 6px 12px; font-size: 12px; font-weight: 600;
}
QPushButton#addBtn:hover { border: 1px solid $accent; color: $accent; }

QFrame#guideBox { background: $surface_alt; border: 1px solid $border; border-radius: 8px; }

QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { margin: 2px 4px; border-radius: 8px; }
QListWidget::item:selected { background: $selected_bg; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $text_faint; border-radius: 4px; min-height: 26px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
""")


def build_qss(tokens: dict) -> str:
    return _QSS.substitute(font=FONT_STACK, **tokens)


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


_FIELD_H = {"textarea": 120, "list": 104, "dict": 104}  # 펼침 높이 추정용(위젯별)
_TITLE_FIELD = {  # AI 생성 후 제목으로 쓸 대표 필드
    "prose-guideline": "heading",
    "permission-rule": "pattern",
    "mcp-server": "server_name",
    "hook": "script_name",
    "policy-doc": "doc_name",
    "sub-agent": "name",
}


def _dot(color: str, size: int = 10) -> QLabel:
    d = QLabel()
    d.setFixedSize(size, size)
    d.setStyleSheet(f"background: {color}; border-radius: {size // 2}px;")
    return d


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
        add = QPushButton("+ 항목 추가")
        add.setObjectName("addBtn")
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.clicked.connect(lambda: self._add_row(""))
        outer.addWidget(add)
        self._loading = False

    def _add_row(self, value: str) -> None:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        le = QLineEdit(value)
        le.textChanged.connect(self._emit)
        rm = QPushButton("삭제")
        rm.setObjectName("crudBtn")
        rm.clicked.connect(lambda: self._remove(row, le))
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
        add = QPushButton("+ 변수 추가")
        add.setObjectName("addBtn")
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.clicked.connect(lambda: self._add_row("", ""))
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
        rm = QPushButton("삭제")
        rm.setObjectName("crudBtn")
        rm.clicked.connect(lambda: self._remove(row, (k_le, v_le)))
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
        self, row: vm.RowVM, state: BuilderState, tokens: dict, is_dark: bool, llm_fill=None
    ) -> None:
        super().__init__()
        self.setObjectName("rowCard")
        self._row = row
        self._state = state
        self._llm_fill = llm_fill  # (kind, comp_id) 콜백 — 키 있을 때만 전달
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
        header.addWidget(_dot(inv))
        title = QLabel(row.title)
        title.setStyleSheet(f"font-weight: 600; color: {tokens['text']};")
        header.addWidget(title)
        header.addStretch(1)
        pill = QLabel(row.involvement_label)
        pill.setStyleSheet(
            f"background: {_rgba(inv, 0.24 if is_dark else 0.14)}; color: {inv};"
            f"border-radius: 9px; padding: 1px 9px; font-size: 11px; font-weight: 600;"
        )
        header.addWidget(pill)
        kind_lbl = QLabel(row.kind)
        kind_lbl.setObjectName("faint")
        header.addWidget(kind_lbl)
        for label, tip, fixed, fn in (
            ("↑", "위로", True, lambda: self._state.move(self._row.id, "up")),
            ("↓", "아래로", True, lambda: self._state.move(self._row.id, "down")),
            ("복제", "복제", False, lambda: self._state.duplicate(self._row.id)),
            ("삭제", "삭제", False, lambda: self._state.remove(self._row.id)),
        ):
            b = QPushButton(label)
            b.setObjectName("crudBtn")
            if fixed:
                b.setFixedSize(24, 24)
            b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked, f=fn: f())
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

    # 편집 폼 구성 (값 설정 후 시그널 연결 → 초기 patch 폭주 방지) ---
    def _build_editor(self, row: vm.RowVM, specs: list) -> QWidget:
        editor = QWidget()
        ed = QVBoxLayout(editor)
        ed.setContentsMargins(0, 0, 0, 0)
        ed.setSpacing(6)

        title_le = QLineEdit(row.title)
        title_le.setPlaceholderText("제목")
        title_le.textChanged.connect(lambda t: self._patch("title", t))
        ed.addWidget(self._labeled("제목", title_le))

        inv_combo = QComboBox()
        inv_keys = []
        for lab, key in vm.INVOLVEMENT_OPTIONS:
            inv_combo.addItem(lab)
            inv_keys.append(key)
        inv_combo.setCurrentIndex(inv_keys.index(row.involvement))
        inv_combo.currentIndexChanged.connect(lambda i: self._patch("involvement", inv_keys[i]))
        ed.addWidget(self._labeled("결정방식", inv_combo))

        for s in specs:
            ed.addWidget(self._labeled(s.label, self._field_widget(s, row.values.get(s.name))))

        if row.guide:
            ed.addWidget(self._guide_box(row.guide))
        return editor

    def _labeled(self, label: str, widget: QWidget) -> QWidget:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        lab = QLabel(label)
        lab.setObjectName("faint")
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
            cb = QComboBox()
            cb.addItems(list(spec.options))
            if value in spec.options:
                cb.setCurrentText(value)
            cb.currentTextChanged.connect(lambda t: self._patch(name, t))
            return cb
        if spec.widget == "list":
            return ListEditor(value or [], lambda v: self._patch(name, v))
        if spec.widget == "dict":
            return DictEditor(value or {}, lambda v: self._patch(name, v))
        le = QLineEdit("" if value is None else str(value))
        le.setPlaceholderText(spec.placeholder)
        le.textChanged.connect(lambda t: self._patch(name, t))
        return le

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
            ai = QPushButton("AI로 채우기")
            ai.setObjectName("primaryBtn")
            ai.setCursor(Qt.CursorShape.PointingHandCursor)
            ai.clicked.connect(lambda: self._llm_fill(self._row.kind, self._row.id))
            head.addWidget(ai)
        copy = QPushButton("프롬프트 복사")
        copy.setObjectName("addBtn")
        copy.setCursor(Qt.CursorShape.PointingHandCursor)
        copy.clicked.connect(lambda: QApplication.clipboard().setText(guide["ask"]))
        head.addWidget(copy)
        head_w = QWidget()
        head_w.setLayout(head)
        v.addWidget(head_w)
        ask = QLabel(guide["ask"])
        ask.setObjectName("faint")
        ask.setWordWrap(True)
        v.addWidget(ask)
        return box

    def _patch(self, name: str, value) -> None:
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


class BuilderWindow(QMainWindow):
    def __init__(self, state: BuilderState | None = None) -> None:
        super().__init__()
        self.state = state or BuilderState("my-project", preset="minimal")
        self._settings = QSettings("harness-builder", "qt-shell")
        self.theme_name = os.environ.get("HB_THEME") or self._settings.value("theme", "light")
        if self.theme_name not in THEMES:
            self.theme_name = "light"
        self.setWindowTitle("하네스 빌더 — 실행 전 시뮬레이터형")
        self.resize(1180, 720)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._left_host = self._host("leftPane")
        self._center_host = self._host("centerPane")
        self._right_host = self._host("rightPane")
        for h in (self._left_host, self._center_host, self._right_host):
            splitter.addWidget(h)
        splitter.setSizes([240, 560, 380])
        splitter.setCollapsible(0, False)
        self.setCentralWidget(splitter)

        self._sig: tuple | None = None
        self.state.subscribe(self._on_change)
        self._apply_theme()

    # 테마 ---
    @property
    def tokens(self) -> dict:
        return THEMES[self.theme_name]

    @property
    def is_dark(self) -> bool:
        return self.theme_name == "dark"

    def _apply_theme(self) -> None:
        self._settings.setValue("theme", self.theme_name)
        self._force_rebuild()
        # 위젯 생성 후 스타일시트 적용 → 전 위젯 polish 보장(특히 버튼/콤보 배경)
        QApplication.instance().setStyleSheet(build_qss(self.tokens))

    def set_theme(self, name: str) -> None:
        if name != self.theme_name and name in THEMES:
            self.theme_name = name
            self._apply_theme()

    # 호스트·재빌드 라우팅 ---
    def _host(self, name: str) -> QWidget:
        w = QWidget()
        w.setObjectName(name)
        QVBoxLayout(w).setContentsMargins(0, 0, 0, 0)
        return w

    def _signature(self) -> tuple:
        return (
            self.theme_name,
            self.state.selected_layer,
            self.state.advanced_mode,
            tuple((c.id, c.enabled, c.involvement) for c in self.state.ir.components),
        )

    def _on_change(self) -> None:
        """편집(콘텐츠)은 우패널만, 구조/계층/테마 변경 시에만 중앙·좌측 재빌드(포커스 보존)."""
        sig = self._signature()
        if sig != self._sig:
            self._sig = sig
            self._rebuild_left()
            self._rebuild_center()
        self._rebuild_right()

    def _force_rebuild(self) -> None:
        self._sig = self._signature()
        self._rebuild_left()
        self._rebuild_center()
        self._rebuild_right()

    def _clear(self, host: QWidget, margins: tuple[int, int, int, int]) -> QVBoxLayout:
        lay = host.layout()
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        inner = QWidget()
        lay.addWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(*margins)
        v.setSpacing(10)
        return v

    # 좌 nav (S2) ---
    def _rebuild_left(self) -> None:
        t = self.tokens
        v = self._clear(self._left_host, (16, 18, 16, 16))
        title = QLabel("구성 영역")
        title.setObjectName("h1")
        v.addWidget(title)
        hint = QLabel("6계층을 차례로 채우면 하네스가 완성됩니다.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        v.addWidget(hint)
        v.addWidget(self._preset_toggle())

        nav = QListWidget()
        nav.setSpacing(0)
        for item in vm.nav_items(self.state):
            li = QListWidgetItem(nav)
            cell = QWidget()
            row = QHBoxLayout(cell)
            row.setContentsMargins(10, 7, 10, 7)
            dot_color = t["ok"] if item.count else t["text_faint"]
            row.addWidget(_dot(dot_color))
            col = QVBoxLayout()
            col.setSpacing(1)
            name = QLabel(f"{item.label}  ({item.count})")
            name_color = t["text"] if item.interactive else t["text_faint"]
            name.setStyleSheet(f"font-weight: 600; color: {name_color};")
            col.addWidget(name)
            sub = QLabel(item.hint)
            sub.setObjectName("muted")
            col.addWidget(sub)
            row.addLayout(col)
            row.addStretch(1)
            li.setSizeHint(cell.sizeHint())
            nav.addItem(li)
            nav.setItemWidget(li, cell)
            if not item.interactive:
                li.setFlags(li.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            elif item.selected:
                li.setSelected(True)
        nav.itemClicked.connect(self._on_nav)
        self._nav = nav
        v.addWidget(nav, 1)

    def _on_nav(self, li: QListWidgetItem) -> None:
        self.state.set_selected_layer(layer_order[self._nav.row(li)])

    # 중앙 (S3/S4) ---
    def _rebuild_center(self) -> None:
        v = self._clear(self._center_host, (22, 20, 22, 20))
        intro = vm.layer_intro(self.state)
        card = QFrame()
        card.setObjectName("introCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        h = QLabel(vm.layer_meta_label(self.state))
        h.setObjectName("h1")
        cl.addWidget(h)
        what = QLabel(intro["what"])
        what.setWordWrap(True)
        cl.addWidget(what)
        mn = QLabel(f"최소 할 일 · {intro['minimum']}")
        mn.setObjectName("muted")
        mn.setWordWrap(True)
        cl.addWidget(mn)
        v.addWidget(card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        rows_lay = QVBoxLayout(holder)
        rows_lay.setContentsMargins(0, 0, 0, 0)
        rows_lay.setSpacing(10)
        fill = self._llm_fill_component if self._llm_ready() else None
        self._rows: list[RowWidget] = []
        for r in vm.rows_for_selected(self.state):
            rw = RowWidget(r, self.state, self.tokens, self.is_dark, fill)
            self._rows.append(rw)
            rows_lay.addWidget(rw)
        rows_lay.addStretch(1)
        scroll.setWidget(holder)
        v.addWidget(scroll, 1)
        v.addWidget(self._add_bar())

    def _preset_toggle(self) -> QWidget:
        track = QWidget()
        track.setObjectName("segTrack")
        lay = QHBoxLayout(track)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        group = QButtonGroup(track)
        group.setExclusive(True)
        for key, label in (("minimal", "빈 시작"), ("safety-first", "안전우선")):
            b = QPushButton(label)
            b.setObjectName("segBtn")
            b.setCheckable(True)
            b.setChecked(self.state._preset == key)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked, k=key: self.state.load_preset(k))
            group.addButton(b)
            lay.addWidget(b)
        return track

    def _add_bar(self) -> QWidget:
        """선택 계층의 추가 가능 kind 버튼 — 동적 추가(요구 1). 고급 토글로 advanced kind 노출."""
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        all_entries = addable_kinds_by_layer.get(self.state.selected_layer, [])
        entries = [e for e in all_entries if e["basic"] or self.state.advanced_mode]
        if entries:
            lbl = QLabel("추가:")
            lbl.setObjectName("muted")
            lay.addWidget(lbl)
        for entry in entries:
            kind = entry["kind"]
            b = QPushButton(f"+ {kind_registry[kind]['label']}")
            b.setObjectName("addBtn")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked, k=kind: self.state.add_component(k))
            lay.addWidget(b)
        lay.addStretch(1)
        if any(not e["basic"] for e in all_entries):
            adv = QPushButton("고급")
            adv.setObjectName("segBtn")
            adv.setCheckable(True)
            adv.setChecked(self.state.advanced_mode)
            adv.setCursor(Qt.CursorShape.PointingHandCursor)
            adv.clicked.connect(lambda: self.state.set_advanced_mode(not self.state.advanced_mode))
            lay.addWidget(adv)
        return bar

    # 우 패널 (S5/S6) + 테마 토글 ---
    def _rebuild_right(self) -> None:
        v = self._clear(self._right_host, (20, 18, 20, 18))

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        view_lbl = QLabel("보기")
        view_lbl.setObjectName("section")
        head.addWidget(view_lbl)
        head.addStretch(1)
        gear = QPushButton("LLM 설정")
        gear.setObjectName("addBtn")
        gear.setCursor(Qt.CursorShape.PointingHandCursor)
        gear.clicked.connect(self._open_settings)
        head.addWidget(gear)
        head.addWidget(self._theme_toggle())
        head_w = QWidget()
        head_w.setLayout(head)
        v.addWidget(head_w)

        v.addWidget(self._section("라이브 시뮬레이터 · LLM 0회"))
        for s in vm.sim_items(self.state):
            line = QLabel(f"•  {s.label}  →  {s.outcome}")
            line.setWordWrap(True)
            v.addWidget(line)

        v.addWidget(self._section("정합성 검사"))
        lints = vm.lint_items(self.state)
        if not lints:
            ok = QLabel("문제 없음 — 내보낼 준비 완료")
            ok.setObjectName("muted")
            v.addWidget(ok)
        for li in lints:
            lbl = QLabel(f"[{li.code}] {li.message}")
            lbl.setObjectName("lintErr" if li.level == "error" else "lintWarn")
            lbl.setWordWrap(True)
            v.addWidget(lbl)

        v.addWidget(self._section("산출 미리보기"))
        for p in vm.export_paths(self.state)[:8]:
            f = QLabel(p)
            f.setObjectName("faint")
            v.addWidget(f)

        v.addStretch(1)
        combo = QComboBox()
        combo.addItems(["minimal", "harness-only"])
        combo.setCurrentText(self.state.scaffold)
        combo.currentTextChanged.connect(self.state.set_scaffold)
        v.addWidget(combo)
        btn = QPushButton("폴더 선택 → 하네스 생성")
        btn.setObjectName("primaryBtn")
        btn.clicked.connect(self._on_export)
        v.addWidget(btn)

    def _theme_toggle(self) -> QWidget:
        track = QWidget()
        track.setObjectName("segTrack")
        lay = QHBoxLayout(track)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        group = QButtonGroup(track)
        group.setExclusive(True)
        for key, label in (("light", "라이트"), ("dark", "다크")):
            b = QPushButton(label)
            b.setObjectName("segBtn")
            b.setCheckable(True)
            b.setChecked(self.theme_name == key)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked, k=key: self.set_theme(k))
            group.addButton(b)
            lay.addWidget(b)
        return track

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setObjectName("section")
        return lbl

    def _on_export(self) -> None:
        dest = QFileDialog.getExistingDirectory(self, "하네스를 생성할 폴더 선택")
        if not dest:
            return
        tree = assemble_project(self.state.ir, self.state.scaffold)
        report = write_tree(tree, Path(dest), strategy=MergeStrategy.SKIP_EXISTING)
        QMessageBox.information(
            self,
            "생성 완료",
            f"생성 {len(report.created)}개 · 건너뜀 {len(report.skipped)}개\n{dest}",
        )

    # 인앱 LLM (BYO 키) — 키 있을 때만 활성, 없으면 §0.6 복사→붙여넣기 유지 (PM3-C) ---
    def _llm_ready(self) -> bool:
        return anthropic_available() and credentials.has_api_key("anthropic")

    def _llm_fill_component(self, kind: str, comp_id: str) -> None:
        intent, ok = QInputDialog.getMultiLineText(
            self, "AI로 채우기", f"무엇을 만들지 자연어로 적으세요 ({kind}):", ""
        )
        if not ok or not intent.strip():
            return
        key = credentials.get_api_key("anthropic")
        if not key:
            QMessageBox.information(
                self, "LLM 설정 필요", "먼저 'LLM 설정'에서 API 키를 입력하세요."
            )
            return
        model = self._settings.value("llm_model", DEFAULT_MODEL)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            data = AnthropicClient(key, model).generate(kind, intent.strip())
        except LLMError as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "LLM 오류", str(e))
            return
        QApplication.restoreOverrideCursor()
        patch = dict(data)
        tf = _TITLE_FIELD.get(kind)
        if tf and data.get(tf):
            patch["title"] = str(data[tf])[:60]
        patch["intent"] = {"raw": intent.strip(), "compiled_by": "llm", "confidence": 0.9}
        self.state.patch(comp_id, patch)
        self._force_rebuild()
        for rw in self._rows:
            if rw._row.id == comp_id:
                rw.set_open(True)
                break

    def _open_settings(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("LLM 설정")
        dlg.setMinimumWidth(460)
        v = QVBoxLayout(dlg)
        v.setSpacing(10)
        info = QLabel(
            "API 키를 입력하면 '외부 LLM에 이렇게 요청' 대신 앱에서 바로 생성합니다.\n"
            "주의: 입력한 의도가 선택한 LLM 제공자로 전송됩니다(오프라인 → 온라인 전환).\n"
            "키는 OS 자격증명관리자에 저장되며 코드·로그에 남지 않습니다."
        )
        info.setObjectName("muted")
        info.setWordWrap(True)
        v.addWidget(info)
        if not anthropic_available():
            warn = QLabel("anthropic 미설치 — pip install harness-builder[llm]")
            warn.setObjectName("lintWarn")
            warn.setWordWrap(True)
            v.addWidget(warn)
        v.addWidget(QLabel("모델"))
        model_cb = QComboBox()
        model_cb.addItems(MODELS)
        model_cb.setCurrentText(self._settings.value("llm_model", DEFAULT_MODEL))
        v.addWidget(model_cb)
        v.addWidget(QLabel("Anthropic API 키"))
        key_le = QLineEdit()
        key_le.setEchoMode(QLineEdit.EchoMode.Password)
        key_le.setPlaceholderText(
            "(저장됨 — 변경 시에만 입력)" if credentials.has_api_key("anthropic") else "sk-ant-..."
        )
        v.addWidget(key_le)
        btns = QHBoxLayout()
        delete = QPushButton("키 삭제")
        delete.setObjectName("addBtn")
        close = QPushButton("닫기")
        close.setObjectName("addBtn")
        save = QPushButton("저장")
        save.setObjectName("primaryBtn")
        btns.addWidget(delete)
        btns.addStretch(1)
        btns.addWidget(close)
        btns.addWidget(save)
        bw = QWidget()
        bw.setLayout(btns)
        v.addWidget(bw)

        def do_save() -> None:
            self._settings.setValue("llm_model", model_cb.currentText())
            k = key_le.text().strip()
            if k:
                try:
                    credentials.save_api_key("anthropic", k)
                except RuntimeError as e:
                    QMessageBox.warning(dlg, "저장 실패", str(e))
                    return
            dlg.accept()

        def do_delete() -> None:
            credentials.delete_api_key("anthropic")
            dlg.accept()

        save.clicked.connect(do_save)
        delete.clicked.connect(do_delete)
        close.clicked.connect(dlg.reject)
        dlg.exec()
        self._force_rebuild()  # 키 변경 반영(AI 버튼 활성/비활성)


def make_app():
    from PySide6.QtGui import QFont, QFontDatabase

    app = QApplication.instance() or QApplication([])
    # Fusion: 네이티브(windowsvista) 스타일은 QPushButton background-color 등 QSS를 무시 →
    # Fusion 으로 전환해 커스텀 테마 QSS 를 일관 적용(Apple풍 재디자인 기반).
    app.setStyle("Fusion")
    # 한글 글리프 보장: 폰트 파일 명시 로드(오프스크린 플랫폼 폴백 회피)
    family = "Malgun Gothic"
    font_path = Path("C:/Windows/Fonts/malgun.ttf")
    if font_path.exists():
        fams = QFontDatabase.applicationFontFamilies(
            QFontDatabase.addApplicationFont(str(font_path))
        )
        if fams:
            family = fams[0]
    app.setFont(QFont(family, 10))
    win = BuilderWindow()
    return app, win


def main() -> None:
    app, win = make_app()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
