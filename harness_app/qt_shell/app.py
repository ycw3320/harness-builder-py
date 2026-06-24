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
    QFileDialog,
    QFrame,
    QHBoxLayout,
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


def _dot(color: str, size: int = 10) -> QLabel:
    d = QLabel()
    d.setFixedSize(size, size)
    d.setStyleSheet(f"background: {color}; border-radius: {size // 2}px;")
    return d


class RowWidget(QFrame):
    """컴팩트 행 — 클릭 시 펼쳐 heading/body 편집. 접힘 시 편집부 숨김(겹침 방지)."""

    HEADER_H = 34
    COLLAPSED = 44
    EXPANDED = 210

    def __init__(self, row: vm.RowVM, state: BuilderState, tokens: dict, is_dark: bool) -> None:
        super().__init__()
        self.setObjectName("rowCard")
        self._row = row
        self._state = state
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
        kind = QLabel(row.kind)
        kind.setObjectName("faint")
        header.addWidget(kind)
        # 행 CRUD 컨트롤 (위/아래/복제/삭제) — 버튼이 클릭을 소비해 펼침 토글과 분리됨
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

        # 편집부 — PM3-A: prose 만 인라인 편집(전 kind 폼은 PM3-B)
        self._is_prose = row.kind == "prose-guideline"
        self._editor: QWidget | None = None
        if self._is_prose:
            self._editor = QWidget()
            ed = QVBoxLayout(self._editor)
            ed.setContentsMargins(0, 0, 0, 0)
            ed.setSpacing(5)
            self._heading = QLineEdit(row.heading or "")
            self._heading.setPlaceholderText("섹션 제목")
            self._heading.textChanged.connect(self._on_heading)
            ed.addWidget(self._heading)
            self._body = QPlainTextEdit(row.body or "")
            self._body.setPlaceholderText("외부 LLM 답변을 여기에 붙여넣으세요…")
            self._body.setMinimumHeight(104)
            self._body.textChanged.connect(self._on_body)
            ed.addWidget(self._body)
            self._editor.setVisible(False)
            outer.addWidget(self._editor)

        self._anim = QPropertyAnimation(self, b"maximumHeight")
        self._anim.setDuration(170)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(self._on_anim_done)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt 시그니처)
        if self._is_prose and self._header_w.geometry().contains(event.position().toPoint()):
            self.toggle()
        super().mousePressEvent(event)

    def set_open(self, value: bool) -> None:
        if self._editor is None:
            return
        self._open = value
        if value:
            self._editor.setVisible(True)
        self._anim.stop()
        self._anim.setStartValue(self.maximumHeight())
        self._anim.setEndValue(self.EXPANDED if value else self.COLLAPSED)
        self._anim.start()

    def _on_anim_done(self) -> None:
        if not self._open and self._editor is not None:
            self._editor.setVisible(False)

    def toggle(self) -> None:
        if self._editor is not None:
            self.set_open(not self._open)

    def _on_heading(self, text: str) -> None:
        self._state.patch(self._row.id, {"heading": text})

    def _on_body(self) -> None:
        self._state.patch(self._row.id, {"body": self._body.toPlainText()})


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
            tuple((c.id, c.enabled) for c in self.state.ir.components),
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
        self._rows: list[RowWidget] = []
        for r in vm.rows_for_selected(self.state):
            rw = RowWidget(r, self.state, self.tokens, self.is_dark)
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
        """선택 계층의 기본 추가 가능 kind 버튼 — 동적 추가(요구 1)."""
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        entries = [
            e for e in addable_kinds_by_layer.get(self.state.selected_layer, []) if e["basic"]
        ]
        if not entries:
            return bar
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
