"""라이브 관측 창(PM9-P1, 비모달) — Claude Code 세션의 하네스 여정을 실시간 타임라인으로.

폴더 선택 → [관측 켜기] → QTimer tail(hb-live.jsonl) → 이벤트를 결정론 매핑으로 해석해 표시.
매칭 문구는 '앱의 현재 구성 기준 재현'(실제 판정 주체는 Claude Code) — 헤더에 명시.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..observe import LIVE_LOG, describe_event, install_observer, parse_live_line, remove_observer
from .widgets import make_btn

_MAX_ROWS = 300


class LiveObserveDialog(QDialog):
    """비모달 관측 창 — BuilderWindow.state 를 참조해 현재 구성 기준으로 매칭 표시."""

    def __init__(self, parent, state) -> None:
        super().__init__(parent)
        self._state = state
        self._root: Path | None = None
        self._pos = 0  # tail 오프셋
        self.setWindowTitle("라이브 관측 (실험) — 하네스 여정")
        self.setMinimumSize(640, 420)
        v = QVBoxLayout(self)
        v.setSpacing(8)

        intro = QLabel(
            "Claude Code 가 일하는 동안 어느 규칙 카드를 지나는지 실시간으로 보여줍니다. "
            "매칭 표시는 이 앱의 현재 구성 기준 재현이며, 실제 판정은 Claude Code 가 합니다."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        v.addWidget(intro)

        row = QHBoxLayout()
        row.addWidget(make_btn("프로젝트 폴더 선택", "addBtn", self._pick))
        self._root_lbl = QLabel("아직 선택 안 함 — 하네스를 생성한 폴더를 고르세요")
        self._root_lbl.setObjectName("faint")
        self._root_lbl.setWordWrap(True)
        row.addWidget(self._root_lbl, 1)
        rw = QWidget()
        rw.setLayout(row)
        v.addWidget(rw)

        btns = QHBoxLayout()
        self._on_btn = make_btn(
            "관측 켜기(훅 설치)",
            "primaryBtn",
            self._install,
            tip="settings.local.json 에만 등록 — 팀 하네스 무영향",
        )
        self._on_btn.setEnabled(False)
        btns.addWidget(self._on_btn)
        self._off_btn = make_btn("관측 끄기", "addBtn", self._remove)
        self._off_btn.setEnabled(False)
        btns.addWidget(self._off_btn)
        btns.addWidget(make_btn("타임라인 비우기", "addBtn", self._clear))
        btns.addStretch(1)
        bw = QWidget()
        bw.setLayout(btns)
        v.addWidget(bw)

        self._status = QLabel("")
        self._status.setObjectName("faint")
        self._status.setWordWrap(True)
        v.addWidget(self._status)

        self._timeline = QListWidget()
        self._timeline.setWordWrap(True)
        v.addWidget(self._timeline, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(700)
        self._timer.timeout.connect(self._poll)

    # 조작 ---
    def _pick(self) -> None:
        dest = QFileDialog.getExistingDirectory(self, "관측할 프로젝트 폴더(.claude 포함) 선택")
        if not dest:
            return
        self.set_root(dest)

    def set_root(self, dest: str) -> None:
        """폴더 지정(테스트에서도 사용) — tail 리셋 후 감시 시작."""
        self._root = Path(dest)
        self._root_lbl.setText(str(self._root))
        self._on_btn.setEnabled(True)
        self._off_btn.setEnabled(True)
        self._pos = 0
        self._timeline.clear()
        self._timer.start()
        log = self._root / LIVE_LOG
        self._status.setText(
            "기록 감시 중 — 이 폴더에서 Claude Code 세션을 시작하세요."
            if log.exists()
            else "아직 기록 없음 — [관측 켜기] 후 이 폴더에서 Claude Code 세션을 시작하세요."
        )

    def _install(self) -> None:
        if self._root is None:
            return
        self._status.setText(install_observer(str(self._root)))

    def _remove(self) -> None:
        if self._root is None:
            return
        self._status.setText(remove_observer(str(self._root)))

    def _clear(self) -> None:
        self._timeline.clear()

    # tail ---
    def _poll(self) -> None:
        if self._root is None:
            return
        log = self._root / LIVE_LOG
        if not log.exists():
            return
        try:
            size = log.stat().st_size
            if size < self._pos:  # 로그가 비워짐(재시작 등) — 처음부터
                self._pos = 0
            if size == self._pos:
                return
            with open(log, encoding="utf-8-sig", errors="replace") as f:
                f.seek(self._pos)
                chunk = f.read()
                self._pos = f.tell()
        except OSError:
            return
        for line in chunk.splitlines():
            line = line.strip()
            if not line:
                continue
            ev = parse_live_line(line)
            if ev is None:
                continue
            text, comp_id = describe_event(self._state.ir, ev)
            ts = ev.ts[11:19] if len(ev.ts) >= 19 else ""
            item = QListWidgetItem(f"{ts}  {text}")
            if comp_id:  # 규칙 카드에 걸린 이벤트 강조
                item.setData(Qt.ItemDataRole.UserRole, comp_id)
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self._timeline.addItem(item)
        while self._timeline.count() > _MAX_ROWS:
            self._timeline.takeItem(0)
        self._timeline.scrollToBottom()

    def closeEvent(self, ev) -> None:  # noqa: N802 (Qt 가상함수명)
        self._timer.stop()
        super().closeEvent(ev)
