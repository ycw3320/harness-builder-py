"""테마 토큰·QSS 단일 소스 — Apple 미니멀(라이트 크림 ↔ 다크 Space Gray).

LIGHT/DARK dict 에서 build_qss 로 주입, 토글은 QApplication 스타일시트 런타임 스왑
(재시작 불필요·QSettings persist).
"""

from __future__ import annotations

from string import Template

from PySide6.QtGui import QColor, QPalette

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
    "accent": "#B85A38",  # Claude 테라코타(딥) — 흰글씨 버튼 4.6:1·크림 위 텍스트 4.5:1(WCAG AA)
    "accent_hover": "#A5482A",
    "on_accent": "#FFFFFF",
    "selected_bg": "#F5E4DC",  # 소프트 피치 틴트(선택 행·아하 카드)
    "danger": "#C9362B",
    "warn": "#B26A00",
    "ok": "#177C3D",
    # 결정방식 3색 — 파랑(추천) 제거하고 따뜻한 심각도 램프(녹→금→러스트)로. Claude 팔레트
    # 통일(차가운 파랑이 테라코타와 섞여 보이던 문제 해소) + 신호등식 의미(자유→추천→직접승인).
    "involvement_auto": "#177C3D",
    "involvement_assisted": "#96640F",
    "involvement_manual": "#BC4A2C",
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
    "accent": "#CF6D4E",  # Claude 테라코타(밝게) — 다크배경 위 텍스트 4.8:1(WCAG AA)
    "accent_hover": "#E0785C",
    "on_accent": "#FFFFFF",
    "selected_bg": "#3A281F",  # 뮤트 테라코타 다크 틴트
    "danger": "#FF6961",
    "warn": "#FFB340",
    "ok": "#30D158",
    "involvement_auto": "#30D158",
    "involvement_assisted": "#E0A93A",
    "involvement_manual": "#F0663A",
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

/* 3택1 선택 버튼(퀵스타트 성향 등) — 선택 상태를 틴트+accent 로 명시(RuleToggle 체크와 동일 문법) */
QPushButton#choiceBtn {
    background: $surface_alt; color: $text; border: 1px solid $border;
    border-radius: 7px; padding: 8px 12px; font-size: 12px; font-weight: 600;
}
QPushButton#choiceBtn:hover { border: 1px solid $accent; }
QPushButton#choiceBtn:checked {
    background: $selected_bg; border: 1px solid $accent; color: $accent;
}

QFrame#guideBox { background: $surface_alt; border: 1px solid $border; border-radius: 8px; }
QFrame#ahaCard { background: $selected_bg; border: 1px solid $accent; border-radius: 10px; }

QLabel#helpChip {
    background: $surface_alt; color: $text_muted; border: 1px solid $border;
    border-radius: 8px; padding: 0px 6px; font-size: 10px; font-weight: 700;
}
QLabel#helpChip:hover { border: 1px solid $accent; color: $accent; }

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
QListWidget::item { margin: 2px 4px; border-radius: 8px; color: $text; }
QListWidget::item:selected { background: $selected_bg; color: $text; }

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


# QSS 가 색을 지정하지 않는 위젯·상태는 팔레트로 폴백한다. 팔레트를 테마와 맞추지 않으면
# 라이트 기본 팔레트가 남아, QDialog 배경(QSS 규칙 없음)이 밝은 회색으로 뜨고 그 위에
# `* { color: $text }` 로 칠한 밝은 글씨가 묻혀 사라진다(다크 테마 QuickStart 라벨 실종의 근본 원인).
# QSS 는 팔레트 위에 얹혀 '지정한 부분만' 덮으므로 기존 스타일과 충돌하지 않는다.
_PALETTE_ROLES = {
    QPalette.ColorRole.Window: "bg",
    QPalette.ColorRole.WindowText: "text",
    QPalette.ColorRole.Base: "surface",
    QPalette.ColorRole.AlternateBase: "surface_alt",
    QPalette.ColorRole.Text: "text",
    QPalette.ColorRole.Button: "surface",
    QPalette.ColorRole.ButtonText: "text",
    QPalette.ColorRole.ToolTipBase: "surface",
    QPalette.ColorRole.ToolTipText: "text",
    QPalette.ColorRole.PlaceholderText: "text_faint",
    QPalette.ColorRole.Highlight: "accent",
    QPalette.ColorRole.HighlightedText: "on_accent",
    QPalette.ColorRole.Link: "accent",
}


def build_palette(tokens: dict) -> QPalette:
    """테마 토큰 → QPalette (QSS 미지정 폴백을 테마색과 일치시켜 다크 대비 붕괴 근절)."""
    pal = QPalette()
    for role, key in _PALETTE_ROLES.items():
        pal.setColor(role, QColor(tokens[key]))
        # 비활성(창 비포커스) 그룹도 동일색 — 아이템뷰가 흐려지는 것 방지.
        pal.setColor(QPalette.ColorGroup.Inactive, role, QColor(tokens[key]))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor(tokens["text_faint"]))
    return pal


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"
