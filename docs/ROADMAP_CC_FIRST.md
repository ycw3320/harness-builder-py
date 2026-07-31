# 로드맵 — Claude Code 우선 완성 (2026-07-09)

> 다중 에이전트 감사(현 커버리지 · CC 전체 표면 · 해자/UX 갭 병렬 → 종합 → 적대 검증) 산출.
> 원 계획 아카이브는 [PLANS_ARCHIVE.md](PLANS_ARCHIVE.md), 비가역 결정은 `DECISIONS/`.

## 전략 프레임 — "CC 우선 = 중립성 포기"가 아니라 "중립성의 전제조건"

감사 확인: **`targetTool`은 명목상 슬롯일 뿐 실제 중립성이 없다.** `Meta.target_tool = Literal["claude-code"]`로
고정, 코드 어디서도 이 값을 *읽어 분기*하지 않으며(grep 확인), `export_ir`/`assemble`는 `.claude/`·`CLAUDE.md`·
`.mcp.json` 경로와 `settings.json` 포맷을 하드코딩 → 이미 CC 전용.

따라서 "CC 우선"은 후퇴가 아니라 **현 상태의 정직한 인정 + depth-first**. 논리: 얕은 멀티툴은 아무것도
증명하지 못한다. 한 도구에서 ①완전한 표면 커버리지 ②거짓 없는 오프라인 해자(시뮬=현실)를 먼저 증명해야
일반화할 자격이 생긴다. **방법 = 추상화 선반이 아니라 "경계"**: 저작 모델(kind·필드)은 도구중립 명명 유지,
CC 고유 직렬화는 `export_ir`/`assemble` 어댑터 한 곳에 격리 → 훗날 두 번째 툴 어댑터는 순수 ADD.

## 핵심 발견 — 지금 필요한 건 "기능 추가"보다 "해자가 진실을 말하게" 하는 것

초심자 신뢰가 북극성인 제품에서 "거짓 안전"은 "기능 누락"보다 나쁘다. **신뢰 삼각** — 넓히기 전에 먼저 메운다:

- **발견 A — 시뮬 ≠ 산출물:** hook의 `action(deny)`·`path_glob`이 `settings.json`에 **직렬화되지 않음**
  (`export_ir.py` matcher+command만 기록, action/glob은 simulate 전용 메타). 화면에서 본 "차단"이 실제 파일엔 없음.
- **발견 B — 크로스플랫폼 거짓 안전:** 프리셋 훅은 `#!/usr/bin/env bash`(`presets.py`)인데 주 사용자·타깃은
  Windows. git-bash/WSL 없으면 훅이 조용히 미실행되며 성숙도 "Lv4 검증됨" 도달.
- **발견 C — 최다 kind가 시뮬 0:** `CLAUDE.md`/prose는 시뮬 효과 0(`simulate`는 hook/permission만 처리) →
  지침만 작성한 median 초심자는 빈 시뮬 화면.

## 개선안 (방안/이유/기대효과) — frozen 경계 정직하게 3티어

불변식: **harness_core는 frozen 골든 게이트, ADD만(ADR-0012).** 각 안을 건드리는 계층으로 분류(공수·승인 기준).

### 티어 1 — 앱 계층 (frozen 무관 · 저위험 · 승인 불요 · 즉시 착수)

**1-A. 컨텍스트 프리뷰 & prose 규칙-매칭 시뮬** (발견 C)
- 방안: LLM 0회 유지, ①assemble된 `CLAUDE.md`(+global 병합) 실제 텍스트 프리뷰 ②액션/경로 시나리오에 어떤
  prose 지침이 "주입·매칭"되는지 결정론 매칭 표시. **prose 한정** — `.claude/rules/`(policy-doc)는 CC 자동 로드
  표면이 아니라(앱 관례) "주입됨"으로 표시하면 발견 A 괴리 재생산(검증 지적).
- 이유: 앱 최다 kind의 시뮬 효과 0 → 해자가 게이팅만 보여주고 하네스 대부분인 컨텍스트 지침을 못 보여줌.
- 기대: median 초심자가 "무엇이 주입되고 어떤 규칙이 걸리나"를 즉시 봄. 북극성 직관 핵심 결손 해소.

**1-B. 신호 정합화 (자기모순 제거)** — *착수*
- 방안: ①`completion()`(view_model.py)이 "의도적으로 건너뛴" 계층(무-MCP/무-agent) N/A 처리해 100% 도달 가능
  (현재 5계층 하드코딩이라 안내를 따르면 100% 불가) ②권한 recommended_default `Bash(:*)`→좁은 예시로 교정
  (자기 팁 "좁게"와 충돌·`sec-broad-allow` 자기발화) ③hook 이벤트·matcher 정규식·MCP 네임스페이스
  (`mcp__server__tool`)·모델선택 글로서리 데이터 추가.
- 이유: 도구가 스스로와 모순(따르면 100% 불가, 권장값이 자기 경고에 걸림)이면 초심자 신뢰 붕괴.
- 기대: 저비용 고신뢰 ROI. 완성 체감·신호 일관성 회복, 용어 이해로 진입장벽 하락.

**1-C. 크로스플랫폼 precheck** (발견 B의 안전한 절반)
- 방안: 완료 다이얼로그 "방금 본 차단이 실제 적용됩니다" 출력 전 bash/pwsh 실행 가능 여부 precheck, 미충족 시
  단정 약속 대신 조건부 안내로 문구 강등. (프리셋 훅 OS별 교체는 frozen → 티어 2.)
- 이유: Windows에서 bash 훅 미실행인데 "적용됩니다" 단정 = 거짓 안전.
- 기대: 주 플랫폼에서 약속 신뢰성 확보. 거짓 안전 제거 = 북극성 신뢰의 하한선.

**1-D. 여정 완결** (효과는 "학습 루프", retention 아님)
- 방안: export 전후 `CLAUDE.md`/`settings.json` 실제 내용 프리뷰(1-A 컴포넌트 재사용), 기존 레포 원클릭 적용
  (파일 복사 + 선택적 git init), 완료 후 "작동 확인→반복 수정→`.harness.json` 팀 공유" 다음 단계 안내.
- 이유: 현재 export는 경로 목록(최대 8개)+`APPLY.md` 산문에서 멈춰 학습 루프가 얕음. (검증 지적: 1회성
  빌더라 SaaS형 잔존율 KPI 부적합 — 효과는 "학습 루프 완결"로 한정.)
- 기대: 확인→적용→반복 학습 루프 완결. 초심자가 산출물 정체를 이해한 채 실사용으로 넘어감.

### 티어 2 — extended-ADD (harness_core 편집, ADR-0012 절차 = gen_golden_ext + 생성/검증 2커밋. frozen 바이트 불변)

**2-A. 보안 lint 강화** — 시크릿 벤더(OpenAI `sk-`·Google `AIza`·PEM), PowerShell/파이썬 인젝션
(`iex`·`Invoke-WebRequest`·`python -c`), MCP command/args 스캔, 죽은 규칙(넓은 deny에 가린 allow) 탐지.
- 정직 표기: 전부 warning·export 미차단인 오프라인 권고 스캐너 → "권고 정확도 향상"이지 "차단력 획득" 아님.

**2-B. deny 훅 미집행 탐지 lint (`hook-no-enforce`)** — exit 2 없거나 본문 스텁(`enforcement.py` exit 0 TODO)인
deny 훅 경고. 발견 A를 *탐지*하는 저비용 절반(근본 해결은 3-A).

**2-C. bash-shebang × Windows lint 경고** — security 룰셋 추가 + pwsh 대체본 제시. 발견 B를 lint로 표면화.

### 티어 3 — frozen 수정 / 코어 확장 (사용자 명시 승인 + 골든 재생성. 신뢰 트랙 green 이후)

**3-A. 시뮬↔산출물 정합 코드젠 통일** (발견 A 근본 해결) — `action`+`matcher`+`path_glob`을 실제 exit-2 가드로
코드젠 export + `simulate`/export 단일 생성기 통일. **frozen 변경**(export_ir·simulate·enforcement) → 승인+재박제.
"시뮬에서 막힌 것 = 산출물에서 막힘" 계약 성립 → Lv4 "검증됨"이 진실이 됨.
- **실측 발견(2026-07-10, 함께 수정)**: `glob_to_regexp` 치환 순서 버그 — `**/`→`(?:.*/)?` 삽입 후
  `*`→`[^/]*` 치환이 삽입된 `.*`까지 오염시켜 `**`가 "최대 한 단계 디렉터리"로 축소. 실증:
  `sub/dir/.env`가 시뮬=통과 / 실제 bash hook=차단(과소 매칭 = 시뮬이 현실보다 덜 막음).
  frozen 골든 재박제 필요 항목.

**3-B. settings.json 핵심 필드 저작** — 신규 config kind로 `model`·`permission.defaultMode`(관련도 HIGH 2종)
+ `env`(medium) 병합 export. 현재 settings.json은 permissions·hooks 두 키뿐.

**3-C. 슬래시 커맨드·스킬 신규 kind + hook 이벤트 확장** — `.claude/commands/*.md`·`.claude/skills/`는 지금 빈
`.gitkeep`만(저작 불가), hook 이벤트도 4종뿐(`UserPromptSubmit`·`SubagentStop` 등 5종 누락). 코어 2회차·대형 → 최후.

## 권장 순서

**티어 1 → 티어 2 → 티어 3.** 원칙: 해자가 거짓말하는 상태에서 커버리지를 쌓으면 거짓을 복리로 키운다.
먼저 해자가 진실을 말하게 하고(오프라인·LLM 0 유지), 그다음 표면을 넓힌다. 코어를 건드리는 3-A/B/C만
골든 게이트 리스크 → 승인 후반부에 집중.

## 진행 상태
- [x] 1-B 신호 정합화 — 완성도 미터 적응화(100% 도달 가능) + 권장 기본값 자기모순 교정 + model/MCP 용어 툴팁 (1ca17b0 외)
- [x] 1-A 미리보기 다이얼로그 — 산출물 실제 텍스트 + '언제 적용되나'(정직한 타이밍: prose=상시, hook/permission=조건부, policy=자동로드 안 됨). 키워드 매칭 대신 kind 기반 타이밍(휴리스틱 무·오해 방지). 부수: 다크테마 QListWidget 대비 버그 수정
- [ ] 1-D 여정 완결
- [x] 1-C 크로스플랫폼 precheck — `runtime_check.py`(shebang→실행기 판정, 단어경계 매칭으로 pwsh/zsh≠sh) +
  성숙도 Lv4 **보류**(bash 부재 시 차단 훅 미실행 → '검증됨' 거짓 안전 차단) + 완료 다이얼로그 ③ 문구
  단정→조건부 강등 + 상태 카드 경고. **발견 B의 안전한 절반 완료**(프리셋 훅 OS별 교체는 티어2 2-C).
- [ ] 2-A/2-B/2-C (extended-ADD)
- [ ] 3-A/3-B/3-C (frozen, 승인 필요)
