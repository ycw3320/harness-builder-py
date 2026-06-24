"""Flet 3-pane 셸 (S1~S6). 공유 state·view_model 소비, 위젯 배선만 Flet 고유.

S1 3-pane(Row+VerticalDivider) · S2 nav(context만 실동작+색점) · S3 행 펼침(animate)
· S4 편집→patch→우측 라이브 갱신 · S5 우패널(시뮬·lint·export) · S6 폴더쓰기(write_tree).

주: flet 0.85 신형 API — border/padding 헬퍼 제거, 비동기 다이얼로그(await get_directory_path).
"""

from __future__ import annotations

import os

import flet as ft

from harness_core.export.assemble_project import assemble_project
from harness_fs.policy import MergeStrategy
from harness_fs.writer import write_tree

from .. import view_model as vm
from ..state import BuilderState

ACCENT = "#0969da"
BG = "#ffffff"
PANEL = "#f6f8fa"
TEXT = "#1f2328"
MUTED = "#656d76"


def _dot(color: str, size: int = 10) -> ft.Container:
    return ft.Container(width=size, height=size, bgcolor=color, border_radius=size / 2)


def _section(text: str) -> ft.Text:
    return ft.Text(text.upper(), size=11, weight=ft.FontWeight.W_600, color=MUTED)


def main(page: ft.Page) -> None:
    state = BuilderState("my-project")
    page.title = "하네스 빌더 — 실행 전 시뮬레이터형 (Flet 프로토타입)"
    page.padding = 0
    page.bgcolor = PANEL
    page.window.width = 1160
    page.window.height = 700

    file_picker = ft.FilePicker()
    page.services.append(file_picker)  # flet 0.85: FilePicker 는 Service (overlay 아님)

    async def on_generate(e: ft.ControlEvent) -> None:
        path = await file_picker.get_directory_path("하네스를 생성할 폴더 선택")
        if not path:
            return
        tree = assemble_project(state.ir, state.scaffold)
        report = write_tree(tree, path, strategy=MergeStrategy.SKIP_EXISTING)
        bar = ft.SnackBar(
            ft.Text(f"생성 {len(report.created)}개 · 건너뜀 {len(report.skipped)}개 — {path}")
        )
        bar.open = True
        page.overlay.append(bar)
        page.update()

    # 좌 nav (S2) ---
    def build_nav() -> ft.Column:
        cells = []
        for item in vm.nav_items(state):
            body = ft.Row(
                [
                    _dot(item.dot_color),
                    ft.Column(
                        [
                            ft.Text(
                                f"{item.label}  ({item.count})",
                                weight=ft.FontWeight.W_600,
                                color=TEXT if item.interactive else "#afb8c1",
                            ),
                            ft.Text(item.hint, size=11, color=MUTED),
                        ],
                        spacing=0,
                    ),
                ],
                spacing=8,
            )
            cells.append(
                ft.Container(
                    content=body,
                    padding=8,
                    border_radius=6,
                    bgcolor="#ddf4ff" if item.selected else None,
                    on_click=(lambda e, ly=item.layer: state.set_selected_layer(ly))
                    if item.interactive
                    else None,
                )
            )
        return ft.Column(
            [
                ft.Text("구성 영역", size=15, weight=ft.FontWeight.W_600),
                ft.Text("6계층을 차례로 채우면 하네스가 완성됩니다.", size=12, color=MUTED),
                ft.Container(height=6),
                *cells,
            ],
            spacing=4,
        )

    # 행 펼침 (S3/S4) ---
    def build_row(r: vm.RowVM) -> ft.Container:
        opened = {"v": False}
        heading = ft.TextField(
            value=r.heading or "",
            hint_text="섹션 제목",
            on_change=lambda e: state.patch(r.id, {"heading": e.control.value}),
            dense=True,
        )
        body = ft.TextField(
            value=r.body or "",
            hint_text="외부 LLM 답변을 여기에 붙여넣으세요…",
            on_change=lambda e: state.patch(r.id, {"body": e.control.value}),
            multiline=True,
            min_lines=3,
            max_lines=5,
        )
        editor = ft.Column([heading, body], spacing=6, visible=False)

        def toggle(e: ft.ControlEvent) -> None:
            opened["v"] = not opened["v"]
            editor.visible = opened["v"]
            page.update()

        header = ft.Row(
            [
                _dot(r.color),
                ft.Container(
                    ft.Text(r.title, weight=ft.FontWeight.W_600), on_click=toggle, expand=True
                ),
                ft.Container(
                    ft.Text(r.involvement_label, size=11, color="white"),
                    bgcolor=r.color,
                    border_radius=9,
                    padding=ft.Padding(left=8, top=2, right=8, bottom=2),
                ),
                ft.Text(r.kind, size=11, color=MUTED),
            ],
            spacing=8,
        )
        return ft.Container(
            content=ft.Column([header, editor], spacing=8),
            padding=12,
            border_radius=8,
            bgcolor=BG,
            animate=160,
        )

    # 중앙 (S3) ---
    def build_center() -> ft.Column:
        intro = vm.layer_intro(state)
        card = ft.Container(
            ft.Column(
                [
                    ft.Text(vm.layer_meta_label(state), size=15, weight=ft.FontWeight.W_600),
                    ft.Text(intro["what"]),
                    ft.Text(f"최소 할 일 · {intro['minimum']}", size=12, color=MUTED),
                ],
                spacing=4,
            ),
            padding=14,
            border_radius=8,
            bgcolor=BG,
        )
        rows = [build_row(r) for r in vm.rows_for_selected(state)]
        return ft.Column([card, *rows], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

    # 우 패널 (S5/S6) ---
    def build_right() -> ft.Column:
        sims = [ft.Text(f"•  {s.label}  →  {s.outcome}", size=12) for s in vm.sim_items(state)]
        lints = vm.lint_items(state)
        if lints:
            lint_ctrls = [
                ft.Text(
                    f"[{li.code}] {li.message}",
                    size=12,
                    color="#cf222e" if li.level == "error" else "#9a6700",
                )
                for li in lints
            ]
        else:
            lint_ctrls = [ft.Text("문제 없음 — 내보낼 준비 완료", size=12, color=MUTED)]
        files = [ft.Text(p, size=12, color=MUTED) for p in vm.export_paths(state)[:8]]
        scaffold = ft.Dropdown(
            value=state.scaffold,
            options=[ft.dropdown.Option("minimal"), ft.dropdown.Option("harness-only")],
            dense=True,
        )
        scaffold.on_change = lambda e: state.set_scaffold(e.control.value)
        gen = ft.ElevatedButton(
            "폴더 선택 → 하네스 생성", bgcolor=ACCENT, color="white", on_click=on_generate
        )
        return ft.Column(
            [
                _section("라이브 시뮬레이터 · LLM 0회"),
                *sims,
                _section("정합성 검사"),
                *lint_ctrls,
                _section("산출 미리보기"),
                *files,
                ft.Container(expand=True),
                scaffold,
                gen,
            ],
            spacing=6,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    left = ft.Container(build_nav(), width=230, bgcolor=PANEL, padding=14)
    center = ft.Container(build_center(), expand=True, padding=18, bgcolor=PANEL)
    right = ft.Container(build_right(), width=370, bgcolor=PANEL, padding=18)

    def refresh() -> None:
        left.content = build_nav()
        center.content = build_center()
        right.content = build_right()
        page.update()

    state.subscribe(refresh)
    page.add(
        ft.Row(
            [left, ft.VerticalDivider(width=1), center, ft.VerticalDivider(width=1), right],
            spacing=0,
            expand=True,
        )
    )


def run() -> None:
    if os.environ.get("FLET_VIEW", "") == "web":
        ft.run(main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("FLET_PORT", "8552")))
    else:
        ft.run(main)


if __name__ == "__main__":
    run()
