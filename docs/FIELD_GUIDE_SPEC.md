# 필드 가이드 명세 (골격 — PM3에서 본문)

> 안내형 누적 흐름(§0.6)의 핵심 데이터. PM3에서 데이터 + 위젯(B6) 구현. 콘텐츠는 자체 작성(외부 복제 아님).

## 데이터 구조(예정)
- kind/필드별 `FieldGuidance`: `purpose` · `produces_file` · `ask_llm_template`("외부 LLM에 이렇게 요청하세요", 빈칸 토큰) · `good_examples[]` · `anti_example` · `tips[]` · `recommended_default`
- layer별 `LayerIntro`: `what_it_controls` · `minimum_to_do` · `if_unsure`
- (확장) 영역단위 종합 프롬프트

## 렌더 규칙(예정)
- 도움말 토글 · placeholder(recommended_default) · 예시 채우기 · **프롬프트 복사**(클립보드)
- 채우기는 본문(body) 한정. 읽기전용 + 콜백만.

## 흐름 연결
`ask_llm_template` = 사용자가 외부 LLM에 붙여넣는 프롬프트 = (선택)자연어 컴파일러 입력과 동일 출처.
