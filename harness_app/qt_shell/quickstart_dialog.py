"""30초 빠른 시작 다이얼로그 — 질문 3개(폴더·성향·보호)로 Lv4 하네스 (PM8 실험).

선택이 바뀔 때마다 예상 성숙도·차단 요약을 결정론으로 미리보기(vm.maturity 재사용, LLM 0회).
결과는 result_ir/result_dest 로 노출 — 적용(load_ir·생성)은 BuilderWindow 가 담당.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import view_model as vm
from ..detect import detect_project
from ..quickstart import PERSONAS, PROTECTIONS, build_quick_ir
from ..state import BuilderState
from .widgets import RuleToggle, make_btn


class QuickStartDialog(QDialog):
    def __init__(self, parent, tokens: dict, project_name: str = "my-project") -> None:
        super().__init__(parent)
        self._tokens = tokens
        self._project_name = project_name
        self._detected = None
        self._dest: str | None = None
        self._persona = PERSONAS[0][0]
        self._protections: set[str] = {k for k, _ in PROTECTIONS}
        self.result_ir = None
        self.result_dest: str | None = None

        self.setWindowTitle("30초 빠른 시작")
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.setSpacing(10)
        title = QLabel("질문 3개면 끝나요")
        title.setObjectName("h1")
        v.addWidget(title)

        # ① 폴더(선택) — 스택 자동 감지
        q1 = QLabel("① 프로젝트 폴더를 알려주면 스택을 자동으로 채워드려요 (건너뛰어도 돼요)")
        q1.setObjectName("landingH2")
        q1.setWordWrap(True)
        v.addWidget(q1)
        folder_row = QHBoxLayout()
        folder_row.addWidget(make_btn("폴더 선택", "addBtn", self._pick_folder))
        self._detect_lbl = QLabel("아직 선택 안 함")
        self._detect_lbl.setObjectName("faint")
        self._detect_lbl.setWordWrap(True)
        folder_row.addWidget(self._detect_lbl, 1)
        frw = QWidget()
        frw.setLayout(folder_row)
        v.addWidget(frw)

        # ② 성향(1클릭)
        q2 = QLabel("② AI에게 얼마나 맡길까요?")
        q2.setObjectName("landingH2")
        v.addWidget(q2)
        self._persona_group = QButtonGroup(self)
        self._persona_group.setExclusive(True)
        for key, label, _preset in PERSONAS:
            b = QPushButton(label)
            b.setObjectName("addBtn")
            b.setCheckable(True)
            b.setChecked(key == self._persona)
            b.clicked.connect(lambda _c=False, k=key: self._set_persona(k))
            self._persona_group.addButton(b)
            v.addWidget(b)

        # ③ 핵심 보호(기본 전부 켬)
        q3 = QLabel("③ 꼭 지킬 것 — 기본값 그대로가 가장 안전해요")
        q3.setObjectName("landingH2")
        v.addWidget(q3)
        for key, label in PROTECTIONS:
            v.addWidget(
                RuleToggle(label, True, tokens, lambda on, k=key: self._set_protection(k, on))
            )

        # 실시간 미리보기 — 해자(성숙도·시뮬)가 답의 결과를 즉시 증명
        self._preview = QLabel()
        self._preview.setObjectName("muted")
        self._preview.setWordWrap(True)
        v.addWidget(self._preview)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(make_btn("취소", "addBtn", self.reject))
        # 폴더 선택 시 '바로 생성'까지 — 부작용(파일 쓰기)을 버튼 라벨로 투명하게(비파괴 SKIP_EXISTING)
        self._make_btn_widget = make_btn("만들고 빌더에서 확인  →", "primaryBtn", self._confirm)
        row.addWidget(self._make_btn_widget)
        rw = QWidget()
        rw.setLayout(row)
        v.addWidget(rw)
        self._update_preview()

    # 입력 핸들러 ---
    def _pick_folder(self) -> None:
        dest = QFileDialog.getExistingDirectory(self, "프로젝트 폴더 선택")
        if not dest:
            return
        self._dest = dest
        self._detected = detect_project(dest)
        self._detect_lbl.setText(
            f"감지: {self._detected.summary()} (근거 {self._detected.evidence})"
            if self._detected
            else "스택을 감지하지 못했어요 — 만들고 나서 컨텍스트에 직접 적으면 돼요"
        )
        self._make_btn_widget.setText("만들고 이 폴더에 바로 생성  →")
        self._update_preview()

    def _set_persona(self, key: str) -> None:
        self._persona = key
        self._update_preview()

    def _set_protection(self, key: str, on: bool) -> None:
        (self._protections.add if on else self._protections.discard)(key)
        self._update_preview()

    # 미리보기·확정 ---
    def _build(self):
        return build_quick_ir(
            self._project_name, self._persona, frozenset(self._protections), self._detected
        )

    def _update_preview(self) -> None:
        ir = self._build()
        st = BuilderState(self._project_name)
        st.load_ir(ir)
        m = vm.maturity(st)
        blocked = [
            f"{r.label.replace(' 시도', '')}→{r.after_outcome}"
            for r in vm.sim_compare(st)
            if r.changed
        ]
        summary = " · ".join(blocked) if blocked else "차단 없음(모두 통과)"
        self._preview.setText(f"이대로 만들면: 성숙도 {m.label} · {summary}")
        self._preview.setToolTip(m.detail)

    def _confirm(self) -> None:
        self.result_ir = self._build()
        self.result_dest = self._dest
        self.accept()
