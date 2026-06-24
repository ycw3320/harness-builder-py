# ADR-0002: IR 필드명 = snake_case + camelCase alias

- **상태:** 수락 (2026-06-24)
- **맥락:** PM1 코어는 TS 골든 충실을 위해 IR 필드명을 camelCase(`serverName`·`matcherTool`·`scriptBody` 등)로 두었다. Python 관례는 snake_case다.
- **결정:** IR 모델의 속성명을 **snake_case**로 바꾸고, 직렬화·역직렬화 호환을 위해 camelCase **alias**를 부여한다. `model_config = ConfigDict(populate_by_name=True, extra="forbid")`.
- **근거:** export 산출물은 export 코드가 **문자열 키로 dict를 수동 조립**하므로 IR 필드명을 바꿔도 **산출 바이트가 불변**이다(검증: 골든 25 GREEN 유지). 코어 전체 표기를 snake_case로 통일하면 가독성·일관성이 오른다. 전환 비용 ≈ 0.
- **영향:** 코어의 속성 접근(`h.script_body` 등)을 일괄 갱신한다. 골든 재생성 불필요. 입력 dict는 snake/camel 둘 다 허용(populate_by_name).
