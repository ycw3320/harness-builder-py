# 라이브 시뮬레이터 명세 (계약)

> **진실원: `harness_core/sim/simulate.py`.** LLM 0회·결정론. **제품 1순위 차별 가치.**

## simulate(ir, action) → 결과
평가 우선순위:
1. **hook**(PreToolUse·deny): 도구가 `matcher_tool`(정규식)에 맞고 경로가 `path_glob`(glob→정규식)에 맞으면 → `blocked-by-hook`
2. **권한 deny**: 패턴 파싱 후 도구+prefix 매칭 → `blocked-by-permission`
3. **권한 ask**: 매칭 → `ask`
4. 그 외 → `allowed`

반환: `{ action, outcome, reasons[], blocked_by? }`.

## action
`{ tool, path?, command?, label }`

## default_scenarios
`.env 쓰기`(→hook 차단) · `git push --force`(→ask) · `npm run build`(→통과)

## 범위 (정직)
결정론 라우팅(hook 매처·permission 패턴·glob)만 모델한다. **LLM 판단·hook 스크립트의 실제 bash 실행은 모델하지 않는다** → "실행 전, 이 액션이 *라우팅상* 차단/확인/통과되는가"의 미리보기. 그래도 "위험 차단 규칙을 깜빡함/권한 과넓음"을 실행 전 0비용으로 잡는 게 가치.

## UI(B5a)
state 변경 구독 → 시나리오별 `simulate()` → 색 칩(통과/확인/차단) + reasons 툴팁. 150ms 디바운스.
