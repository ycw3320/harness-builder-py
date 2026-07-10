"""미리보기 다이얼로그(1-A) — 생성될 하네스 산출물의 실제 텍스트 + 각 규칙이 '언제' 적용되나.

발견 C 대응: prose/CLAUDE.md 는 시뮬 효과가 0이라 지침만 쓴 초심자는 빈 시뮬 화면을 봤다.
여기서 assemble 된 실제 파일 내용을 그대로 보여주고(맥락=항상 주입, 규칙=조건부 발동을 정직히 라벨),
'export 하면 무엇이 만들어지나'를 조립 중에 확인하게 한다. 읽기 전용·결정론·LLM 0회.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import view_model as vm
from .widgets import make_btn


def _role_for(path: str) -> str:
    """'이 파일이 하는 일' 한 줄 설명(초심자 교육) — 맥락/규칙/역할 구분을 심는다."""
    p = path.replace("\\", "/")
    if p.endswith("CLAUDE.md"):
        return "Claude 가 매 요청마다 항상 읽는 맥락(지침)."
    if p.endswith("settings.json"):
        return "권한(allow/ask/deny)과 hook 을 정의하는 설정."
    if p.endswith(".mcp.json"):
        return "외부 도구(MCP 서버) 연결 정의."
    if "/hooks/" in p:
        return "이벤트 발동 시 실행되는 차단·검사 스크립트."
    if "/agents/" in p:
        return "특정 작업에 위임되는 서브에이전트 역할 정의."
    if "/rules/" in p:
        return "참고 규칙 문서 — Claude 가 자동 로드하진 않음(수동 참조)."
    if p.endswith(".env.example"):
        return "MCP 가 참조하는 환경변수 목록(실제 값 아님)."
    return "프로젝트 스캐폴드 파일."


class PreviewDialog(QDialog):
    """생성될 산출물 미리보기 — 파일 목록+실제 내용 + '언제 적용되나' 타이밍 뷰(모달, 읽기 전용)."""

    def __init__(self, parent, state) -> None:
        super().__init__(parent)
        self.setWindowTitle("미리보기 — 생성될 하네스 산출물")
        self.setMinimumSize(800, 600)
        self._files = vm.assembled_files(state)

        v = QVBoxLayout(self)
        v.setSpacing(8)
        intro = QLabel(
            "export 하면 아래 파일들이 프로젝트 폴더에 생성됩니다. 왼쪽에서 파일을 고르면 실제 내용이 "
            "보입니다. (읽기 전용 미리보기 — 결정론, 외부 호출 없음)"
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        v.addWidget(intro)

        # 파일 목록 + 내용 --------------------------------------------------
        row = QHBoxLayout()
        self._list = QListWidget()
        self._list.setMaximumWidth(260)
        # 긴 경로는 가로 스크롤바 대신 중간 말줄임(파일명 보존) + 전체경로 툴팁.
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        for path, _ in self._files:
            item = QListWidgetItem(path)
            item.setToolTip(path)
            self._list.addItem(item)
        row.addWidget(self._list)

        right = QVBoxLayout()
        self._role = QLabel("")
        self._role.setObjectName("faint")
        self._role.setWordWrap(True)
        right.addWidget(self._role)
        self._content = QPlainTextEdit()
        self._content.setReadOnly(True)
        self._content.setFont(QFont("Consolas", 10))
        self._content.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        right.addWidget(self._content, 1)
        rw = QWidget()
        rw.setLayout(right)
        row.addWidget(rw, 1)
        roww = QWidget()
        roww.setLayout(row)
        v.addWidget(roww, 1)

        # '언제 적용되나' — 규칙 타이밍(정직: prose=항상, hook/permission=조건부, policy=수동참조)
        when_lbl = QLabel("각 규칙이 언제 적용되나")
        when_lbl.setObjectName("section")
        v.addWidget(when_lbl)
        self._when = QListWidget()
        self._when.setMaximumHeight(150)
        for a in vm.applicability(state):
            mark = "상시" if a.always_on else "조건부"
            self._when.addItem(f"[{mark}]  {a.title} — {a.when}")
        v.addWidget(self._when)

        close = make_btn("닫기", "addBtn", self.accept)
        v.addWidget(close)

        self._list.currentRowChanged.connect(self._show)
        # 기본 선택: 프로젝트 CLAUDE.md 우선(발견 C 핵심 — _APPLY/global 병합용은 제외), 없으면 첫 파일.
        idx = next(
            (
                i
                for i, (p, _) in enumerate(self._files)
                if p.replace("\\", "/").endswith("CLAUDE.md") and "_APPLY" not in p
            ),
            0 if self._files else -1,
        )
        if idx >= 0:
            self._list.setCurrentRow(idx)

    def _show(self, row: int) -> None:
        if 0 <= row < len(self._files):
            path, content = self._files[row]
            self._role.setText(f"{path} — {_role_for(path)}")
            self._content.setPlainText(content)
