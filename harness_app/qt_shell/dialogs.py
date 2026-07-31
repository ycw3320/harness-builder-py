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
    dlg.setWindowTitle("버클 — 안내")
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
        "③ [폴더 선택 → 하네스 생성]으로 내려받아, 그 폴더에서 Claude Code를 실행하면 적용됩니다.\n"
        "· 항목의 ? 표시는 도움말이에요 — 마우스를 올리거나 클릭하면 쉬운 풀이가 나옵니다."
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


def show_export_done(
    parent,
    dest: str,
    report,
    n_unedited_examples: int,
    maturity_label: str = "",
    runtime=None,
) -> None:
    """PM6-S6: 생성 후 '다음 단계' — 결과물을 손에 쥐고도 작동을 못 보던 갭을 닫는다.

    1-C: runtime(HookRuntimeVM)이 실행기 부재를 알리면 ③ 문구를 단정에서 조건부로 강등한다
    (발견 B — bash 없는 Windows 에서 '실제로 적용됩니다'는 거짓 안전).
    """
    dlg = QDialog(parent)
    dlg.setWindowTitle("하네스 생성 완료 — 다음 단계")
    dlg.setMinimumWidth(520)
    v = QVBoxLayout(dlg)
    v.setSpacing(10)
    title = QLabel("하네스를 만들었어요. 이제 이렇게 쓰세요")
    title.setObjectName("h1")
    v.addWidget(title)
    badge = f" · 성숙도 {maturity_label}" if maturity_label else ""
    summary = QLabel(
        f"생성 {len(report.created)}개 · 건너뜀 {len(report.skipped)}개{badge}\n{dest}"
    )
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
    # ③ 문구: 훅 실행기가 이 PC 에 있을 때만 단정한다(1-C).
    missing_runtime = runtime is not None and not runtime.ok
    third = (
        "③ 이 PC 에는 훅 실행기가 없어, 방금 본 차단이 지금 상태로는 적용되지 않습니다"
        " — 아래 안내를 먼저 확인하세요."
        if missing_runtime
        else "③ 방금 시뮬레이터에서 본 차단(.env·강제 push)이 실제로 적용됩니다."
    )
    steps = QLabel(
        "① 이 폴더를 프로젝트 루트에 두세요(이미 프로젝트라면 그대로).\n"
        "② 그 폴더에서 Claude Code를 실행하세요 — 터미널에서 claude\n"
        "   터미널이 처음이라면: [폴더 열기] 후 폴더 창 주소칸에 cmd 입력 → 엔터 → 붙여넣기.\n"
        f"{third}"
    )
    steps.setObjectName("muted")
    steps.setWordWrap(True)
    v.addWidget(steps)
    if missing_runtime:
        rt = QLabel(
            f"훅 실행기 없음: {runtime.runtime_names}\n"
            f"영향받는 훅 {len(runtime.affected_titles)}개 — "
            + ", ".join(runtime.affected_titles[:3])
            + ("…" if len(runtime.affected_titles) > 3 else "")
            + ("\n" + runtime.notes[0] if runtime.notes else "")
        )
        rt.setObjectName("lintErr" if runtime.blocking_affected else "lintWarn")
        rt.setWordWrap(True)
        v.addWidget(rt)
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


def show_receive_review(parent, ir, findings: list[dict], compare) -> bool:
    """PM7-S2 수신 검증 — 받은/연 .harness.json 이 '무엇을 하는지'를 가져오기 전에 보여준다.

    해자의 두 번째 사용처: '만들 때 검증'에 이어 '받을 때 검증'(LLM 0회·오프라인).
    반환 True=가져오기 확정. findings=lint_ir 결과, compare=vm.sim_compare_ir 결과.
    """
    dlg = QDialog(parent)
    dlg.setWindowTitle("하네스 파일 확인 — 가져오기 전 검증")
    dlg.setMinimumWidth(560)
    v = QVBoxLayout(dlg)
    v.setSpacing(10)
    title = QLabel(f"이 하네스가 하는 일 — {ir.meta.project_name}")
    title.setObjectName("h1")
    v.addWidget(title)
    summary = QLabel(f"구성요소 {len(ir.components)}개 · 프리셋 기원: {ir.meta.preset}")
    summary.setObjectName("muted")
    v.addWidget(summary)

    # 실행 전 시뮬 — 받은 규칙이 실제로 무엇을 막는지
    for s in compare:
        line = QLabel(f"•  {s.label} → {s.after_outcome}")
        line.setObjectName("muted" if s.after_raw == "allowed" else "lintWarn")
        line.setWordWrap(True)
        v.addWidget(line)

    # lint 결과(상위 5)
    errors = [f for f in findings if f["level"] == "error"]
    warns = [f for f in findings if f["level"] != "error"]
    if not findings:
        ok = QLabel("정합성 검사: 문제 없음")
        ok.setObjectName("muted")
        v.addWidget(ok)
    for f in (errors + warns)[:5]:
        lbl = QLabel(f"[{f['code']}] {f['message']}")
        lbl.setObjectName("lintErr" if f["level"] == "error" else "lintWarn")
        lbl.setWordWrap(True)
        v.addWidget(lbl)

    caution = QLabel(
        "외부에서 받은 파일이라면: 가져온 뒤 가드레일의 hook 스크립트 본문을 한 번 확인하세요 — "
        "스크립트는 실행 코드입니다."
    )
    caution.setObjectName("faint")
    caution.setWordWrap(True)
    v.addWidget(caution)

    row = QHBoxLayout()
    row.addStretch(1)
    cancel = make_btn("취소", "addBtn", dlg.reject)
    accept = make_btn("가져오기(현재 작업 대체)", "primaryBtn", dlg.accept)
    row.addWidget(cancel)
    row.addWidget(accept)
    rw = QWidget()
    rw.setLayout(row)
    v.addWidget(rw)
    return dlg.exec() == QDialog.DialogCode.Accepted


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
