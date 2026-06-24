"""빌더 상태 컨테이너 — UI 프레임워크 무의존 (STATE_SPEC). TS store.ts 포팅.

불변 업데이트(매 변경 새 HarnessIR) + subscribe 통지. 위젯 배선(page.update/Signal)은
subscribe 한 곳에서만 갈린다 — 프레임워크 피벗 시 교체 지점.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from harness_core.ir.factory import create_component, gen_id
from harness_core.ir.presets import PRESETS
from harness_core.ir.schema import (
    ComponentKind,
    HarnessComponent,
    HarnessIR,
    Layer,
    parse_component,
)

Scaffold = Literal["minimal", "harness-only"]
Direction = Literal["up", "down"]
Scope = Literal["global", "project"]
PresetName = Literal["minimal", "safety-first"]


def group_key(c: HarnessComponent) -> str:
    """순서 변경 그룹 키 — 같은 layer, prose 는 scope 까지 분리(전역/프로젝트 경계 보존)."""
    scope = c.scope if c.kind == "prose-guideline" else ""
    return f"{c.layer}|{scope}"


class BuilderState:
    """변경 시마다 새 IR + 구독자 통지. id 인자는 component.id."""

    def __init__(
        self, project_name: str = "my-project", preset: PresetName = "safety-first"
    ) -> None:
        self._project_name = project_name
        self._preset: PresetName = preset
        self.ir: HarnessIR = PRESETS[preset](project_name)
        self.selected_layer: Layer = "context"
        self.selected_file: str | None = None
        self.advanced_mode: bool = False
        self.scaffold: Scaffold = "minimal"
        self._listeners: list[Callable[[], None]] = []

    # 구독 (프레임워크 어댑터 경계) ---
    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        """리스너 등록 → 해제 함수 반환."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def _notify(self) -> None:
        for fn in list(self._listeners):
            fn()

    def _set_components(self, components: list[HarnessComponent]) -> None:
        """새 HarnessIR 로 교체(제자리 변형 금지) 후 통지."""
        self.ir = HarnessIR(meta=self.ir.meta, components=components)
        self._notify()

    # 선택 상태 ---
    def set_selected_layer(self, layer: Layer) -> None:
        self.selected_layer = layer
        self._notify()

    def set_selected_file(self, path: str | None) -> None:
        self.selected_file = path
        self._notify()

    def set_advanced_mode(self, value: bool) -> None:
        self.advanced_mode = value
        self._notify()

    def set_scaffold(self, scaffold: Scaffold) -> None:
        self.scaffold = scaffold
        self._notify()

    def load_preset(self, name: PresetName | None = None) -> None:
        """프리셋 적용. name 생략 시 현재 프리셋 재적용."""
        if name is not None:
            self._preset = name
        self.ir = PRESETS[self._preset](self._project_name)
        self.selected_file = None
        self._notify()

    # CRUD ---
    def add_component(self, kind: ComponentKind) -> None:
        comp = create_component(kind, self.selected_layer)
        self._set_components([*self.ir.components, comp])

    def add_prose_section(self, scope: Scope) -> None:
        base = create_component("prose-guideline", "context")
        self._set_components([*self.ir.components, base.model_copy(update={"scope": scope})])

    def remove(self, comp_id: str) -> None:
        self._set_components([c for c in self.ir.components if c.id != comp_id])

    def duplicate(self, comp_id: str) -> None:
        comps = list(self.ir.components)
        idx = next((i for i, c in enumerate(comps) if c.id == comp_id), -1)
        if idx < 0:
            return
        orig = comps[idx]
        copy = orig.model_copy(update={"id": gen_id(orig.kind), "title": f"{orig.title} (복제)"})
        comps.insert(idx + 1, copy)
        self._set_components(comps)

    def move(self, comp_id: str, direction: Direction) -> None:
        comps = list(self.ir.components)
        idx = next((i for i, c in enumerate(comps) if c.id == comp_id), -1)
        if idx < 0:
            return
        key = group_key(comps[idx])
        siblings = [i for i, c in enumerate(comps) if group_key(c) == key]
        pos = siblings.index(idx)
        swap = pos - 1 if direction == "up" else pos + 1
        if swap < 0 or swap >= len(siblings):
            return
        j = siblings[swap]
        comps[idx], comps[j] = comps[j], comps[idx]
        self._set_components(comps)

    def toggle(self, comp_id: str) -> None:
        comps = [
            c.model_copy(update={"enabled": not c.enabled}) if c.id == comp_id else c
            for c in self.ir.components
        ]
        self._set_components(comps)

    def patch(self, comp_id: str, patch: dict) -> None:
        """kind 별 필드 부분 갱신 — patch 후 재검증(STATE_SPEC)."""
        comps: list[HarnessComponent] = []
        for c in self.ir.components:
            if c.id == comp_id:
                data = c.model_dump(by_alias=False)
                data.update(patch)
                comps.append(parse_component(data))
            else:
                comps.append(c)
        self._set_components(comps)
