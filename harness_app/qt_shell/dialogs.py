"""BuilderWindow 부속 다이얼로그 — 환영/생성 완료/LLM 설정 (자기 상태 최소 인자화).

BuilderWindow 의 해당 메서드는 이 함수들에 위임하는 얇은 래퍼로 유지된다(R#8 분해).
"""

from __future__ import annotations

import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from harness_llm import credentials
from harness_llm.client import DEFAULT_MODEL, MODELS, anthropic_available

from ..guides import HARNESS_DEFINITION
from .widgets import make_btn


def show_welcome(parent) -> None:
    """도움말 다이얼로그 — 하네스 정의 + 사용 3단계."""
    dlg = QDialog(parent)
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
    start = make_btn("시작하기", "primaryBtn", dlg.accept)
    row.addWidget(start)
    rw = QWidget()
    rw.setLayout(row)
    v.addWidget(rw)
    dlg.exec()


def show_export_done(parent, dest: str, report, n_unedited_examples: int) -> None:
    """PM6-S6: 생성 후 '다음 단계' — 결과물을 손에 쥐고도 작동을 못 보던 갭을 닫는다."""
    dlg = QDialog(parent)
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
    if n_unedited_examples:
        warn = QLabel(
            f"편집하지 않은 예시 {n_unedited_examples}개가 그대로 포함됐어요 — 내 프로젝트에 맞는지 검토하거나 "
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
    # pushd: cmd 에서 드라이브 전환 포함(cd 는 /d 없인 드라이브 미전환), PowerShell 은
    # Push-Location 별칭으로 동일. 트레일링 개행 = 마지막 명령까지 자동 실행.
    cmd_text = f'pushd "{os.path.normpath(dest)}"\nclaude\n'
    copyb = make_btn(
        "이동+실행 명령 복사",
        "addBtn",
        lambda: QApplication.clipboard().setText(cmd_text),
        tip="터미널에 붙여넣으면 폴더 이동 후 Claude Code 가 실행됩니다 (cmd·PowerShell 공용)",
    )
    row.addWidget(copyb)
    openb = make_btn(
        "폴더 열기", "addBtn", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(dest))
    )
    row.addWidget(openb)
    row.addStretch(1)
    close = make_btn("닫기", "primaryBtn", dlg.accept)
    row.addWidget(close)
    rw = QWidget()
    rw.setLayout(row)
    v.addWidget(rw)
    dlg.exec()


def open_llm_settings(parent, settings) -> None:
    """LLM 설정(BYO 키) 다이얼로그 — 모델 선택 + API 키 저장/삭제(OS 자격증명관리자)."""
    dlg = QDialog(parent)
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
    model_cb.setCurrentText(settings.value("llm_model", DEFAULT_MODEL))
    v.addWidget(model_cb)
    v.addWidget(QLabel("Anthropic API 키"))
    key_le = QLineEdit()
    key_le.setEchoMode(QLineEdit.EchoMode.Password)
    key_le.setPlaceholderText(
        "(저장됨 — 변경 시에만 입력)" if credentials.has_api_key("anthropic") else "sk-ant-..."
    )
    v.addWidget(key_le)

    def do_save() -> None:
        settings.setValue("llm_model", model_cb.currentText())
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

    btns = QHBoxLayout()
    delete = make_btn("키 삭제", "addBtn", do_delete)
    close = make_btn("닫기", "addBtn", dlg.reject)
    save = make_btn("저장", "primaryBtn", do_save)
    btns.addWidget(delete)
    btns.addStretch(1)
    btns.addWidget(close)
    btns.addWidget(save)
    bw = QWidget()
    bw.setLayout(btns)
    v.addWidget(bw)
    dlg.exec()
