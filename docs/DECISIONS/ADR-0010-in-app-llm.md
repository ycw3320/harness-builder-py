# ADR-0010: 인앱 LLM (Anthropic BYO 키, 오프라인 기본)

- **상태:** 수락 (2026-06-24)
- **맥락:** 사용자 요구3 — "외부 LLM 복사 대신, 각자 API 키로 앱 내부 수신 + 백단에 하네스용 프롬프트 사전탑재". PM5 가속기로 두었던 것을 PM3-C로 앞당김(사용자 단계적 승인).
- **결정:** 신규 **`harness_llm/`** 패키지(코어 순수성 보존 — core·fs·app 무의존). **Anthropic 우선**, 멀티 프로바이더는 `LLMClient` ABC 로 확장 여지만.
  - `credentials.py` — **keyring**(OS 자격증명관리자) 저장. 키는 코드/커밋/로그/QSettings에 **절대 미저장**(QSettings엔 model 선택만). keyring 미설치 시 None/False(오프라인 유지).
  - `content_models.py` — kind별 **편집 필드만**의 경량 pydantic 모델(id/layer/involvement/enabled 제외). `messages.parse(output_format=...)` 스키마. structured-outputs 제약상 **열린 dict 금지** → mcp `env`는 (name,value) 쌍 리스트로 받아 앱에서 dict 변환(`to_patch`). `extra=forbid`(additionalProperties:false).
  - `prompts.py` — kind별 **하네스용 시스템 프롬프트**(우리 표현 — ECC 등 외부 복제 금지). 안전우선 내장(mcp는 `${VAR}`만, hook은 exit 2).
  - `client.py` — `AnthropicClient.generate(kind, intent)` → `messages.parse` → 검증된 content dict. 모델 기본 `claude-opus-4-8`(설정서 opus/sonnet/haiku). `intent.compiled_by="llm"`.
- **구조화 출력:** `client.messages.parse(output_format=PydanticModel)` → `parsed_output`(검증 인스턴스) — "JSON으로 답하라" 프롬프팅보다 견고. 우리 IR/콘텐츠 pydantic 스키마를 SSOT 재사용.
- **오프라인 기본 보존:** 키 없으면 §0.6 복사→붙여넣기 그대로(AI 버튼 비활성/미표시). 결정론 시뮬레이터·lint는 **LLM 0회** 유지(해자 불변). opt-in only.
- **의존성:** `[project.optional-dependencies] llm = ["anthropic>=0.69", "keyring>=24"]`. 지연 import — 미설치 시 기능 비활성 + 안내.
- **보안·프라이버시:** 외부 네트워크 호출이 새로 생김(오프라인→온라인) + 입력 의도가 외부 LLM 전송 → 설정 다이얼로그에 **명시 고지**. 키는 keyring만, 화면 되읽기 금지(placeholder만).
- **영향:** 행 필드 가이드에 "AI로 채우기" 버튼(키 있을 때만). 라이브 실키 검증은 사용자 제공 키로 수동. 관련 [[ADR-0001]](3계층·코어 순수), [[ADR-0009]].
