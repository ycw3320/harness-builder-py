> **아카이브(2026-07-06):** 세션 플랜 파일(.claude/plans/wondrous-baking-kahan.md)이 47KB 로 커져 매 세션 재주입 컨텍스트를 잠식 — 완료된 PM2~PM9 상세 계획 전문을 여기로 이관 보존(내용 무변경). 활성 계획은 플랜 파일에 요약만 유지. 비가역 결정은 docs/DECISIONS/ 참조.

---

# 하네스 빌더 (Python) — PM2 사전 엔지니어링 + 실행 계획

## Context (배경)

PM1(코어 Python 포팅 + 바이트-동일 골든 게이트, pytest 25 GREEN)은 완료·push됨([ycw3320/harness-builder-py](https://github.com/ycw3320/harness-builder-py), Private). 사용자 요구: **PM2 실개발 착수 전, 업무 영역을 빈틈없이 세분화·정의하고 모호점을 모두 확정**한 뒤, **개발 시 참고할 업무 규칙·정의를 `docs/` MD 문서셋으로 저장**해 "엔지니어링부터 완료"한다. 본 계획이 그 엔지니어링 산출 + PM2 실행 기준이다.

**상위 불변식:** 코어(harness_core)는 무수정·소비만, **골든 게이트 25 GREEN 보존**이 모든 영역의 최우선 제약.

## 북극성 원칙 (항상 인지)
- **핵심 = "Claude Code 초심자도 쉽게 설정할 수 있는 하네스 설정."** 모든 영역·UI·문서·기본값·문구는 이 기준으로 판단한다 — 어렵거나 전문가를 전제하면 재설계. (안내형 누적 흐름 §0.6·필드 가이드·프리셋이 이를 집행)
- **외부 자료(ECC 등)는 설정 *철학*만 차용, 콘텐츠·코드·문구는 복제하지 않는다** — 전부 우리 표현으로 재작성.

## 확정 결정 (사용자 응답 + 경량 권장 채택)
| 분기 | 결정 |
|---|---|
| 문서화 범위 | **전 문서 골격(목차) + PM2 직접영역 본문** (PM3+ 문서는 구현 시 채움) |
| IR 필드명 | **snake_case + camelCase alias + `populate_by_name`** — export 산출 바이트 불변(검증됨), 골든 재생성 불필요 |
| FS 병합 디폴트 | **SKIP_EXISTING(비파괴) + dry-run 필수**. OVERWRITE/BACKUP은 명시 선택지 |
| 프레임워크 판정 | **에이전트 정량 채점(픽셀·LOC) + 사용자 최종(모던룩) 결선** |
| (경량) UI 테스트 | 로직(state/lint/sim)만 pytest 선행, 위젯은 FW 확정 후 |
| (경량) field_guides | PM3 이연 + 데이터 외부화. verification 계층 = 표시만 "준비중". 커밋 co-author 미부착 |

---

## 0.5 경쟁·포지셔닝 (웹 검증 반영)

- **경쟁 지형(검증):** Archon(22.5k★, `.archon/yaml` 워크플로 엔진 — *다른 레이어*) · revfactory/harness(7.5k★, `.claude/` 메타스킬 — *직접 경쟁*) · OpenHarness(런타임 — *무관*). **진짜 최대 위협 = Claude Code 본체**(`/agents`·`/hooks`). 부분 선점 = claude-settings.nl(웹 settings 편집)·opcode/Claudia(GUI 러너).
- **검증된 빈틈:** "표준 `.claude/` **6계층 전체** 시각 조립 + **실행 전 결정론 시뮬레이션** + 로컬 폴더 병합"을 한 번에 주는 도구는 **부재**.
- **무게중심(반영, 구조 변경 없음):** 제품·PM2 데모·랜딩의 **1순위 가치 = 라이브 결정론 시뮬레이터(LLM 0회) + 정합성 lint = "실행 전 안전 검증"**. 진짜 해자는 시뮬레이터(`core.sim`)이며 GUI·초심자·표준산출은 *진입조건*이지 해자 아님. → PM2 우패널/첫 데모의 강조점을 **시뮬레이터·lint**에 둔다. (코어·아키텍처 불변)
- **제품명 재고 메모:** "하네스 빌더" 단독 의존 회피(Archon이 "최초 오픈소스 하네스 빌더" 선점 주장). "**실행 전 시뮬레이터형**" 류 수식자 검토. 정식 출시명 추후 확정.
- **정면충돌 회피:** 실행 런타임으로 확장 금지(→ Archon/OpenHarness의 **상류 보완재** 포지션), 숙련자/팀협업 경쟁 회피 → 초심자·단일 데스크톱 집중.

---

## 0.6 주력 UX — 안내형 누적 빌드 흐름 (Guided Accumulation)

**핵심 흐름(사용자 확정):** 앱이 LLM을 직접 호출하지 않고 — **① 영역의 "설정 가능 항목" 제시 → ② "외부 LLM에 이렇게 요청하세요" 프롬프트 제안·복사 → ③ 사용자가 외부 LLM 답을 항목에 채움(=소규모 컨텍스트) → ④ 시뮬레이터·lint·완성도 실시간 갱신 → ⑤ "다음 추천 영역" → 반복 → ⑥ 6계층 채워지면 하네스 완성 → 내보내기.** 결정론·오프라인·BYO-LLM(API키 불요)을 그대로 유지하며, 이는 우리 강점(시뮬레이터·결정론)과 정합한다.
- **재사용(이미 설계):** 필드 가이드(`askLLMTemplate`·복사·예시채우기) · 6계층 영역 제시(add-bar·layer intro) · 라이브 시뮬레이터·lint(실시간).
- **신규 추가(이 흐름 격상):** (a) **영역단위 종합 프롬프트 제안**(현재 항목별만) (b) **완성도 미터 + "다음 추천 영역"** (c) **안내(가이드) 모드**(초심자 디폴트).
- **in-app 자연어 컴파일러는 "선택적 가속기"로 강등**(앱이 직접 LLM 호출, BYO-key, PM5+). **주력은 위 복사→누적 흐름이며 PM3 핵심 UX로 편입.**

---

## 0.7 설정 방식 — ECC(affaan-m/Everything Claude Code) 참고 반영

ECC = CLI/플러그인 기반 CC 설정 최적화 시스템(멀티 IDE). 형태는 다르나 **설정 철학이 우리와 정합** → 검증 + 보강.
- **정합(방향 검증):** 계층적 상속(env→글로벌→프로젝트→플러그인) ≈ 우리 6계층+context(global/project) / **"기본값 존중→선택적 제거→점진 확장"** ≈ 프리셋+점진노출+**§0.6 안내형 누적 흐름**(동일) / 선택적 활성화 ≈ enabled 토글.
- **보강(설정 방식에 반영):**
  1. **계층적 우선순위 가시화** — env→글로벌→프로젝트 override 를 UI/IR_SPEC 에 표기.
  2. **토큰/모델 최적화 = 1급 설정영역** — `settings-flag`(model·`MAX_THINKING_TOKENS`·`AUTOCOMPACT_PCT`·hook 프로필)·`env-var`. (ECC 핵심 단계) → 중요도 상향, 안전우선 프리셋에 합리적 기본값 포함 검토. (PM3 settings 계층 / PM5)
  3. **lint → "실행 전 보안 검증" 확장(해자 강화)** — 기존 시크릿·모순 + **권한 과다·MCP>10·도구 과다(토큰비용)·훅 인젝션** 경고. ECC AgentShield 대응을 **라이브 lint 패널에 내장** → 시뮬레이터+lint 1순위 가치 강화. (PM3 lint 확장)
  4. **자동 감지** — 폴더 쓰기/역import(A2/A3) 시 스택·패키지매니저 감지 → 컨텍스트 프리필. (PM3+)
  5. **path-scoped rules** — `.claude/rules/*.md` `paths:` frontmatter(언어/경로별 룰) = policy-doc variant. (advanced)
- **결론:** ECC는 우리 "설정 철학(프리셋→선택제거→점진확장 = 누적 흐름)"을 외부 검증하고, **lint를 보안 검증으로 키울 근거**를 줬다 — 우리 해자(실행 전 안전 검증)와 직결. 아키텍처 변경 없음.

---

## 1. 업무 영역 WBS (빈틈 0 — TS 30개 기능 매핑 완료)

```
A. harness_fs/   [신규·갈래무관]  가상트리 ↔ 디스크 (A1 write_tree · A2 merge · A3 importer[PM3] · A4 fs_errors)
B. harness_app/  [신규·갈래의존]  3-pane GUI (B1 state · B2 shell · B3 nav · B4 center{a행/b폼/c문서뷰} · B5 right{a시뮬/b lint/c export} · B6 field_guide · B7 controllers)
C. guides/       [신규·app계층]   field_guides·layer_intros·meta 데이터 포팅
D. packaging/    [PM4]            빌드·서명·배포
E. cross/        [횡단]           E1 app_config · E2 logging · E3 i18n
```

**임계 의존사슬:** `core → C → B1(state) → B2~B6(위젯)` / `A4 → A1(write_tree) → B5c(export)` / `A2 → B5c(병합)`.
**프레임워크 무관(병행 착수 가능):** C, B1, A1, A4 — Flet/Qt 비교와 동시 진행. **선행 차단점:** B2~B6 위젯 본구현은 프레임워크 확정 후.
**신규 필수 영역 = A(harness_fs):** 브라우저 ZIP → 데스크톱 직접 폴더쓰기 승격(프로젝트 핵심 차별점).

---

## 2. docs/ 문서셋 매니페스트 (승인 후 생성)

원칙: **SSOT** — 각 사실은 한 문서만 소유, 코드가 진실인 항목(경로 매핑·lint 규칙)은 **값 복붙 금지·모듈 경로만 지시**(골든 드리프트 차단). 영역마다 "먼저 볼 문서" 1개.

| 파일 | 목적 | 본문/골격 |
|---|---|---|
| `README.md` · `docs/00_INDEX.md` | 소개 + 문서지도·SSOT 소유표·읽는 순서 | **본문** |
| `docs/ARCHITECTURE.md` | 3계층 단방향 의존·경계 규칙 | **본문** |
| `docs/CONVENTIONS.md` | 네이밍(snake+alias 경계)·pydantic·결정론·테스트·ruff·git | **본문** |
| `docs/GLOSSARY.md` | 25+ 용어 단일 정의처 | **본문** |
| `docs/IR_SPEC.md` `EXPORT_SPEC.md` `LINT_SPEC.md` `SIMULATOR_SPEC.md` *(계약)* | 6 kind·경로매핑·규칙·우선순위 (코어 모듈 지시) | **본문** |
| `docs/FS_SPEC.md` `STATE_SPEC.md` `PM2_SPEC.md` | 직접쓰기/병합 · store CRUD/groupKey · PM2 슬라이스·루브릭 | **본문** |
| `docs/UI_SPEC.md` `FIELD_GUIDE_SPEC.md` `PACKAGING.md` | 3-pane·36px·가이드·패키징 | **골격(PM3/PM4 채움)** |
| `docs/DECISIONS/ADR-0001..0006.md` | 비가역 결정 로그 | **본문** |

**ADR 즉시 기록:** 0001 3계층 단방향 / 0002 IR snake_case+alias / 0003 골든 바이트-동일 게이트 / 0004 프레임워크 판정(에이전트 정량+사용자 최종) / 0005 FS 비파괴 디폴트 / 0006 field_guides PM3 이연.

---

## 3. 핵심 규칙 (확정 권장값)
- **IR 필드명:** snake_case 속성 + `Field(alias="serverName"...)` + `model_config=ConfigDict(populate_by_name=True, extra="forbid")`. export/lint/sim/factory/presets의 속성 접근을 snake_case로 일괄 갱신(골든 바이트 불변 → 25 GREEN 유지가 검증 기준).
- **테스트:** 골든 = 경로집합 + per-path 바이트 동일(순서 무관). 리팩터링 시 골든 갱신 금지 — 의도 변경만 독립 커밋. 로직은 store/lint/sim을 pytest, FS는 `tmp_path` 트리 대조, 위젯은 FW 확정 후.
- **FS:** `write_tree(tree, dest, strategy=SKIP_EXISTING, *, dry_run=False, make_dest=True)` — 전수검증 후 기록·traversal 차단·UTF-8/LF 보존·BOM 금지·dry_run 무변경·멱등.
- **involvement 색(단일출처):** auto `#1a7f37` / assisted `#0969da` / manual-gate `#bc4c00`.
- **커밋:** 한국어 `PM<n>-<단계>: 무엇 (검증)`, 커밋 전 `ruff format --check → ruff check → pytest` 게이트. 파괴적 git·`--no-verify` 승인 필수.
- **ruff 보강:** `select=["E","F","I","N","UP","B","SIM","RUF"]` + `ruff format`.

---

## 3.5 기술스택 × 기능영역

**확정(현재 사용/프레임워크 무관):** Python 3.11 · pydantic v2 · pytest · ruff · setuptools/pyproject · stdlib(pathlib·json·re·dataclasses·enum·secrets·logging·typing).
**PM2 결정대기(GUI):** Flet(+flet-desktop) 또는 PySide6(Qt, LGPL) — 양쪽 프로토타입.
**참조 전용(런타임 아님):** TS 웹 frozen(React/Vite/zod/zustand/jszip=골든 기준) · Node+tsx(골든 재생성) · git/gh.

| 기술 | 사용 기능영역 | 용도 |
|---|---|---|
| pydantic v2 | core.ir · B1 state · A3 importer | IR 모델·검증·discriminated union·safe_parse |
| pathlib | A1 writer · A2 merge · A3 importer · E1 config | 디스크 경로·IO |
| json | core.export · A2 merge(딥머지) · A3 importer · E1 | 직렬화/역직렬화 |
| re | core.sim(glob) · core.lint(pattern) · A3 importer | 정규식·glob |
| dataclasses / enum / secrets | core.export(VirtualFile) / A4(정책) / core.factory(id) | 값객체·정책상수·id |
| logging | E2 | 쓰기/병합/예외 로그(시크릿 미기록) |
| pytest / ruff | tests · 전 코드 | 골든·회귀 게이트 / lint+format |
| **Flet 또는 PySide6** | B2 shell·B3 nav·B4 center·B5 right·B6 guide | 위젯·렌더·이벤트·파일다이얼로그 |
| flet build / PyInstaller·Briefcase | D packaging | 설치본(확정 후) |

**Flet vs Qt UI 구성요소 대조:** 3-pane(`ft.Row+VerticalDivider` / `QSplitter`) · 컴팩트행(`Container(h=36)+AnimatedSwitcher` / `setFixedHeight+QPropertyAnimation+QSS`) · 폴더선택(`FilePicker.get_directory_path` / `QFileDialog.getExistingDirectory`) · 상태반영(observable+`page.update()` / `Signal.emit`) · 핫리로드(Flet 강점/Qt 빈약) · 모던룩(Material 기본/QSS 구매).

---

## 4. PM2 실행 스펙

### 수직 슬라이스 S1~S6 (양 갈래 공통, context 1계층만 실동작)
S1 3-pane 셸(리사이즈) · S2 좌 nav(context만 실동작, 5계층 비활성 라벨 + 색점) · S3 컴팩트 36px 행(prose 행→펼침 heading/body) · S4 편집→state patch→우측 라이브 갱신 · S5 우 패널(`lint_ir` + `assemble_project` 파일목록 + [폴더선택→생성]) · S6 `write_tree` 폴더쓰기.
시드 = `safety_first_preset("my-project")`(context prose 2행). **PM3 이월:** 나머지 5계층 편집기·전 kind 폼·필드가이드·settings 딥머지·역import·멀티타깃.

### 갈래별
- **Flet** `harness_app/flet_shell/`: `ft.Row`+`VerticalDivider` 3-pane, 커스텀 nav, `Container(height=36)`+`AnimatedSwitcher`, `FilePicker.get_directory_path`, `flet run -d` 핫리로드.
- **Qt/PySide6**(LGPL) `harness_app/qt_shell/`: `QSplitter` 3-pane, `QListWidget` nav, `setFixedHeight(36)`+`QPropertyAnimation`+QSS, `QFileDialog.getExistingDirectory`.
- **state mutator는 갈래 무관 동일**(B1). 차이는 `_notify` 배선(`page.update()` vs `Signal.emit`) — 이 LOC도 M6에 반영.

### 결정 루브릭 (가중 100)
M1 36px밀도(15) · M2 색점(10) · M3 펼침애니(12) · M4 리사이즈(12) · M5 모던룩(13) · M6 LOC/시간(20) · M7 핫리로드(8) · M8 패키징(10). 점수=Σ(PASS=가중/부분×0.5/FAIL=0). **채점:** 에이전트(M1·M2·M6·M8 정량 + M3·M4 1차) / 사용자(M5 최종 + M3·M4 승인, 스크린샷).
**임계:** 점수차≥10 → 즉시 채택. <10 & M1·M3·M4 FAIL 0 → 사용자 M5 결선(동률 시 M6→M8). 한 갈래라도 M1/M3/M4 FAIL → 탈락. 갈래당 셸 시간박스 1~2일.
**DoD:** 양 셸 S1~S6 동작(동일 시드·state API) + `write_tree` 실폴더 생성/병합(비파괴 확인) + 루브릭 채점·스크린샷 + 사용자 M5 확정 → 1종 채택, 폐기 갈래 `_archive/` 격리.

---

## 5. 착수 순서 (승인 후)
```
0. ADR-0001~0006 기록
1. docs/ 생성: 00_INDEX → ARCHITECTURE·CONVENTIONS·GLOSSARY → 계약 SPEC(IR/EXPORT/LINT/SIMULATOR) → FS/STATE/PM2_SPEC → (UI/FIELD_GUIDE/PACKAGING 골격)
2. 코어 snake_case+alias 적용(골든 25 GREEN 유지가 게이트)
3. C(guides) 포팅            ┐
4. A4 → A1(write_tree)+pytest │ 프레임워크 무관, 병행
5. B1(state)+pytest          ┘
6. PM2 프로토타입: Flet 갈래(S1~S6) ∥ Qt 갈래(S1~S6) — 시간박스
7. 루브릭 채점+스크린샷 → 사용자 M5 → 프레임워크 확정 → 폐기 갈래 _archive/
8. PM3 착수(전 계층 패리티·A3 역import·UI/FIELD_GUIDE 본문)
```

## 5.5 원래 의도 추적성 (보존 확인 + 누락 복원)

여러 피벗(웹→Python 재작성)에도 **초기 의도가 전부 살아있음을 명시 보장**한다.
- **보존(코어 완료 또는 PM2~3 명시):** 시각 GUI·6계층·결정방식(involvement)·**라이브 시뮬레이터**·정합성 lint·즉시실행 폴더(직접쓰기)·점진노출·필드 가이드·컴팩트 UI·컨텍스트 문서뷰·CRUD·역import(A3)·멀티타깃(IR `targetTool`).
- **누락 복원 → PM5 신설(MVP 이후, 원래 의도 완결):** 웹이 M1.5에서 멈춰 "패리티=PM3"가 그 위 항목을 빠뜨렸으므로 명시 복원한다.
  1. **안내형 누적 빌드 흐름(§0.6) 완성** — 영역단위 종합 프롬프트 + 완성도 미터 + "다음 영역" 추천 + 안내 모드. **주력 UX이므로 PM3 핵심에 편입**, 온보딩 마감은 PM5. *(선택) in-app 자연어 컴파일러*는 이 흐름의 가속기(BYO-key)로 별도.
  2. **강제수준 사다리 UI** — 프로즈<정책문서<hook 승격 인터랙션(`enforcement` 데이터 존재).
  3. **추가 프리셋 4종**(속도/엔터프라이즈/MVP).
  4. **온보딩** — 가이드 투어 + 읽기전용 개관맵.
- **마일스톤 전체:** PM1✅(코어) → PM2(프레임워크·직접쓰기) → PM3(기능 패리티 + **안내형 누적 흐름 §0.6** + 역import·멀티타깃) → PM4(패키징·MVP 출시) → **PM5(온보딩·완성도·강제수준 사다리·프리셋 확장 + (선택)자연어 컴파일러 = 원래 의도 완결)**.

---

## 6. 검증
- **문서/엔지니어링:** docs/00_INDEX의 영역→문서 매핑이 WBS 전 영역을 덮는지(빈틈 0 재확인). 계약 SPEC이 코어 모듈을 지시(값 복붙 0).
- **코어 snake_case 적용:** `pytest` 25 GREEN 유지(골든 바이트 불변) — 회귀 0.
- **FS/state(프레임워크 무관):** `pytest`(write_tree `tmp_path` 트리 대조, state CRUD/move/groupKey).
- **PM2 프로토타입:** 양 셸 실행→폴더 생성/병합 확인 + 루브릭 표·스크린샷 → 사용자 M5.

---

# PM3 실행 계획 (확정 2026-06-24) — 동적 CRUD · 풀 패리티 · 인앱 LLM

## Context (왜)
PM2까지: 프레임워크 PySide6/Qt 확정([[ADR-0007]]), Apple 라이트/다크 테마([[ADR-0008]]), 그러나 Qt 셸은 **context 1계층·prose만 편집·CRUD 버튼 없음·7개 시드 고정**. 사용자 3대 요구:
1. **너무 기본 세팅이 많다 → 동적으로 늘려가는 방향** (가벼운 시작 + add/remove).
2. **안 채워도 되게 + 서브에이전트 등 전 kind 확장** (전 6계층·전 kind 폼, 빈 계층 허용).
3. **외부 LLM 복사 대신, 각자 API 키로 앱 내부 수신 + 백단에 하네스용 프롬프트 사전탑재** (BYO-키 인앱 LLM).

**핵심 발견(조사 완료):** 백엔드는 이미 대부분 존재 — `state.py`의 CRUD 7종(add/add_prose/remove/duplicate/move/toggle/patch, 프레임워크 무관), `factory.create_component`·`registry.addable_kinds_by_layer`가 **6 kind 전부**(sub-agent 포함, verification 빈 계층 허용), `guides.field_guides`(전 kind ask_llm_template), `Intent.compiled_by="llm"`, `safe_parse_component`. **요구 1·2는 UI 노출**, 요구 3은 **`client.messages.parse(output_format=pydantic)`** 로 우리 IR 스키마를 SSOT 재사용해 검증된 컴포넌트 생성.

**확정 결정(사용자):** ① 빈/최소 시작 + 프리셋 선택(빈 시작 기본) ② Anthropic(Claude) 우선(멀티 프로바이더 인터페이스만 준비) ③ 단계적 A→B→C. **북극성·해자 불변:** 결정론 시뮬레이터·lint = LLM 0회 유지, 오프라인 복사→붙여넣기 흐름(§0.6) 기본 보존, 코어 골든 25 GREEN 불변(코어는 `minimal_preset` 추가만).

---

## PM3-A — 동적 CRUD + 가벼운 시작 (요구 1)
**범위:**
- `harness_core/ir/presets.py`: **`minimal_preset(project_name)` 신규** — context에 "프로젝트 개요" prose 1개(본문 비움)만. `safety_first_preset` 은 "안전우선"으로 보존. (코어 ADD만 — 골든 불변.)
- `harness_app/state.py`: 프리셋 레지스트리 `{"minimal","safety-first"}` + `load_preset(name)` / `__init__(preset=...)`. 기존 CRUD 메서드(이미 존재) 그대로 사용.
- `harness_app/qt_shell/app.py`:
  - **시작 프리셋 선택**(첫 실행 모달 또는 좌패널 상단): 빈 시작 / 안전우선 → `state.load_preset`.
  - **계층별 add-bar**: `registry.addable_kinds_by_layer[layer]`(basic/고급 토글) 버튼 → `state.add_component(kind)`.
  - **행 컨트롤**: 각 행에 ✕(remove)·복제(duplicate)·↑↓(move) → 기존 `state.*`. **시그니처 라우팅 refresh**(이미 구현)로 구조 변경만 중앙 재빌드(편집 포커스 보존).
**검증:** `pytest`(minimal_preset 1개 시드, state CRUD 회귀) · 골든 25 GREEN · 오프스크린 렌더로 add/remove 확인 · ruff/format.

## PM3-B — 전 6계층 풀 패리티 + 전 kind 폼 (요구 2)
**범위:**
- `harness_app/view_model.py`: **`SLICE_ACTIVE_LAYER` 게이팅 제거 → 전 계층 interactive**. kind별 **필드 스펙** 함수 `field_specs(kind) -> list[FieldSpec]`(name·label·위젯종류 line/textarea/combo/list/dict·options) 신규 — 스키마 필드에서 도출(데이터 구동, 서브클래스 6종 회피).
- `harness_app/qt_shell/app.py`: **RowWidget을 field_specs 구동 폼으로 일반화**(현재 heading/body 하드코딩 → 동적 렌더). 각 에디터 변경 → `state.patch({field: value})`. kind별 필드:
  - prose: scope(combo) · heading · body / permission: action(combo) · pattern / mcp: server_name · command · args(list) · env(dict, `${VAR}` 힌트) / hook: event(combo) · matcher_tool · path_glob · action(combo) · script_name · script_body(textarea) / policy-doc: doc_name · body / sub-agent: name · description · tools(list) · model · system_prompt(textarea).
  - **결정방식(involvement) 선택**(자동/추천/직접 combo) → patch. **빈 계층**도 layer intro + add-bar 표시.
  - **필드 가이드 패널**(§0.6 복사→붙여넣기): `guidance_for(component)`의 purpose·ask_llm_template·예시를 **"외부 LLM에 이렇게 요청" 복사 버튼**으로. (요구 3 미사용 시 기본 흐름.)
- 재사용 list/dict 미니 에디터(행 추가/삭제) 2종.
**검증:** `pytest`(factory 6 kind·state.patch 각 kind 필드·field_specs 커버리지) · 각 계층 오프스크린 렌더 · lint/sim GREEN · ruff.

## PM3-C — 인앱 LLM (Anthropic BYO 키, 오프라인 기본 유지) (요구 3)
**신규 패키지 `harness_llm/`**(코어 순수성 보존 — core는 LLM 무의존):
- `credentials.py`: **keyring**(Windows 자격증명관리자) `save/get/delete/has(provider)`. SERVICE="harness-builder". **키 로그·커밋 절대 금지**(QSettings엔 provider/model 선택만, 키는 keyring만).
- `prompts.py`: **kind별 하네스용 시스템 프롬프트**(우리 표현 — ECC 등 외부 복제 금지). 각 kind가 *무엇을 만들지* + 안전우선(예: mcp는 `${VAR}`만, hook은 exit2). `guides.field_guides`와 역할 분리(사용자용 ask_template ↔ 시스템용).
- `content_models.py`: kind별 **편집 필드만의 경량 pydantic 모델**(id/layer/involvement/enabled 제외) → `messages.parse(output_format=...)` 스키마. (extra=forbid → additionalProperties:false, structured-outputs 호환.)
- `client.py`: `LLMClient`(ABC) + **`AnthropicClient`**: `anthropic` SDK `client.messages.parse(model, system=prompts[kind], max_tokens=2048, messages=[{user:intent}], output_format=ContentModel)`. 모델 기본 `claude-opus-4-8`(설정서 opus/sonnet/haiku 선택). 멀티 프로바이더는 ABC로 확장 여지만.
- `pyproject.toml`: `[project.optional-dependencies] llm = ["anthropic>=0.40", "keyring>=24"]` + `packages.find`에 `harness_llm*`. **지연 import**(미설치 시 LLM 버튼 비활성 + "pip install harness-builder[llm]" 안내).
- `harness_app/qt_shell/app.py`:
  - **설정 다이얼로그**: 프로바이더(Anthropic)·모델 콤보·API 키 입력(마스킹, 되읽기 금지) → `credentials.save`. **프라이버시 고지**(오프라인→온라인 전환, 입력이 외부 LLM 전송).
  - **컴포넌트/추가 옆 "LLM로 채우기" 버튼**: 키 있을 때만 활성. 의도 입력 → `AnthropicClient` → 검증된 content → `state.patch`(+`Intent.compiled_by="llm"`). 오류(auth/rate/parse) 인라인. **키 없으면 §0.6 복사→붙여넣기 그대로**.
**보안:** keyring 저장·키 미로그·`.gitignore`(.env 이미 차단)·외부호출 고지. 결정론 시뮬·lint는 LLM 0회 유지.
**검증:** `pytest`(prompts·content_models 오프라인 파싱: 샘플 JSON→유효 컴포넌트, network 없이 / credentials 라운드트립은 keyring 백엔드 모킹) · 오프라인 경로 48 GREEN 불변 · 실키 1건 수동 라이브(사용자 제공) · ruff.

---

## 변경 파일 요약 & 재사용
| 파일 | PM3 작업 | 재사용(이미 존재) |
|---|---|---|
| `harness_core/ir/presets.py` | A: minimal_preset 추가(ADD만) | safety_first_preset |
| `harness_app/state.py` | A: preset 레지스트리·load_preset(name) | CRUD 7종(무관·완비) |
| `harness_app/view_model.py` | B: 게이팅 제거·field_specs | nav_items/rows/sim/lint/involvement_meta |
| `harness_app/qt_shell/app.py` | A·B·C: add-bar·행CRUD·kind폼·involvement·가이드패널·설정·LLM버튼 | build_qss/테마·시그니처 라우팅·_dot/_rgba |
| `harness_app/guides.py` | B·C: field_guides 연결 | field_guides·guidance_for·involvement_meta |
| `harness_core/ir/registry.py` | (무변경) | addable_kinds_by_layer·basic/고급 |
| `harness_core/ir/schema.py` | (무변경) | parse/safe_parse_component·Intent(llm) |
| **`harness_llm/`(신규)** | C: credentials·prompts·content_models·client | — |
| `pyproject.toml` | C: optional-deps llm·packages | — |
| `docs/DECISIONS/` | ADR-0009(동적CRUD·minimal·field-spec)·ADR-0010(인앱LLM·keyring·구조화출력·오프라인기본) | — |

## 검증 (E2E)
- **회귀 불변:** 골든 25 GREEN(코어 minimal_preset ADD만), 오프라인 pytest 48 GREEN, ruff/format clean.
- **신규 pytest:** minimal_preset·field_specs(전 kind)·llm content 파싱(오프라인)·credentials(모킹).
- **오프스크린 렌더:** 6계층 interactive·add/remove·kind 폼·설정 다이얼로그·LLM 버튼(키 없으면 비활성).
- **라이브:** 빈 시작→권한규칙 추가→필드 편집→시뮬 갱신 / (C) 실키로 1 kind LLM 생성.
- **커밋:** `PM3-A/B/C: …` 단계별, 프리커밋 게이트(format→check→pytest).

---

# PM6 실행 계획 (확정 2026-06-26) — 초심자 직관화: 하네스 "아하" 재설계

## Context (왜 이 작업인가)
사용자 피드백: **"아직 어려워."** 현재 앱은 PM1~5로 기능은 완비됐으나, **북극성("CC 초심자도 쉽게 + 하네스가 뭔지 직관 이해")에 미달**. 다각도 검증(워크플로우 29 에이전트: 현업/지망 개발자 페르소나 4명 첫 실행 시뮬 → 6렌즈 독립 재설계 → 3인 패널 18심사 → 종합)에서 **페르소나 4명 전원이 "아, 이게 하네스구나" 도달에 실패**. 공통 원인 3가지가 만장일치로 지목됨:
1. **빈 시작(minimal) 기본** → 첫 화면이 텅 비어 차단 장면을 못 봄.
2. **before/after 가치 시연 부재** → 시뮬레이터가 결과만 보이고 "하네스 없으면 vs 있으면" 대비를 안 보여줌.
3. **"하네스" 정의 부재** → 온보딩 괄호 1곳뿐, 전문용어(PreToolUse·exit 2·glob·`${VAR}`·MCP·`Write|Edit`) 무설명 노출.

**의도한 결과:** 초심자가 **글을 읽기 전에 화면으로 먼저 "하네스가 하는 일"을 체감**하고, 토글로 직접 차단을 무너뜨려본 뒤 정의를 만나, **첫 실행 30초 내 "아, 이게 하네스구나"에 도달**.

## 북극성 + 핵심 메커니즘
- **북극성(불변):** "Claude Code 초심자도 쉽게 + 하네스 개념 직관 이해."
- **단일 핵심 메커니즘:** **"설명 대신 결과의 차이로 정의한다."** 빈 IR vs 현재 IR을 동시 `simulate`해 before/after 2열을 보여주고, 사용자가 가드레일 토글을 끄면 우열이 즉시 무너지는 인과를 손으로 만지게 한 뒤, **그 사건 직후** "방금 본 게 하네스예요" 정의가 페이드인.
- **앵커 비유:** **안전벨트**(주) — "하네스 = Claude Code가 내 규칙대로 안전하게 움직이도록 잡아주는 설정 묶음(.claude/ + CLAUDE.md). 빠른 말에게 채우는 안전벨트처럼 평소엔 자유롭게 일하되 위험한 방향(.env·강제push)으로는 못 가게 잡아준다." 비유는 **치환 아닌 병기**(실제 용어 항상 동반).
- **해자 보존:** 결정론 오프라인 시뮬레이터(LLM 0회) + lint는 그대로. before/after는 `simulate`를 빈 IR로 1회 더 부르는 것뿐 — **신규 코어 0, 골든 게이트 불변**.

## 확정 결정 (사용자 응답 2026-06-26)
| 분기 | 결정 |
|---|---|
| 작업 범위 | **온보딩 풀패키지 (Step 1~6)** — 아하 엔진 + 서사 + 6계층 캡션 + 용어 툴팁 + 프리셋 비교 + export 다음단계 |
| 예시 항목 안심 | **항목마다 "예시예요, 지워도 됩니다" 배너** (편집 시 사라짐) |
| 용어 풀이 톤 | **2단: 쉬운 말 라벨 1줄 + 호버 시 개발자용 1줄** |
| before/after 좌열 프레이밍 | (권고 채택) **정직하게 "규칙 없으면"** — 빈 IR 기준. "완전 무방비" 과장 금지(해자 신뢰 보존) |
| 자유입력 샌드박스 | **이번 제외**(Step 7) — 입력 해석 휴리스틱 오분류가 결정론 해자 신뢰를 흔듦 |

## 검증된 코드 사실 (계획의 토대 — 직접 확인 완료)
- `app.py:552` — `BuilderState("my-project", preset="minimal")`로 윈도가 minimal **강제**(state 기본은 이미 safety-first). → 1줄 교정.
- `app.py:815-819` — `f"•  {s.label}  →  {s.outcome}"`로 렌더, **`SimVM.reason`(view_model.py:67-71에 이미 채워짐)을 버림**. → 살리기만 하면 됨.
- `app.py:602-617` — `_signature`는 `(theme, layer, advanced, (id,enabled,involvement))`만 추적(pattern/body 미추적). **`_rebuild_right()`는 항상 실행(617)**. → before/after 패널을 **우측에 두면 토글 역전이 추가 배선 0**. (중앙 상단 배치 시 pattern 편집에 갱신 누락 → **우측 배치 필수**.)
- `state.toggle`(state.py:141) / `state.set_selected_layer` / `simulate(ir, action)`(순수 함수, `reasons`·`blockedBy` 반환) / `default_scenarios` 3종(.env 쓰기·강제 push·정상 빌드) 모두 재사용 준비됨.

## 재설계된 초심자 여정 (목표 경험)
1. 앱 켜짐 → **safety-first 채워진 상태**로 시작, 우측 1급 패널에 before/after가 이미 대비되어 보임.
2. 코치마크 1줄: "아래 토글을 꺼보세요 — 차단이 풀립니다."
3. 사용자가 `.env hook` 토글 OFF → 우열 그 줄이 즉시 `통과⚠`로 붕괴(인과 체감).
4. **그 직후** "방금 본 게 하네스예요" + 안전벨트 정의 페이드인.
5. 좌측 6계층에 "아는가→해도되나→절대못함→어떻게→검증" 흐름 캡션. 항목 펼치면 `?` 용어 풀이.
6. export → "다음 단계" 가이드(폴더를 루트에 두고 `claude` 실행 → 방금 본 차단이 실제 적용) + [폴더 열기].

## 구현 — Step별 (검증 가능 단위)

### Step 1 — 첫 화면 즉효 (저위험, 1줄)
- **변경:** `harness_app/qt_shell/app.py:552` `preset="minimal"` → `preset="safety-first"`.
- **검증:** 앱 실행 시 우측 시뮬레이터에 `.env→차단`·`강제push→확인`·`정상빌드→통과`가 서로 다르게 표시(빈 화면 아님). 오프스크린 스크린샷.

### Step 2 — before/after 2열 시연 패널 (본체)
- **`harness_app/view_model.py`:** `sim_compare(state) -> list[SimCompareVM]` 신규. 시나리오마다 `simulate(_empty_ir, sc)`(before)와 `simulate(state.ir, sc)`(after) 동시 평가. `SimCompareVM(label, before_outcome, before_reason, after_outcome, after_reason, after_blocked_by)`. `_empty_ir = HarnessIR(meta=state.ir.meta, components=[])`. **코어 무수정**(빈 IR은 앱 계층에서 생성).
- **`harness_app/qt_shell/app.py` `_rebuild_right`(815-819 교체):** "라이브 시뮬레이터" 섹션을 **세로 스택 2열 대비**로 재구성(380px 폭 대응): `시나리오 / 규칙없으면→결과⚠ / 지금→결과✓ + reason 1줄`. outcome 색·아이콘 차등. 이어 **"지금 켜진 규칙" 토글 리스트**(enabled guardrail/permission 컴포넌트, `state.toggle` 연결). 우패널 상시 재빌드라 토글 시 즉시 역전.
- **검증:** `.env hook` 토글 OFF → after 열이 `통과⚠`로 바뀌고 reason 갱신. pytest: `sim_compare` 단위(빈 IR 전부 allowed, safety-first IR은 .env 차단).

### Step 3 — 인과 강화 (점프)
- **`view_model.py`:** `SimCompareVM.after_blocked_by`에 `simulate` 결과의 `blockedBy`(컴포넌트 id) 채움.
- **`app.py`:** 차단 결과 줄 클릭 → 원인 컴포넌트의 layer로 `state.set_selected_layer` + 중앙에서 해당 행 강조/스크롤.
- **검증:** 차단 줄 클릭 → 중앙의 원인 항목이 선택·강조되는지.

### Step 4 — 온보딩 서사 (체감→정의)
- **`app.py`:** 텍스트 벽 환영 다이얼로그(`_show_welcome` 1035-1067) **제거/축소** — 첫 실행에 모달 없이 곧장 대비 화면. 토글 위 **코치마크 1줄**(첫 상호작용 전까지만). 사용자 첫 토글 OFF 시 우패널 상단에 **정의+안전벨트 비유 페이드인**("방금 본 게 하네스예요…"). 도움말 버튼은 간결한 정의+여정 안내로 교체.
- **`guides.py` + `app.py` 좌패널(`_rebuild_left`):** 6계층 리스트 위 **"아는가→해도되나→절대못함→어떻게→검증" 흐름 캡션** 1줄(`layer_meta` 곁).
- **검증:** 첫 실행 시 텍스트 폭탄 없이 대비가 먼저 보이고, 토글 후 정의가 뜨는지(오프스크린 2컷).

### Step 5 — 용어·프리셋·안심 (2단 풀이)
- **`harness_app/guides.py`:** `GLOSSARY: dict[str, dict]` 신규 — 용어→`{short, dev}` 2단. 대상: PreToolUse/PostToolUse/SessionStart/Stop, exit 2, glob(`**/.env*`), `${VAR}`, MCP, hook, `Write|Edit`, npx, deny/ask/allow. **단일 출처 정의 상수**(`HARNESS_DEFINITION`)도 여기 두어 창부제·시연 헤더·export 3곳 반복(spaced repetition).
- **`app.py` RowWidget / `view_model.field_specs`:** 필드 라벨에 쉬운 말 1줄 + `setToolTip(dev)`(2단 톤). **Hook 시점 콤보 한글 라벨**((표시, 값) 매핑) — 현재 raw 값만 노출(view_model.py:130) → 라벨/값 분리.
- **프리셋 비교:** 드롭다운에 프리셋별 1줄 설명 + 계층별 항목 수.
- **예시 안심 배너:** 프리셋 시드 컴포넌트에 **"예시예요, 지워도 됩니다"** 옅은 배너(RowWidget). `load_preset` 시 시드 id 기억 → 해당 항목 `patch`(편집) 시 배너 제거(BuilderWindow UI 레벨 set).
- **검증:** hook 편집폼·프리셋 드롭다운 무설명 약어 0건. 예시 항목 배너 표시→편집 시 사라짐.

### Step 6 — export 종결 (다음 단계)
- **`app.py` export 성공 다이얼로그(≈885-888):** "생성 N개" 단순 메시지 → **"다음 단계" 가이드**: ① 이 폴더를 프로젝트 루트에 두세요 ② 그 폴더에서 `claude` 실행([복사] 버튼) ③ 방금 본 차단이 실제로 적용됩니다 + **[폴더 열기]**(`QDesktopServices.openUrl`).
- **검증:** export 후 다이얼로그에 단계·명령 복사·폴더 열기 동작.

## 변경 파일 요약 & 재사용
| 파일 | PM6 작업 | 재사용(이미 존재) |
|---|---|---|
| `harness_app/qt_shell/app.py` | S1 프리셋 1줄·S2 2열패널+토글리스트·S3 점프·S4 서사/코치마크/정의·S5 라벨풀이/배너·S6 export가이드 | `_rebuild_right`(상시), `_signature` 라우팅, `state.toggle/set_selected_layer`, RowWidget |
| `harness_app/view_model.py` | S2 `sim_compare`(빈 IR vs 현재)·S3 `after_blocked_by`·S5 콤보 라벨 | `simulate`, `default_scenarios`, `SimVM.reason`, `field_specs` |
| `harness_app/guides.py` | S4 흐름 캡션·S5 `GLOSSARY`+`HARNESS_DEFINITION` | `layer_intros`, `field_guides.tips`, `involvement_meta` |
| `harness_core/*` | **무변경**(골든 불변) | `simulate`/`assemble_project`/`presets` |
| `tests/` | S2 `sim_compare`·S5 GLOSSARY 커버리지·프리셋 기본=safety-first 회귀 | 기존 66 GREEN |
| `docs/DECISIONS/` | ADR-0011(초심자 아하 재설계: 결과차이=정의·우측 시연승격·체감후정의) | — |

## 이번에 빼는 것 (descope)
- **자유입력 샌드박스**(위험명령 직접 타이핑) — 휴리스틱 오분류로 결정론 해자 신뢰 훼손 위험. 다음 마일스톤.
- **모드 탭 분리**(시험장/구성 2탭) — 단일 3-pane 유지. 모드 전환 동기 부재 + `_signature` 충돌.
- **`rm -rf` 시나리오 신규 추가** — `default_scenarios` 변경 시 골든 재박제 필요. 기존 3종으로 충분, 필요 시 view_model 전용 리스트(코어 불변).
- **위험도 라벨 신규 데이터(⚠비밀유출/💥삭제)** — outcome 색·아이콘 차등만. 신규 데이터 출처 미확정.
- **확장 비유 일러스트(SVG)** — 안전벨트 한 줄 정의로 충분.

## 검증 (E2E)
- **회귀 불변:** 코어 무수정 → **골든 66 GREEN 유지**, ruff format/check clean.
- **신규 pytest:** `sim_compare`(빈 IR=전부 통과 vs safety-first=.env 차단·강제push 확인), GLOSSARY 키 커버리지, `BuilderState` 기본 프리셋=safety-first.
- **오프스크린 렌더(`QT_QPA_PLATFORM=offscreen`):** ① 첫 화면 before/after 대비 ② 토글 후 역전+정의 페이드인 ③ hook 편집폼 용어 풀이 ④ export 다음단계 다이얼로그.
- **라이브 시나리오:** 앱 실행 → 토글 OFF로 차단 붕괴 체감 → 정의 확인 → 항목 편집(배너 사라짐) → export → 다음단계 가이드.
- **커밋:** `PM6-S1..S6: …` 단계별, 프리커밋 게이트(format→check→pytest). 파괴적 git·`--no-verify` 금지.

---

# R#8 실행 계획 (2026-06-29 작성, 승인 대기) — qt_shell/app.py 기계적 분해

## Context
R트랙(#1~#7) 완료·main 머지 후 마지막 항목. `app.py` ~1,700줄 모놀리스에 리뷰 발견 7건(다이얼로그 인라인·버튼 보일러플레이트 21회·사적 속성 월경(state._preset)·매직넘버·지역 import)이 몰려 있고, 이후 PM7 UI 작업(수신 검증 화면·성숙도 레벨)이 전부 이 파일을 지나므로 먼저 분해한다. **offscreen 테스트 15건이 안전망**(행동 불변 검증).

## 원칙
- **기계적 이동만** — 로직 변경 0, 시그니처 유지, 리네임 최소. 동작 차이가 나면 실패.
- **테스트 무수정 통과**: `app.py` 가 기존 공개 이름(BuilderWindow·RuleToggle·LIGHT·build_qss 등)을 re-export 유지 → 기존 import 경로 전부 생존.
- pytest 84 GREEN + 오프스크린 렌더 전/후 비교가 게이트.

## 분해 구조 (harness_app/qt_shell/)
| 신규 파일 | 이동 대상 |
|---|---|
| `theme.py` | LIGHT/DARK/THEMES·FONT_STACK·_QSS·build_qss·_rgba·_INV_KEY |
| `widgets.py` | _dot·ClickableLabel·RuleToggle·ListEditor·DictEditor·RowWidget·_FIELD_H·_TITLE_FIELD + `make_btn(label, object_name, on_click, tip)` 헬퍼(버튼 5줄 패턴 21회 축약·커서 누락 4곳 일관화) |
| `landing.py` | LandingPage |
| `dialogs.py` | 환영(show_welcome)·export 다음단계(show_export_done)·LLM 설정(open_llm_settings) — BuilderWindow 메서드에서 함수로 추출(parent·필요 상태 인자화) |
| `app.py` 잔여 | BuilderWindow(라우팅·재빌드·콜백)·make_app·main + re-export (~700줄 예상) |

## 준비 커밋(사적 접근 제거)
- `BuilderState.preset` property 추가(state.py — `_preset` 직접 접근 치환), RowWidget 의 `_row.id` 접근은 `row_id` property 로 노출. (경계 위반 5곳 해소)

## 검증
- pytest 84 GREEN(테스트 무수정) · ruff clean · 오프스크린 렌더 2컷(랜딩·빌더) 전후 동일 확인 · 커밋 2개(준비/분해) + push.
## 비범위
- 스타일 규약 재정리·펼침 높이 실측·기능 추가 일절 없음(별도 트랙).
- **완료(2026-06-29):** 9092c2c(property화)·b7cb008(4모듈 분해). app.py 1,764→797줄, 테스트 무수정 84 GREEN, 렌더 픽셀 동일, main 머지.

---

# PM7 실행 계획 (2026-06-29 작성, 승인 대기) — 통합 하네스 파일 + 실행 전 안전 검증 심화

## Context
진화 탐색(29방향·3심사) 종합의 1순위 묶음. 논지: **"GUI 조립 도구 → 검증 가능한 하네스 파일 표준 + 안전 검증 엔진"** — 파일의 모든 이동(저장·공유·열기)이 결정론 lint+시뮬 관문을 통과하는 구조가 해자가 된다. 현재 작업이 메모리 전용(앱 끄면 소실)인 최대 결손도 함께 해소. R#8 분해 완료로 UI 작업 준비됨.

## S1 — 골든 게이트 2계층화 (절차 선행, 소)
- `tests/golden/` → `tests/golden/frozen/`(기존 TS 기원 fixture 이동 — 영구 불변) + `tests/golden/extended/`(Python 자체 박제, 신규 코어 ADD 전용). conftest `golden` 픽스처에 탐색 경로 추가.
- `scripts/gen_golden_ext.py` 신설(생성 커밋과 검증 커밋 분리 강제). ADR-0012(코어 ADD 절차: frozen 불변·extended 는 의도 변경 커밋에서만 재생성).
- 검증: 기존 84 GREEN 불변(경로만 이동).

## S2 — 통합 .harness.json (저장=공유=마이그레이션, 소)
- **코어 ADD**: `harness_core/ir/migrate.py` — `MIGRATIONS: dict[str, callable]`(현재 빈), `load_ir_any(text) -> HarnessIR`(ir_version 순차 마이그레이션 후 parse). ADR-0013(스키마 진화 규칙: 신규 필드 default 필수, extra=forbid 유지, 버전 올릴 때만 MIGRATIONS 추가).
- **앱**: 우패널에 [저장]·[열기] — 저장 = `state.ir.model_dump_json(by_alias=True, indent=2)` → `<프로젝트>.harness.json`. 열기 = `load_ir_any` → **수신 검증 다이얼로그**(lint 결과 + before/after 시뮬 요약 + "이 하네스가 하는 일" 표시) → 확인 시 `state.load_ir`. 외부 파일 경고(hook script_body 확인 유도) 포함.
- 파일 의미 구분: **단일 확장자 .harness.json**(작업/공유 동일 포맷 — 심사관 이중 포맷 금지 권고 채택).
- 검증: 저장→열기 라운드트립(pytest)·golden preset_ir 로 열기 스모크·수신 검증 다이얼로그 렌더.

## S3 — lint 보안 룰팩 (opt-in, 소)
- **코어 ADD**: `lint_ir(ir, rulesets=("core",))` 시그니처 확장 — 기본 호출 결과 바이트 불변(frozen 골든 보호). `"security"` 룰셋 5규칙: broad-allow(전면 허용 경고)·dangerous-allow(rm -rf 류 allow)·hook-injection(curl|sh 등)·secret-literal(sk-ant-·ghp_ 등)·mcp-overload. **전부 warning**(export 차단 없음), 문구는 2단 톤.
- 앱: lint 패널 + S2 수신 검증에서 `rulesets=("core","security")` 로 호출. 프리셋 5종 전부 security 클린 검증(시드 신뢰 보호).
- 검증: 규칙별 pytest(발화/미발화)·frozen 골든 불변·프리셋-클린.

## S4 — 성숙도 레벨 Lv0~4 (종결자, 소)
- `view_model.maturity(state)` — 결정론 산식: Lv0 무방비(활성 규칙 0) / Lv1 약속(prose만) / Lv2 규칙(permission·policy 존재) / Lv3 강제(활성 PreToolUse+deny hook ≥1) / Lv4 검증됨(**기본 임계값 제안**: lint error 0 + security 경고 0 + sim changed ≥1 + .env 차단·강제 push 확인 커버 — 산식은 툴팁으로 공개, 조정 가능).
- UI: 완성도 미터를 레벨 표시로 보강("Lv3 강제 — 다음: lint 경고 0으로") + can_promote 승격 버튼·가드레일 add-bar 로 점프 연동. export README 에 레벨 문구 1줄.
- 검증: 프리셋별 레벨 pytest(minimal=Lv1·safety-first=Lv4 기대)·오프스크린 렌더.

## 불변·순서
코어는 **ADD만**(S1 절차 하에)·frozen 골든 불변·오프라인/LLM 0회 유지. 순서 S1→S2→S3→S4(의존: S2 수신검증이 S3 룰팩을, S4 가 S3 결과를 소비 — S2 는 S3 전엔 core 룰셋만으로 출시 가능). 단계별 커밋+게이트, 새 브랜치 `feature/pm7-harness-file`.
- **완료(2026-06-29):** S1 68566ea → S2 627ca65 → S3 cf821dc → S4 85c99da. pytest 84→102 GREEN, main 머지.

---

# PM8-실험 계획 (2026-06-29) — 빠른 시작(QuickStart): 최소 입력으로 하네스 완성

## Context
사용자 요구: "엄청나게 직관적이거나 최소한의 입력만으로" — 현재는 간단해졌어도 여전히 '조립'이 필요.
진화 탐색 고득점 조합(자동 감지 7/10 + 예시 이식 8/10 + 성숙도 S4)을 묶어 **질문 3개(클릭 2~5회)로
Lv4 하네스**를 만드는 초간편 경로를 실험 브랜치 `feature/pm8-quickstart` 에서 프로토타입.

## 흐름(초심자 여정)
랜딩 [30초 빠른 시작] → 다이얼로그 1장:
① (선택) 프로젝트 폴더 선택 → **스택 자동 감지**(package.json/pyproject/pom/go.mod/Cargo 등) →
   컨텍스트(스택·빌드·테스트 명령) 자동 채움 문구 표시
② 성향 3택1: 조심조심(safety-first) / 균형(mvp) / 빠르게(speed)
③ 핵심 보호 체크 3개(기본 켬): .env 비밀키 차단(hook) · 폴더 통삭제 금지(deny) · 강제 push 물어보기(ask)
→ **실시간 미리보기**: 예상 성숙도 LvN + 차단 요약(선택 바꾸면 즉시 갱신 — vm.maturity 재사용)
→ [빌더에서 확인](채워진 상태로 착지) / (폴더 선택 시) [지금 바로 이 폴더에 생성](write_tree+다음단계)

## 구현(전부 앱 계층 — 코어 무수정)
- `harness_app/detect.py`(신규, 순수): 폴더→DetectedProject(스택 라벨·빌드/테스트 명령 추정·근거 파일).
  package.json 은 scripts 파싱으로 build/test 정밀화. 감지 실패=None(흐름 지속).
- `harness_app/quickstart.py`(신규, 순수): PERSONAS·PROTECTIONS 매핑 +
  `build_quick_ir(project_name, persona, protections, detected)->HarnessIR` —
  프리셋 기반 + 보호 컴포넌트를 safety_first 시드에서 복제(ensure/remove, gen_id 재부여) +
  감지 결과로 프로젝트 prose 본문 프리필. 결정론·LLM 0회.
- `harness_app/qt_shell/quickstart_dialog.py`(신규): 위 흐름 UI. LandingPage 에 [30초 빠른 시작] 추가.
  BuilderWindow: 수락 시 `_example_ids=set()`(사용자가 답해 만든 것 — 예시 아님) + load_ir,
  '바로 생성' 시 export 경로 재사용.
- 테스트: detect(tmp 프로젝트 픽스처)·build_quick_ir(성향×보호→기대 성숙도: 전체보호=Lv4)·Qt 스모크.
## 검증
게이트(ruff/pytest) + 오프스크린 렌더 + 실행 앱으로 사용자 직접 테스트 → 피드백 후 main 머지 여부 결정.
- **완료(2026-06-29):** QuickStart+도움말칩+체크역할 명시, main 머지(9afb958). 사용자 라이브 테스트 반복 반영.

---

# PM9-P1 계획 (2026-06-29, 승인됨) — 라이브 관측: 하네스 여정 실시간 추적

## Context
사용자 요청: "CLI 지시에 따라 하네스 설정의 어느 부분을 거치는지 앱에서 육안 확인 → 보강점 찾기".
**공식 hooks 표면**을 관측 채널로 사용(비공식 transcript 파싱은 기존 veto 유지) — 관측 전용 hook 이
이벤트를 로컬 JSONL 에 기록하고 앱이 tail. 해자의 3단 완성: 사전 시뮬 ↔ **실행 중 트레이스** ↔ 사후 보강.

## P1 범위 (Windows 우선, 실험 브랜치 feature/pm9-live-observe)
- `harness_app/observe.py`(순수): ①관측 hook 스크립트(PowerShell, stdin JSON→hb-live.jsonl append,
  항상 exit 0 — 판정 무간섭) ②`install_observer(root)`: `.claude/hooks/hb-observer.ps1` 생성 +
  `settings.local.json` hooks 병합 등록(SessionStart·UserPromptSubmit·PreToolUse·PostToolUse·
  SubagentStop·Stop, 재설치 멱등) + `.gitignore` 에 로그 제외 ③`remove_observer` ④이벤트 파서 +
  **매핑 엔진**: PreToolUse payload(tool_name·tool_input)→action dict→기존 `_safe_simulate` 로
  "어느 규칙 카드에 매칭"을 결정론 재현.
- `qt_shell/live_dialog.py`: 비모달 — 폴더 선택→[관측 켜기]→QTimer tail→타임라인 리스트
  ("요청 수신 / 도구 실행 전 Bash: … → 매칭 '.env 쓰기 차단'(차단)"). 우패널 [라이브 관측(실험)] 진입.
- 정직 표기: 매칭은 '앱의 현재 구성 기준 재현'(실제 판정 주체는 Claude Code), 모델 내부는 관측 불가.
- 테스트: 파서·매핑(가짜 이벤트)·설치 멱등·다이얼로그 tail 스모크. **실제 CLI 연동은 수동 검증**
  (TEST_SCENARIOS I그룹) — Windows hook 실행(PowerShell) 확인이 1순위 리스크.
## P2+(후속): 카드 여정 시각화·시뮬 예측 대조·보강 제안("안 걸린 위험 액션→규칙 추가").
