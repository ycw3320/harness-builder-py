"""Qt 3-pane 셸 (S1~S6) — Apple 미니멀 테마(라이트 크림 ↔ 다크 Space Gray) 토글.

공유 state·view_model 소비, 위젯 배선만 Qt 고유. 테마 토큰은 LIGHT/DARK dict 단일 소스에서
build_qss 로 주입, 토글은 QApplication 스타일시트 런타임 스왑(재시작 불필요·QSettings persist).
편집(콘텐츠 patch)은 우패널만 갱신, 구조 변경 시에만 중앙/좌측 재빌드(편집 포커스 보존).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from string import Template

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from harness_core.export.assemble_project import assemble_project
from harness_core.ir.enforcement import promote
from harness_core.ir.registry import addable_kinds_by_layer, kind_registry
from harness_fs.importer import import_project
from harness_fs.policy import MergeStrategy
from harness_fs.writer import write_tree
from harness_llm import credentials
from harness_llm.client import DEFAULT_MODEL, MODELS, AnthropicClient, LLMError, anthropic_available

from .. import view_model as vm
from ..guides import HARNESS_AHA, HARNESS_DEFINITION, LAYER_FLOW_CAPTION, layer_order
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

# 번들 Pretendard 를 1순위로 — 모든 PC에서 동일·깔끔. 미설치 환경 대비 시스템 폰트 폴백 동반.
FONT_STACK = (
    '"Pretendard", "Malgun Gothic", "맑은 고딕", "Segoe UI", "Apple SD Gothic Neo", sans-serif'
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
QFrame#ahaCard { background: $selected_bg; border: 1px solid $accent; border-radius: 10px; }

QWidget#landing { background: $bg; }
QLabel#heroTitle { font-size: 30px; font-weight: 700; color: $text; }
QLabel#tagline { font-size: 15px; color: $text_muted; }
QLabel#landingH2 { font-size: 15px; font-weight: 600; color: $text; }
QLabel#landingBody { font-size: 13px; color: $text_muted; }
QFrame#valueCard { background: $surface; border: 1px solid $border; border-radius: 10px; }
QLabel#valueTitle { font-size: 13px; font-weight: 600; color: $text; }
QLabel#valueDesc { font-size: 12px; color: $text_muted; }
QPushButton#startBtn {
    background-color: $accent; color: $on_accent; border: none;
    border-radius: 10px; padding: 12px 28px; font-size: 15px; font-weight: 600;
}
QPushButton#startBtn:hover { background-color: $accent_hover; }

QProgressBar#meter { background: $surface_alt; border: none; border-radius: 4px; }
QProgressBar#meter::chunk { background: $accent; border-radius: 4px; }

QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { margin: 2px 4px; border-radius: 8px; }
QListWidget::item:selected { background: $selected_bg; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $text_faint; border-radius: 4px; min-height: 26px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: $text_faint; border-radius: 4px; min-width: 26px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
""")


def build_qss(tokens: dict) -> str:
    return _QSS.substitute(font=FONT_STACK, **tokens)


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


_PRESET_LABELS = [
    ("minimal", "빈 시작"),
    ("safety-first", "안전우선"),
    ("speed", "속도"),
    ("mvp", "MVP"),
    ("enterprise", "엔터프라이즈"),
]
# PM6-S5: 프리셋 1줄 설명(무엇이 채워지는지) — 드롭다운 툴팁 + 현재 선택 설명에 사용
_PRESET_DESC = {
    "minimal": "빈 시작 — 규칙 없이 처음부터 직접 채웁니다.",
    "safety-first": "안전우선 — .env 차단·강제 push 확인 등 기본 안전망 포함(추천).",
    "speed": "속도 — 자주 쓰는 개발 명령(npm·git 등)을 자유 허용.",
    "mvp": "MVP — 새 프로젝트용 균형 스타터(기본 지침 + 핵심 권한).",
    "enterprise": "엔터프라이즈 — 안전우선 + 코드리뷰 규칙·리뷰 에이전트까지.",
}
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
        # PM6-S5: 2단 풀이 — 라벨은 쉬운 말, dev 설명은 호버 툴팁('(?)' 로 호버 가능 신호).
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        lab = QLabel(f"{label}  (?)" if tip else label)
        lab.setObjectName("faint")
        if tip:
            lab.setToolTip(tip)
            widget.setToolTip(tip)
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
            ai = QPushButton("AI로 채우기")
            ai.setObjectName("primaryBtn")
            ai.setCursor(Qt.CursorShape.PointingHandCursor)
            ai.clicked.connect(lambda: self._llm_fill(self._row.kind, self._row.id))
            head.addWidget(ai)
        if self._promote is not None and self._row.promotable:
            up = QPushButton("강제수준 ↑")
            up.setObjectName("addBtn")
            up.setToolTip("같은 의도를 더 강하게 집행(프로즈→정책문서→hook)")
            up.setCursor(Qt.CursorShape.PointingHandCursor)
            up.clicked.connect(lambda: self._promote(self._row.id))
            head.addWidget(up)
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


class LandingPage(QWidget):
    """첫 진입 소개 화면 — 하네스 엔지니어링이 뭔지·왜 만들었는지 + [시작하기].

    PM6 측정의 잔여 약점('우측을 안 보면 정의를 놓침=경로 의존')을 보완 — 누구나 진입 전에
    정의·가치를 본다. 스타일은 전부 QSS objectName(인라인 색 금지)이라 테마 토글이 자동 반영된다.
    """

    def __init__(self, on_start) -> None:
        super().__init__()
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

        hero = QLabel("하네스 빌더")
        hero.setObjectName("heroTitle")
        col.addWidget(hero)
        tag = QLabel("AI 코딩 도구에게 '안전벨트'를 채우는 가장 쉬운 방법")
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
        start = QPushButton("시작하기  →")
        start.setObjectName("startBtn")
        start.setCursor(Qt.CursorShape.PointingHandCursor)
        start.clicked.connect(on_start)
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


class BuilderWindow(QMainWindow):
    def __init__(
        self, state: BuilderState | None = None, settings: QSettings | None = None
    ) -> None:
        super().__init__()
        # PM6-S1: 빈 캔버스(minimal) 대신 '작동하는 예시'(safety-first)로 시작 —
        # 첫 화면에서 before/after 차단 시연이 보여야 초심자 아하 모먼트가 가능.
        self.state = state or BuilderState("my-project", preset="safety-first")
        # settings 주입은 테스트 격리용(미지정 시 사용자 QSettings)
        self._settings = settings or QSettings("harness-builder", "qt-shell")
        # PM6-S4: 규칙을 처음 꺼본(=인과 체감) 직후 정의를 페이드인하는 '체감→정의' 서사 상태.
        # 아하는 persist — 랜딩 스킵과 결합해도 정의 노출이 0회가 되지 않게 재실행 시 배너 유지.
        self._aha_revealed = self._settings.value("aha_seen", False, type=bool)
        self._aha_animated = self._aha_revealed  # 복원 시 애니메이션 없이 정적 표시
        # PM6-S5: 프리셋이 넣어준 시드 = '예시'. 사용자가 편집하면 해당 id 를 제거(배너 사라짐).
        self._example_ids: set[str] = {c.id for c in self.state.ir.components}
        self._reseed_examples = False  # 프리셋 교체 시 1회 재계산 플래그(이중 재빌드·깜빡임 방지)
        self._dup_prev_ids: set[str] | None = None  # 예시 복제 시 새 id 감지용(단일 재빌드 유지)
        self.theme_name = os.environ.get("HB_THEME") or self._settings.value("theme", "light")
        if self.theme_name not in THEMES:
            self.theme_name = "light"
        self.setWindowTitle("하네스 빌더 — 실행 전 시뮬레이터형")
        self.resize(1180, 720)
        self.setMinimumSize(960, 640)  # frozen(PyInstaller) 환경 창 축소 방어

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._left_host = self._host("leftPane")
        self._center_host = self._host("centerPane")
        self._right_host = self._host("rightPane")
        for h in (self._left_host, self._center_host, self._right_host):
            splitter.addWidget(h)
        splitter.setSizes([240, 560, 380])
        splitter.setCollapsible(0, False)

        # 랜딩(소개) → [시작하기] → 빌더(3-pane). QStackedWidget 로 전환.
        self._stack = QStackedWidget()
        self._stack.addWidget(LandingPage(self._enter_builder))  # index 0: 소개
        self._stack.addWidget(splitter)  # index 1: 빌더
        self.setCentralWidget(self._stack)
        # 재방문자는 빌더로 직행(랜딩은 '소개' 버튼으로 상시 재방문 가능).
        # 정의 노출은 persist 된 아하 배너가 담당하므로 스킵해도 0회가 되지 않는다.
        # 스킵 조건 = 랜딩을 봤고 '아하(정의)'까지 만난 경우만 — 정의 노출 0회 불변식 보장.
        # (랜딩만 스치고 종료한 초심자는 다음 실행에도 랜딩부터)
        if self._settings.value("landing_seen", False, type=bool) and self._aha_revealed:
            self._stack.setCurrentIndex(1)

        self._sig: tuple | None = None
        self.state.subscribe(self._on_change)
        self._apply_theme()

    def _enter_builder(self) -> None:
        self._settings.setValue("landing_seen", True)
        self._stack.setCurrentIndex(1)

    def _show_landing(self) -> None:
        self._stack.setCurrentIndex(0)

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
        # involvement 는 미추적 — 콤보 변경이 구조 재빌드로 라우팅되면 편집 중 행이 파괴(접힘)됨.
        # 헤더 색점·pill 은 RowWidget._update_involvement 가 in-place 갱신한다.
        return (
            self.theme_name,
            self.state.selected_layer,
            self.state.advanced_mode,
            tuple((c.id, c.enabled) for c in self.state.ir.components),
        )

    def _on_change(self) -> None:
        """편집(콘텐츠)은 우패널만, 구조/계층/테마 변경 시에만 중앙·좌측 재빌드(포커스 보존)."""
        if self._reseed_examples:  # 프리셋 교체 직후 1회: 새 시드를 '예시'로(단일 재빌드 내에서)
            self._reseed_examples = False
            self._example_ids = {c.id for c in self.state.ir.components}
        if self._dup_prev_ids is not None:  # 예시 복제 직후 1회: 새 id 에 예시 표식 승계
            self._example_ids |= {c.id for c in self.state.ir.components} - self._dup_prev_ids
            self._dup_prev_ids = None
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
        hint = QLabel("6개 영역을 차례로 채우면 하네스가 완성됩니다.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        v.addWidget(hint)
        # PM6-S4: '왜 이 순서인가' 멘탈모델 캡션 — 하네스를 '차단 설정'으로 과소일반화 방지
        flow = QLabel(LAYER_FLOW_CAPTION)
        flow.setObjectName("faint")
        flow.setWordWrap(True)
        v.addWidget(flow)
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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._center_scroll = scroll  # 점프 시 ensureWidgetVisible 용(화면 밖 무반응 방지)
        holder = QWidget()
        rows_lay = QVBoxLayout(holder)
        rows_lay.setContentsMargins(0, 0, 0, 0)
        rows_lay.setSpacing(10)
        fill = self._llm_fill_component if self._llm_ready() else None
        self._rows: list[RowWidget] = []
        for r in vm.rows_for_selected(self.state):
            rw = RowWidget(
                r,
                self.state,
                self.tokens,
                self.is_dark,
                fill,
                self._promote_component,
                is_example=r.id in self._example_ids,
                on_example_edit=self._on_example_edited,
                on_duplicate=self._duplicate_component,
            )
            self._rows.append(rw)
            rows_lay.addWidget(rw)
        rows_lay.addStretch(1)
        scroll.setWidget(holder)
        v.addWidget(scroll, 1)
        v.addWidget(self._add_bar())

    def _on_example_edited(self, comp_id: str) -> None:
        """예시 항목을 사용자가 편집 → 더 이상 예시 아님(재빌드 시 배너 미표시)."""
        self._example_ids.discard(comp_id)

    def _duplicate_component(self, comp_id: str) -> None:
        """복제 — 원본이 '미편집 예시'면 사본도 예시로 승계(태그·export 경고 누락 방지).

        새 id 는 복제 후에야 알 수 있으므로, 이전 id 집합을 기억해 _on_change 가
        차집합으로 감지한다(_reseed_examples 와 같은 단일 재빌드 패턴).
        """
        if comp_id in self._example_ids:
            self._dup_prev_ids = {c.id for c in self.state.ir.components}
        self.state.duplicate(comp_id)

    def _preset_toggle(self) -> QWidget:
        # PM6-S5: 프리셋 비교 — 항목 툴팁 + 현재 프리셋 1줄 설명으로 '무엇이 채워지는지' 안내.
        box = QWidget()
        col = QVBoxLayout(box)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)
        cb = QComboBox()
        keys = []
        for key, label in _PRESET_LABELS:
            cb.addItem(f"프리셋 · {label}")
            cb.setItemData(len(keys), _PRESET_DESC.get(key, ""), Qt.ItemDataRole.ToolTipRole)
            keys.append(key)
        if self.state.preset in keys:
            cb.setCurrentIndex(keys.index(self.state.preset))
        cb.currentIndexChanged.connect(lambda i: self._on_preset_change(keys[i]))
        col.addWidget(cb)
        desc = QLabel(_PRESET_DESC.get(self.state.preset, ""))
        desc.setObjectName("faint")
        desc.setWordWrap(True)
        col.addWidget(desc)
        return box

    def _on_preset_change(self, key: str) -> None:
        # 단일 재빌드: 플래그만 세우고 load_preset 의 통지가 _on_change 에서 example 재계산+재빌드.
        # (이전엔 load_preset 후 _force_rebuild 로 2회 그려 빈 패널이 한 프레임 깜빡였음)
        self._reseed_examples = True
        self.state.load_preset(key)

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
        # PM6-S2: 내용이 늘어 720px 를 초과 → 스크롤로 감싸 카드(word-wrap)가 압축되지 않게.
        outer = self._clear(self._right_host, (0, 0, 0, 0))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        v = QVBoxLayout(body)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(10)
        scroll.setWidget(body)
        outer.addWidget(scroll)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        view_lbl = QLabel("보기")
        view_lbl.setObjectName("section")
        head.addWidget(view_lbl)
        head.addStretch(1)
        intro = QPushButton("소개")
        intro.setObjectName("addBtn")
        intro.setCursor(Qt.CursorShape.PointingHandCursor)
        intro.setToolTip("소개 화면 다시 보기")
        intro.clicked.connect(self._show_landing)
        head.addWidget(intro)
        helpb = QPushButton("도움말")
        helpb.setObjectName("addBtn")
        helpb.setCursor(Qt.CursorShape.PointingHandCursor)
        helpb.clicked.connect(self._show_welcome)
        head.addWidget(helpb)
        gear = QPushButton("LLM 설정")
        gear.setObjectName("addBtn")
        gear.setCursor(Qt.CursorShape.PointingHandCursor)
        gear.clicked.connect(self._open_settings)
        head.addWidget(gear)
        head.addWidget(self._theme_toggle())
        head_w = QWidget()
        head_w.setLayout(head)
        v.addWidget(head_w)

        # 완성도 미터 + 다음 추천 영역 (§0.6 안내형 누적 흐름)
        comp = vm.completion(self.state)
        v.addWidget(self._section(f"완성도 · 구성된 영역 {comp.filled}/{comp.total}"))
        meter = QProgressBar()
        meter.setObjectName("meter")
        meter.setRange(0, 100)
        meter.setValue(comp.percent)
        meter.setTextVisible(False)
        meter.setFixedHeight(8)
        v.addWidget(meter)
        if comp.next_layer:
            nxt = QPushButton(f"다음 추천 영역: {comp.next_label} →")
            nxt.setObjectName("addBtn")
            nxt.setCursor(Qt.CursorShape.PointingHandCursor)
            nxt.clicked.connect(
                lambda _c=False, ly=comp.next_layer: self.state.set_selected_layer(ly)
            )
            v.addWidget(nxt)
        else:
            done = QLabel("핵심 영역 구성 완료 — 내보낼 준비 완료 ✓")
            done.setObjectName("muted")
            done.setWordWrap(True)
            v.addWidget(done)

        # PM6-S2/S3: before/after 2열 시연(빈 IR vs 현재 IR) + reason + '켜진 규칙' 토글.
        # 우패널은 _on_change 가 항상 재빌드 → 토글 시 즉시 역전(추가 배선 0).
        # PM6-S4: 인과 체감(규칙 끄기) 후 정의 페이드인 — '체감 먼저, 정의 나중'.
        if self._aha_revealed:
            v.addWidget(self._aha_banner())
        v.addWidget(self._section("하네스 없으면 ↔ 지금 · 실행 전 시뮬레이터(LLM 0회)"))
        compare = vm.sim_compare(self.state)
        has_invalid = any(s.after_raw == "invalid" for s in compare)
        for s in compare:
            v.addWidget(self._sim_compare_row(s))
        rules = vm.sim_rules(self.state)
        if rules:
            # 힌트는 상황별 1개: 패턴 오류 > 꺼보세요(아하 전) > 허용뿐 안내 — 거짓 약속 금지
            if has_invalid:
                hint_text = (
                    "패턴 오류를 먼저 수정하세요 — 위 붉은 줄을 클릭하면 해당 규칙으로 이동합니다"
                )
            elif any(r.affects_sim for r in rules):
                hint_text = (
                    "아래 규칙을 꺼보세요 — 차단이 풀립니다" if not self._aha_revealed else ""
                )
            else:  # 허용 규칙뿐(speed 등) — 토글해도 결과가 안 변하므로 '꺼보세요' 약속 금지
                hint_text = "지금 규칙은 모두 허용이라 차단 시연이 없어요 — 가드레일에서 차단 규칙을 추가해보세요"
            if hint_text:
                hint = QLabel(hint_text)
                hint.setObjectName("faint")
                hint.setWordWrap(True)
                v.addWidget(hint)
            for r in rules:
                v.addWidget(self._rule_toggle(r))
        else:  # 차단 규칙 0개(빈 시작·가져오기 등) — 아하 도달 경로 안내(끊긴 서사 폴백)
            none_hint = QLabel(
                "차단 규칙(hook·권한)을 추가하면 여기서 꺼보며 효과를 확인할 수 있어요 — "
                "좌측 '가드레일' 영역에서 시작하세요."
            )
            none_hint.setObjectName("faint")
            none_hint.setWordWrap(True)
            v.addWidget(none_hint)

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
        imp = QPushButton("기존 폴더 가져오기")
        imp.setObjectName("addBtn")
        imp.setCursor(Qt.CursorShape.PointingHandCursor)
        imp.clicked.connect(self._on_import)
        v.addWidget(imp)
        combo = QComboBox()
        combo.addItems(["minimal", "harness-only"])
        combo.setCurrentText(self.state.scaffold)
        combo.currentTextChanged.connect(self.state.set_scaffold)
        v.addWidget(combo)
        btn = QPushButton("폴더 선택 → 하네스 생성")
        btn.setObjectName("primaryBtn")
        btn.clicked.connect(self._on_export)
        v.addWidget(btn)

    # PM6-S2/S3: before/after 시연 헬퍼 ---
    def _outcome_style(self, raw: str, column: str) -> tuple[str, str]:
        """outcome → (색, 배지단어). 글리프(⚠/✓)는 Malgun 미지원이라 한국어 단어로 대비.

        column='before'(규칙 없으면)에서 '통과'는 위험, 'after'(지금)의 차단은 안전.
        """
        t = self.tokens
        if raw == "allowed":
            return (t["warn"], "(위험)") if column == "before" else (t["text_muted"], "")
        if raw == "ask":
            return (t["warn"], "")  # 라벨 '사용자 확인' 자체가 의미 전달
        if raw == "invalid":
            return (t["danger"], "")  # hook 패턴 오류 — 규칙 수정 필요
        return (t["ok"], "(안전)")  # blocked-by-hook / blocked-by-permission

    def _sim_line(self, prefix: str, label: str, raw: str, column: str, blocked_by=None) -> QLabel:
        color, badge = self._outcome_style(raw, column)
        text = f"{prefix} →  {label} {badge}".rstrip()
        if blocked_by:  # 차단·확인 줄 클릭 → 원인 항목으로 점프(S3)
            lbl: QLabel = ClickableLabel(text, lambda cid=blocked_by: self._jump_to_component(cid))
        else:
            lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
        lbl.setWordWrap(True)
        return lbl

    def _sim_compare_row(self, s: vm.SimCompareVM) -> QWidget:
        card = QFrame()
        card.setObjectName("rowCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(11, 8, 11, 8)
        lay.setSpacing(3)
        title = QLabel(s.label)
        title.setStyleSheet(f"font-weight: 600; color: {self.tokens['text']};")
        title.setWordWrap(True)
        lay.addWidget(title)
        lay.addWidget(self._sim_line("규칙 없으면", s.before_outcome, s.before_raw, "before"))
        lay.addWidget(
            self._sim_line("지금", s.after_outcome, s.after_raw, "after", s.after_blocked_by)
        )
        if s.after_reason and s.after_raw != "allowed":
            why = QLabel(s.after_reason)
            why.setObjectName("faint")
            why.setWordWrap(True)
            lay.addWidget(why)
        return card

    def _rule_toggle(self, r: vm.SimRuleVM) -> QWidget:
        # allow 권한 등은 시뮬 무영향이지만 enabled 는 export 포함 여부를 좌우하는 실기능 —
        # 목록에서 빼는 대신 배지로 구분(토글 수단 소멸 방지).
        title = r.title if r.affects_sim else f"{r.title} · 시뮬 영향 없음"
        return RuleToggle(
            title, r.enabled, self.tokens, lambda _on, cid=r.id: self._on_rule_toggle(cid)
        )

    def _on_rule_toggle(self, comp_id: str) -> None:
        """결과가 '실제로 변하는' 첫 토글 = 인과 체감 → 정의 페이드인 트리거 후 실제 토글.

        무의미 토글(결과 불변)에 배너를 붙이면 체감→정의 서사가 거짓 인과가 되므로,
        가상 평가(toggle_changes_sim)로 판정한다. 아하는 QSettings 로 persist(재실행 시 유지).
        """
        if not self._aha_revealed and vm.toggle_changes_sim(self.state, comp_id):
            self._aha_revealed = True
            self._settings.setValue("aha_seen", True)
        self.state.toggle(comp_id)  # _notify → _rebuild_right(배너 등장 + 결과 역전)

    def _aha_banner(self) -> QWidget:
        """'방금 본 게 하네스예요' + 안전벨트 정의 — 첫 등장 1회만 페이드인."""
        card = QFrame()
        card.setObjectName("ahaCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)
        t = QLabel(HARNESS_AHA)
        t.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {self.tokens['accent']};")
        t.setWordWrap(True)
        lay.addWidget(t)
        d = QLabel(HARNESS_DEFINITION)
        d.setObjectName("muted")
        d.setWordWrap(True)
        lay.addWidget(d)
        if not self._aha_animated:  # 재빌드마다 재생 방지 — 최초 1회만
            self._aha_animated = True
            eff = QGraphicsOpacityEffect(card)
            card.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", card)
            anim.setDuration(420)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            self._aha_anim = anim  # 참조 유지(GC 방지)
        return card

    def _jump_to_component(self, comp_id: str) -> None:
        """시뮬레이터 차단 줄 → 그 결과를 만든 컴포넌트로 이동·펼침·스크롤."""
        comp = next((c for c in self.state.ir.components if c.id == comp_id), None)
        if comp is None:
            return
        if self.state.selected_layer != comp.layer:
            self.state.set_selected_layer(comp.layer)  # 중앙 재빌드(_rows 갱신)
        for rw in getattr(self, "_rows", []):
            if rw.row_id == comp_id:
                rw.set_open(True)
                # 대상이 뷰포트 밖이면 '무반응'으로 보임 — 펼침 애니(170ms) 종료 후 스크롤 보장
                QTimer.singleShot(200, lambda w=rw: self._scroll_to_row(w))
                break

    def _scroll_to_row(self, rw: QWidget) -> None:
        try:
            scroll = getattr(self, "_center_scroll", None)
            if scroll is not None:
                scroll.ensureWidgetVisible(rw, 0, 60)
        except RuntimeError:
            pass  # 타이머 사이 재빌드로 위젯이 파괴된 경우(무해)

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
        self._show_export_done(dest, report)

    def _show_export_done(self, dest: str, report) -> None:
        """PM6-S6: 생성 후 '다음 단계' — 결과물을 손에 쥐고도 작동을 못 보던 갭을 닫는다."""
        dlg = QDialog(self)
        dlg.setWindowTitle("하네스 생성 완료 — 다음 단계")
        dlg.setMinimumWidth(520)
        v = QVBoxLayout(dlg)
        v.setSpacing(10)
        title = QLabel("하네스를 만들었어요. 이제 이렇게 쓰세요")
        title.setObjectName("h1")
        v.addWidget(title)
        summary = QLabel(f"생성 {len(report.created)}개 · 건너뜀 {len(report.skipped)}개\n{dest}")
        summary.setObjectName("muted")
        summary.setWordWrap(True)
        v.addWidget(summary)
        # 편집하지 않은 '예시'가 그대로 포함됐는지 마지막 확인(예시 태그는 UI 표식일 뿐 export 에 포함됨).
        n_ex = sum(1 for c in self.state.ir.components if c.enabled and c.id in self._example_ids)
        if n_ex:
            warn = QLabel(
                f"편집하지 않은 예시 {n_ex}개가 그대로 포함됐어요 — 내 프로젝트에 맞는지 검토하거나 "
                "필요 없으면 지운 뒤 다시 생성하세요."
            )
            warn.setObjectName("lintWarn")
            warn.setWordWrap(True)
            v.addWidget(warn)
        steps = QLabel(
            "① 이 폴더를 프로젝트 루트에 두세요(이미 프로젝트라면 그대로).\n"
            "② 그 폴더에서 Claude Code를 실행하세요 — 터미널에서 claude\n"
            "   터미널이 처음이라면: [폴더 열기] 후 폴더 창 주소칸에 cmd 입력 → 엔터 → 붙여넣기.\n"
            "③ 방금 시뮬레이터에서 본 차단(.env·강제 push)이 실제로 적용됩니다."
        )
        steps.setObjectName("muted")
        steps.setWordWrap(True)
        v.addWidget(steps)
        row = QHBoxLayout()
        copyb = QPushButton("이동+실행 명령 복사")
        copyb.setObjectName("addBtn")
        copyb.setCursor(Qt.CursorShape.PointingHandCursor)
        copyb.setToolTip(
            "터미널에 붙여넣으면 폴더 이동 후 Claude Code 가 실행됩니다 (cmd·PowerShell 공용)"
        )
        # pushd: cmd 에서 드라이브 전환 포함(cd 는 /d 없인 드라이브 미전환), PowerShell 은
        # Push-Location 별칭으로 동일. 트레일링 개행 = 마지막 명령까지 자동 실행.
        cmd_text = f'pushd "{os.path.normpath(dest)}"\nclaude\n'
        copyb.clicked.connect(lambda: QApplication.clipboard().setText(cmd_text))
        row.addWidget(copyb)
        openb = QPushButton("폴더 열기")
        openb.setObjectName("addBtn")
        openb.setCursor(Qt.CursorShape.PointingHandCursor)
        openb.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(dest)))
        row.addWidget(openb)
        row.addStretch(1)
        close = QPushButton("닫기")
        close.setObjectName("primaryBtn")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(dlg.accept)
        row.addWidget(close)
        rw = QWidget()
        rw.setLayout(row)
        v.addWidget(rw)
        dlg.exec()

    def _on_import(self) -> None:
        src = QFileDialog.getExistingDirectory(self, "기존 프로젝트 루트(.claude 포함) 선택")
        if not src:
            return
        try:
            ir = import_project(src)
        except Exception as e:
            QMessageBox.warning(self, "가져오기 실패", str(e))
            return
        n = len(ir.components)
        if n == 0:
            QMessageBox.information(self, "가져오기", "인식된 .claude 구성요소가 없습니다.")
            return
        ans = QMessageBox.question(
            self, "가져오기", f"{n}개 구성요소를 불러옵니다. 현재 작업을 대체할까요?"
        )
        if ans == QMessageBox.StandardButton.Yes:
            self._example_ids = set()  # 가져온 구성은 실제 설정 — load_ir 통지 '이전'에 클리어
            self.state.load_ir(ir)

    def _promote_component(self, comp_id: str) -> None:
        comp = next((c for c in self.state.ir.components if c.id == comp_id), None)
        if comp is None:
            return
        promoted = promote(comp)
        if promoted is None:
            QMessageBox.information(self, "강제수준", "이미 최고 강제수준(자동 차단)입니다.")
            return
        self.state.replace(comp_id, promoted)
        self.state.set_selected_layer(promoted.layer)  # 승격 결과(가드레일)가 보이도록
        for rw in self._rows:
            if rw.row_id == promoted.id:
                rw.set_open(True)
                break

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
        self._example_ids.discard(comp_id)  # AI로 채움 = 더 이상 '미편집 예시' 아님(오카운트 방지)
        self.state.patch(comp_id, patch)
        self._force_rebuild()
        for rw in self._rows:
            if rw.row_id == comp_id:
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

    # 온보딩 (PM5) — 첫 실행 환영 + 도움말 ---
    def maybe_show_welcome(self) -> None:
        # PM6-S4: 첫 실행에 텍스트 벽 모달 없음 — 곧장 before/after 대비로 '체감 먼저'.
        # 정의는 사용자가 규칙을 꺼본 직후(아하) 우패널에 페이드인된다. 도움말 버튼은 _show_welcome.
        pass

    def _show_welcome(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("하네스 빌더 — 안내")
        dlg.setMinimumWidth(520)
        v = QVBoxLayout(dlg)
        v.setSpacing(10)
        title = QLabel("하네스란?")
        title.setObjectName("h1")
        v.addWidget(title)
        body = QLabel(HARNESS_DEFINITION)
        body.setObjectName("muted")
        body.setWordWrap(True)
        v.addWidget(body)
        steps = QLabel(
            "이렇게 쓰세요\n"
            "① 우측 '하네스 없으면 ↔ 지금'에서 규칙을 꺼보며 효과를 직접 확인하세요.\n"
            "② 좌측 6개 영역을 차례로 채워 내 프로젝트 규칙을 만드세요.\n"
            "③ [폴더 선택 → 하네스 생성]으로 내려받아, 그 폴더에서 Claude Code를 실행하면 적용됩니다."
        )
        steps.setObjectName("muted")
        steps.setWordWrap(True)
        v.addWidget(steps)
        row = QHBoxLayout()
        row.addStretch(1)
        start = QPushButton("시작하기")
        start.setObjectName("primaryBtn")
        start.setCursor(Qt.CursorShape.PointingHandCursor)
        start.clicked.connect(dlg.accept)
        row.addWidget(start)
        rw = QWidget()
        rw.setLayout(row)
        v.addWidget(rw)
        dlg.exec()


def _load_app_font() -> str:
    """번들 Pretendard 우선 로드 → 패밀리명 반환. 실패 시 시스템 Malgun 폴백.

    Pretendard(번들)는 화면 최적화 한글 폰트로, Malgun 소형 크기에서 가로획 모음(ㅡㅜㅗ)이
    힌팅에 깎여 사라지던 글리프 드롭아웃('안전벨ㅌ' 현상)을 해소한다.
    """
    from PySide6.QtGui import QFontDatabase

    fonts_dir = Path(__file__).parent / "fonts"
    loaded: list[str] = []
    if fonts_dir.exists():
        for f in sorted(fonts_dir.glob("*.ttf")):
            loaded += QFontDatabase.applicationFontFamilies(
                QFontDatabase.addApplicationFont(str(f))
            )
    for fam in loaded:
        if "Pretendard" in fam:
            return fam
    # 폴백: 시스템 Malgun (번들 누락·로드 실패 시)
    mp = Path("C:/Windows/Fonts/malgun.ttf")
    if mp.exists():
        fams = QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(str(mp)))
        if fams:
            return fams[0]
    return loaded[0] if loaded else "Malgun Gothic"


def make_app():
    from PySide6.QtGui import QFont

    app = QApplication.instance() or QApplication([])
    # Fusion: 네이티브(windowsvista) 스타일은 QPushButton background-color 등 QSS를 무시 →
    # Fusion 으로 전환해 커스텀 테마 QSS 를 일관 적용(Apple풍 재디자인 기반).
    app.setStyle("Fusion")
    family = _load_app_font()
    font = QFont(family, 10)
    # 한글 가로획 모음 드롭아웃 방지: 풀힌팅이 소형에서 가는 획을 깎으므로 힌팅 끔 + 안티앨리어스.
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)
    win = BuilderWindow()
    return app, win


def main() -> None:
    app, win = make_app()
    win.show()
    win.maybe_show_welcome()
    app.exec()


if __name__ == "__main__":
    main()
