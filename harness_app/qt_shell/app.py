"""Qt 3-pane 셸 (S1~S6) — BuilderWindow 오케스트레이션 + 앱 부트스트랩.

공유 state·view_model 소비, 위젯 배선만 Qt 고유. R#8 분해: 테마 토큰·QSS 는 theme,
행 카드·소형 편집기·버튼 헬퍼는 widgets, 소개 화면은 landing, 부속 다이얼로그는 dialogs.
편집(콘텐츠 patch)은 우패널만 갱신, 구조 변경 시에만 중앙/좌측 재빌드(편집 포커스 보존).
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSettings, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from harness_core.export.assemble_project import assemble_project
from harness_core.ir.enforcement import promote
from harness_core.ir.migrate import dump_ir, load_ir_any
from harness_core.ir.registry import addable_kinds_by_layer, kind_registry
from harness_core.lint.lint import lint_ir
from harness_fs.importer import import_project
from harness_fs.policy import MergeStrategy
from harness_fs.writer import write_tree
from harness_llm import credentials
from harness_llm.client import DEFAULT_MODEL, AnthropicClient, LLMError, anthropic_available

from .. import view_model as vm
from ..guides import HARNESS_AHA, HARNESS_DEFINITION, LAYER_FLOW_CAPTION, layer_order
from ..state import BuilderState
from .dialogs import open_llm_settings, show_export_done, show_receive_review, show_welcome

# 하위호환 re-export — 기존 import 경로(tests 포함) 보존. R#8 분해로 실제 정의는 각 모듈.
from .landing import LandingPage
from .theme import DARK, FONT_STACK, LIGHT, THEMES, build_palette, build_qss  # noqa: F401
from .widgets import (  # noqa: F401
    _TITLE_FIELD,
    ClickableLabel,
    DictEditor,
    ListEditor,
    RowWidget,
    RuleToggle,
    _dot,
    brand_pixmap,
    make_btn,
)

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
        # 제품명은 '버클' 단독(사용자 확정) — 기능 수식어는 랜딩 태그라인 등 부제 자리에만.
        self.setWindowTitle("버클")
        self.setWindowIcon(_brand_icon())  # 작업표시줄·트레이 공용 브랜드 마크
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

        # 랜딩(소개) → [30초 빠른 시작]/[직접 조립] → 빌더(3-pane). QStackedWidget 로 전환.
        self._stack = QStackedWidget()
        self._stack.addWidget(LandingPage(self._enter_builder, self._open_quickstart))  # index 0
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
        self._init_tray()

    def _enter_builder(self) -> None:
        self._settings.setValue("landing_seen", True)
        self._stack.setCurrentIndex(1)

    def load_external_ir(self, ir) -> None:
        """외부에서 인식한 IR 을 빌더로 — 사용자의 실제 설정이므로 '예시' 아님(공용 진입점)."""
        self._example_ids = set()
        self.state.load_ir(ir)
        self._enter_builder()

    # PM9 실험: 라이브 관측 — 비모달 창 1개 재사용(닫아도 인스턴스 유지) ---
    def _open_live(self) -> None:
        from .live_dialog import LiveObserveDialog  # 지연 import

        if getattr(self, "_live_dlg", None) is None:
            self._live_dlg = LiveObserveDialog(self, self.state)
        self._live_dlg.show()
        self._live_dlg.raise_()

    # PM8 실험: 30초 빠른 시작 — 질문 3개 → 검증된 IR → (선택) 즉시 폴더 생성 ---
    def _open_quickstart(self) -> None:
        from .quickstart_dialog import QuickStartDialog  # 지연 import(시작 비용 절감)

        dlg = QuickStartDialog(self, self.tokens, self.state.ir.meta.project_name)
        # exec() 반환: Accepted=1 / Rejected=0 — truthiness 로 판정(QDialog 재import 회피)
        if dlg.exec() and dlg.result_ir is not None:
            self._apply_quickstart(dlg.result_ir, dlg.result_dest)

    def _apply_quickstart(self, ir, dest: str | None) -> None:
        """빠른 시작 결과 적용 — 사용자가 답해 만든 구성이므로 '예시' 아님."""
        self._example_ids = set()
        self.state.load_ir(ir)
        self._enter_builder()
        if dest:  # 폴더를 골랐다면 바로 생성까지(최소 입력의 완결)
            tree = assemble_project(self.state.ir, self.state.scaffold)
            report = write_tree(tree, Path(dest), strategy=MergeStrategy.SKIP_EXISTING)
            self._show_export_done(dest, report)

    # 1-A: 미리보기 — 생성될 산출물 실제 텍스트 + '언제 적용되나'(모달) ---
    def _open_preview(self) -> None:
        from .preview_dialog import PreviewDialog  # 지연 import

        PreviewDialog(self, self.state).exec()

    def _show_landing(self) -> None:
        self._stack.setCurrentIndex(0)

    # 트레이 — X 로 닫으면 종료 대신 백그라운드(라이브 관측 유지), 우클릭 메뉴로 종료 ---
    def _init_tray(self) -> None:
        self._tray: QSystemTrayIcon | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return  # 트레이 없는 환경(offscreen·일부 원격 셸)은 기존 동작(X=종료) 유지
        tray = QSystemTrayIcon(self.windowIcon(), self)
        tray.setToolTip("버클")
        menu = QMenu()
        menu.addAction("열기", self._restore_from_tray)
        menu.addSeparator()
        menu.addAction("종료", self._quit_from_tray)
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self._tray = tray
        self._tray_menu = menu  # 참조 유지(GC 방지)
        # 트레이 사용 중엔 마지막 창이 닫혀도 앱 유지 — 종료 결정은 트레이 메뉴가 담당.
        # (메인 창이 숨은 상태에서 다이얼로그 하나 닫히면 앱이 통째로 꺼지던 것 방지)
        QApplication.instance().setQuitOnLastWindowClosed(False)

    def _on_tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        if self._tray is not None:
            self._tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, ev) -> None:  # noqa: N802 (Qt 가상함수명)
        if getattr(self, "_tray", None) is not None and self._tray.isVisible():
            ev.ignore()
            self.hide()
            if not self._settings.value("tray_hint_seen", False, type=bool):
                self._settings.setValue("tray_hint_seen", True)
                self._tray.showMessage(
                    "버클은 백그라운드에서 계속 실행 중",
                    "트레이 아이콘 클릭 = 다시 열기, 우클릭 → 종료 = 완전히 끄기.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )
            return
        super().closeEvent(ev)

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
        app = QApplication.instance()
        # 팔레트를 테마와 일치 → QSS 미지정 폴백(QDialog 배경·아이템뷰 등)이 라이트로 남는
        # 문제 근절. 그 위에 QSS 를 얹어 세부 스타일 지정(버튼/콤보 배경 등 polish 보장).
        app.setPalette(build_palette(self.tokens))
        app.setStyleSheet(build_qss(self.tokens))

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

        # 테마 토글 — 좌하단 '설정 코너'(데스크톱 관례). 환경 설정을 기능 버튼 줄(우패널
        # head: 소개·미리보기·라이브 관측·도움말·LLM)과 분리해 과밀 해소.
        theme_row = QHBoxLayout()
        theme_lbl = QLabel("테마")
        theme_lbl.setObjectName("faint")
        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self._theme_toggle())
        theme_row.addStretch(1)
        tw = QWidget()
        tw.setLayout(theme_row)
        v.addWidget(tw)

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
        # LLM 'AI 채우기' UI 보류(사용자 결정) — 기능 확장 시 아래 한 줄로 복원:
        #   fill = self._llm_fill_component if self._llm_ready() else None
        # (harness_llm 패키지·_llm_fill_component·_llm_ready·_open_settings 는 휴면 보존)
        fill = None
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
            b = make_btn(
                f"+ {kind_registry[kind]['label']}",
                "addBtn",
                lambda _checked, k=kind: self.state.add_component(k),
            )
            lay.addWidget(b)
        lay.addStretch(1)
        if any(not e["basic"] for e in all_entries):
            adv = make_btn(
                "고급", "segBtn", lambda: self.state.set_advanced_mode(not self.state.advanced_mode)
            )
            adv.setCheckable(True)
            adv.setChecked(self.state.advanced_mode)
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
        intro = make_btn("소개", "addBtn", self._show_landing, tip="소개 화면 다시 보기")
        head.addWidget(intro)
        preview = make_btn(
            "미리보기",
            "addBtn",
            self._open_preview,
            tip="생성될 CLAUDE.md·설정 파일의 실제 내용과 각 규칙이 언제 적용되는지 확인",
        )
        head.addWidget(preview)
        live = make_btn(
            "라이브 관측",
            "addBtn",
            self._open_live,
            tip="Claude Code 세션이 하네스의 어느 규칙을 지나는지 실시간 확인(실험)",
        )
        head.addWidget(live)
        helpb = make_btn("도움말", "addBtn", self._show_welcome)
        head.addWidget(helpb)
        # [LLM 설정] 버튼 보류(사용자 결정) — AI 채우기 확장 시 복원(_open_settings 휴면 유지):
        #   head.addWidget(make_btn("LLM 설정", "addBtn", self._open_settings))
        head_w = QWidget()
        head_w.setLayout(head)
        v.addWidget(head_w)

        # 성숙도(질) + 완성도 미터(양) + 다음 추천 영역 (§0.6 → PM7-S4 질적 진화)
        comp = vm.completion(self.state)
        mat = vm.maturity(self.state)
        sect = self._section(f"성숙도 {mat.label} · 구성 {comp.filled}/{comp.total}")
        sect.setToolTip(mat.detail)  # 산식 공개 — 게임화 역효과 통제
        v.addWidget(sect)
        meter = QProgressBar()
        meter.setObjectName("meter")
        meter.setRange(0, 100)
        meter.setValue(comp.percent)
        meter.setTextVisible(False)
        meter.setFixedHeight(8)
        v.addWidget(meter)
        if mat.next_hint:
            mh = QLabel(f"다음 레벨: {mat.next_hint}")
            mh.setObjectName("faint")
            mh.setWordWrap(True)
            mh.setToolTip(mat.detail)
            v.addWidget(mh)
        if comp.next_layer:
            nxt = make_btn(
                f"다음 추천 영역: {comp.next_label} →",
                "addBtn",
                lambda _c=False, ly=comp.next_layer: self.state.set_selected_layer(ly),
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
        # PM7-S2: 통합 .harness.json — 작업 저장(앱 끄면 소실 해소)=공유(팀 표준 전달) 단일 포맷
        filerow = QHBoxLayout()
        filerow.addWidget(
            make_btn(
                "파일로 저장",
                "addBtn",
                self._on_save_file,
                tip="현재 작업 전체를 .harness.json 하나로 저장 — 그대로 공유할 수 있어요",
            )
        )
        filerow.addWidget(
            make_btn(
                "파일 열기",
                "addBtn",
                self._on_open_file,
                tip="받은/저장한 .harness.json 을 '무엇을 하는지' 확인 후 가져오기",
            )
        )
        filerow.addStretch(1)
        frw = QWidget()
        frw.setLayout(filerow)
        v.addWidget(frw)
        imp = make_btn("기존 폴더 가져오기", "addBtn", self._on_import)
        v.addWidget(imp)
        combo = QComboBox()
        combo.addItems(["minimal", "harness-only"])
        combo.setCurrentText(self.state.scaffold)
        combo.currentTextChanged.connect(self.state.set_scaffold)
        v.addWidget(combo)
        btn = make_btn("폴더 선택 → 하네스 생성", "primaryBtn", self._on_export)
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
            b = make_btn(label, "segBtn", lambda _checked, k=key: self.set_theme(k))
            b.setCheckable(True)
            b.setChecked(self.theme_name == key)
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
        # 미편집 '예시' 수는 윈도 상태(_example_ids)로만 계산 가능 — 여기서 세어 인자로 전달(R#8).
        n_ex = sum(1 for c in self.state.ir.components if c.enabled and c.id in self._example_ids)
        show_export_done(self, dest, report, n_ex, maturity_label=vm.maturity(self.state).label)

    # PM7-S2: 통합 .harness.json 저장/열기 ---
    def _on_save_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "하네스 파일로 저장",
            f"{self.state.ir.meta.project_name}.harness.json",
            "하네스 파일 (*.harness.json)",
        )
        if not path:
            return
        Path(path).write_text(dump_ir(self.state.ir), encoding="utf-8", newline="\n")
        QMessageBox.information(
            self, "저장 완료", f"{path}\n이 파일 하나로 작업 이어가기·팀 공유가 가능합니다."
        )

    def _on_open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "하네스 파일 열기", "", "하네스 파일 (*.harness.json);;JSON (*.json)"
        )
        if not path:
            return
        try:
            ir = load_ir_any(Path(path).read_text(encoding="utf-8"))
        except Exception as e:
            QMessageBox.warning(self, "열기 실패", str(e))
            return
        # 수신 검증(해자의 두 번째 사용처): 가져오기 전에 '무엇을 하는지' 결정론으로 보여줌
        findings = lint_ir(ir, rulesets=("core", "security"))
        if show_receive_review(self, ir, findings, vm.sim_compare_ir(ir)):
            self._example_ids = set()  # 파일에서 온 구성은 예시 아님 — load_ir 통지 이전 클리어
            self.state.load_ir(ir)

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
        open_llm_settings(self, self._settings)
        self._force_rebuild()  # 키 변경 반영(AI 버튼 활성/비활성)

    # 온보딩 (PM5) — 첫 실행 환영 + 도움말 ---
    def maybe_show_welcome(self) -> None:
        # PM6-S4: 첫 실행에 텍스트 벽 모달 없음 — 곧장 before/after 대비로 '체감 먼저'.
        # 정의는 사용자가 규칙을 꺼본 직후(아하) 우패널에 페이드인된다. 도움말 버튼은 _show_welcome.
        pass

    def _show_welcome(self) -> None:
        show_welcome(self)


def _brand_icon() -> QIcon:
    """버클 브랜드 아이콘 — 작업표시줄·트레이 공용, 크기별 재드로잉으로 전 해상도 선명.

    드로잉 단일 소스는 widgets.brand_pixmap (랜딩 히어로·exe .ico 생성과 공유).
    """
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(brand_pixmap(s))
    return icon


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
