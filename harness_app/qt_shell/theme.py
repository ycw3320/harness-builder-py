"""테마 토큰·QSS 단일 소스 — Apple 미니멀(라이트 크림 ↔ 다크 Space Gray).

LIGHT/DARK dict 에서 build_qss 로 주입, 토글은 QApplication 스타일시트 런타임 스왑
(재시작 불필요·QSettings persist).
"""

from __future__ import annotations

from string import Template

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
