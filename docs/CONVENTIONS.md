# 코딩 규칙 (정본)

## 네이밍
- **Python 식별자(모듈·함수·변수·속성) = snake_case.**
- **IR 필드 = snake_case 속성 + camelCase alias**(ADR-0002). 예:
  ```python
  server_name: str = Field(alias="serverName")
  model_config = ConfigDict(populate_by_name=True, extra="forbid")
  ```
  - 직렬화/입력은 snake/camel 둘 다 허용, **속성 접근은 snake_case**(`h.script_body`).
- 클래스 = PascalCase. 상수 = UPPER_SNAKE.

## pydantic v2
- `_Base` 공통필드 상속 + `Annotated[Union[...], Field(discriminator="kind")]` 판별 유니온.
- 모듈 수준 `TypeAdapter` 1회 생성 후 재사용(매 호출 생성 금지).
- 진입점 2종: `parse_*`(예외) / `safe_parse_*`(`{ok, data|errors}` — UI는 safe만 사용).
- `extra="forbid"`로 오타 필드 차단.

## 결정론 / 골든 게이트 (ADR-0003)
- export/lint/sim은 **순수 함수**(부작용·시각·LLM 없음). 동일 입력 → 동일 출력.
- JSON 직렬화는 `json.dumps(x, indent=2, ensure_ascii=False)` + 필요 시 trailing `\n`(JS 동치). **`ensure_ascii=False` 필수**(한국어 보존).
- 파일 리스트 정렬은 Python `sorted(key=path)`(결정론·로케일 무관). 골든은 **내용·경로집합**만 비교(순서 무관).
- **코어 리팩터링 시 골든을 갱신하지 않는다.** 산출 의도가 바뀐 경우에만 골든 재생성 + 독립 커밋.

## 테스트
- 코어·로직(state/lint/sim) = `pytest` 우선. UI 위젯 테스트는 프레임워크 확정 후.
- FS는 `tmp_path` 픽스처로 실제 트리 생성 후 대조.
- 골든 재생성(의도 변경 시): TS repo에서 `npx -y tsx scripts/gen-golden.ts <out>`.

## ruff
```
select = ["E","F","I","N","UP","B","SIM","RUF"]
line-length = 100 ; target-version = "py311"
```
`ruff format`(double quote) 적용.

## 주석·문서
- 주석·docstring = **한국어**. 식별자·타입은 원문 유지.
- 코드가 진실인 사실은 문서에 값 복붙 금지 — 모듈 경로만 지시(SSOT).

## git
- 커밋 메시지(한국어): `PM<n>-<단계>: 무엇 (검증)`.
- 커밋 전 게이트: `ruff format --check` → `ruff check` → `pytest`.
- 파괴적 git(`reset --hard`·force push·브랜치 삭제)·`--no-verify`는 사용자 명시 승인 필수.
- co-author 트레일러 미부착(저장소 일관성).

## 북극성
규칙이 충돌하면 "초심자가 쉽게 설정"을 우선한다.
