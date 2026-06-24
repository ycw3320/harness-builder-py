"""Qt 3-pane 셸 (S1~S6). 공유 state·view_model 소비, 위젯 배선만 Qt 고유.

S1 3-pane(QSplitter) · S2 nav(context만 실동작+색점) · S3 36px 행 펼침(QPropertyAnimation)
· S4 편집→patch→우측 라이브 갱신 · S5 우패널(시뮬·lint·export) · S6 폴더쓰기(write_tree).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
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
from harness_fs.policy import MergeStrategy
from harness_fs.writer import write_tree

from .. import view_model as vm
from ..state import BuilderState

ACCENT = "#0969da"
BG = "#ffffff"
PANEL = "#f6f8fa"
BORDER = "#d0d7de"
TEXT = "#1f2328"
MUTED = "#656d76"

STYLESHEET = f"""
* {{ font-family: 'Malgun Gothic', 'Segoe UI', sans-serif; color: {TEXT}; }}
QMainWindow, QWidget#pane {{ background: {BG}; }}
QWidget#leftPane, QWidget#rightPane {{ background: {PANEL}; }}
QLabel#h1 {{ font-size: 15px; font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; font-size: 12px; }}
QLabel#section {{ font-size: 12px; font-weight: 600; color: {MUTED}; }}
QListWidget {{ background: transparent; border: none; }}
QListWidget::item {{ margin: 2px 6px; border-radius: 6px; }}
QListWidget::item:selected {{ background: #ddf4ff; }}
QListWidget::item:disabled {{ color: #afb8c1; }}
QFrame#row {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; }}
QFrame#card {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; }}
QPushButton#primary {{
    background: {ACCENT}; color: white; border: none; border-radius: 6px;
    padding: 7px 14px; font-weight: 600;
}}
QPushButton#primary:hover {{ background: #0860ca; }}
QPlainTextEdit, QLineEdit, QComboBox {{
    background: {BG}; border: 1px solid {BORDER}; border-radius: 6px; padding: 5px;
}}
QLabel#pill {{ border-radius: 9px; padding: 1px 8px; font-size: 11px; color: white; }}
QLabel#lintErr {{ color: #cf222e; font-size: 12px; }}
QLabel#lintWarn {{ color: #9a6700; font-size: 12px; }}
"""


def _dot(color: str, size: int = 10) -> QLabel:
    d = QLabel()
    d.setFixedSize(size, size)
    d.setStyleSheet(f"background: {color}; border-radius: {size // 2}px;")
    return d


class RowWidget(QFrame):
    """36px 컴팩트 행 — 클릭 시 펼쳐 heading/body 편집 (QPropertyAnimation)."""

    HEADER_H = 34
    COLLAPSED = 44  # 헤더(34) + 상/하 여백(5+5)
    EXPANDED = 210

    def __init__(self, row: vm.RowVM, state: BuilderState) -> None:
        super().__init__()
        self.setObjectName("row")
        self._row = row
        self._state = state
        self._open = False
        self.setMinimumHeight(self.COLLAPSED)
        self.setMaximumHeight(self.COLLAPSED)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 5, 12, 5)
        outer.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self._header_w = QWidget()
        self._header_w.setFixedHeight(self.HEADER_H)
        self._header_w.setLayout(header)
        header.addWidget(_dot(row.color))
        title = QLabel(row.title)
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        pill = QLabel(row.involvement_label)
        pill.setObjectName("pill")
        pill.setStyleSheet(f"background: {row.color}; border-radius: 9px; padding: 1px 8px;")
        header.addWidget(pill)
        kind = QLabel(row.kind)
        kind.setObjectName("muted")
        header.addWidget(kind)
        outer.addWidget(self._header_w)

        # 펼침 편집부 (prose 슬라이스: heading + body). 접힘 시 숨겨 레이아웃에서 제외(겹침 방지)
        self._editor = QWidget()
        ed = QVBoxLayout(self._editor)
        ed.setContentsMargins(0, 0, 0, 0)
        ed.setSpacing(4)
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
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(self._on_anim_done)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt 시그니처)
        if self._header_w.geometry().contains(event.position().toPoint()):
            self.toggle()
        super().mousePressEvent(event)

    def set_open(self, value: bool) -> None:
        self._open = value
        if value:
            self._editor.setVisible(True)  # 펼칠 땐 먼저 보이고 높이 애니메이션
        self._anim.stop()
        self._anim.setStartValue(self.maximumHeight())
        self._anim.setEndValue(self.EXPANDED if value else self.COLLAPSED)
        self._anim.start()

    def _on_anim_done(self) -> None:
        if not self._open:
            self._editor.setVisible(False)  # 접힘 완료 후 숨김(겹침·잔상 방지)

    def toggle(self) -> None:
        self.set_open(not self._open)

    def _on_heading(self, text: str) -> None:
        self._state.patch(self._row.id, {"heading": text})

    def _on_body(self) -> None:
        self._state.patch(self._row.id, {"body": self._body.toPlainText()})


class BuilderWindow(QMainWindow):
    def __init__(self, state: BuilderState | None = None) -> None:
        super().__init__()
        self.state = state or BuilderState("my-project")
        self.setWindowTitle("하네스 빌더 — 실행 전 시뮬레이터형 (Qt 프로토타입)")
        self.setStyleSheet(STYLESHEET)
        self.resize(1160, 700)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_left())
        self._center_host = QWidget()
        self._center_host.setObjectName("pane")
        QVBoxLayout(self._center_host).setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(self._center_host)
        self._right_host = QWidget()
        self._right_host.setObjectName("rightPane")
        QVBoxLayout(self._right_host).setContentsMargins(0, 0, 0, 0)
        splitter.addWidget(self._right_host)
        splitter.setSizes([230, 560, 370])
        splitter.setCollapsible(0, False)
        self.setCentralWidget(splitter)

        self._rows: list[RowWidget] = []
        self.state.subscribe(self.refresh)
        self.refresh()

    # 좌 nav (S2) ---
    def _build_left(self) -> QWidget:
        w = QWidget()
        w.setObjectName("leftPane")
        w.setMinimumWidth(200)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 16, 14, 16)
        title = QLabel("구성 영역")
        title.setObjectName("h1")
        lay.addWidget(title)
        hint = QLabel("6계층을 차례로 채우면 하네스가 완성됩니다.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self._nav = QListWidget()
        for item in vm.nav_items(self.state):
            li = QListWidgetItem(self._nav)
            cell = QWidget()
            row = QHBoxLayout(cell)
            row.setContentsMargins(8, 6, 8, 6)
            row.addWidget(_dot(item.dot_color))
            txt = QVBoxLayout()
            txt.setSpacing(0)
            name = QLabel(f"{item.label}  ({item.count})")
            name.setStyleSheet("font-weight: 600;")
            txt.addWidget(name)
            sub = QLabel(item.hint)
            sub.setObjectName("muted")
            txt.addWidget(sub)
            row.addLayout(txt)
            row.addStretch(1)
            li.setSizeHint(cell.sizeHint())
            self._nav.addItem(li)
            self._nav.setItemWidget(li, cell)
            if not item.interactive:
                li.setFlags(li.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            elif item.selected:
                li.setSelected(True)
        self._nav.itemClicked.connect(self._on_nav)
        lay.addWidget(self._nav, 1)
        return w

    def _on_nav(self, li: QListWidgetItem) -> None:
        idx = self._nav.row(li)
        layer = vm.layer_order[idx]
        self.state.set_selected_layer(layer)

    # 중앙 (S3/S4) ---
    def refresh(self) -> None:
        self._rebuild_center()
        self._rebuild_right()

    def _clear(self, host: QWidget) -> QVBoxLayout:
        lay = host.layout()
        while lay.count():
            item = lay.takeAt(0)
            wdg = item.widget()
            if wdg is not None:
                wdg.setParent(None)
                wdg.deleteLater()
        inner = QWidget()
        lay.addWidget(inner)
        v = QVBoxLayout(inner)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(10)
        return v

    def _rebuild_center(self) -> None:
        v = self._clear(self._center_host)
        intro = vm.layer_intro(self.state)
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
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
        rows_lay.setSpacing(8)
        self._rows = []
        for r in vm.rows_for_selected(self.state):
            rw = RowWidget(r, self.state)
            self._rows.append(rw)
            rows_lay.addWidget(rw)
        rows_lay.addStretch(1)
        scroll.setWidget(holder)
        v.addWidget(scroll, 1)

    # 우 패널 (S5/S6) ---
    def _rebuild_right(self) -> None:
        v = self._clear(self._right_host)

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
            f.setObjectName("muted")
            v.addWidget(f)

        v.addStretch(1)
        combo = QComboBox()
        combo.addItems(["minimal", "harness-only"])
        combo.setCurrentText(self.state.scaffold)
        combo.currentTextChanged.connect(self.state.set_scaffold)
        v.addWidget(combo)
        btn = QPushButton("폴더 선택 → 하네스 생성")
        btn.setObjectName("primary")
        btn.clicked.connect(self._on_export)
        v.addWidget(btn)

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
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
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
