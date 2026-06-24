"""프로바이더 추상화 + Anthropic 클라이언트 — messages.parse 구조화 출력.

anthropic 미설치/구버전이면 LLMError. 멀티 프로바이더는 LLMClient ABC 로 확장 여지만.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .content_models import CONTENT_MODELS, to_patch
from .prompts import SYSTEM_PROMPTS

DEFAULT_MODEL = "claude-opus-4-8"
MODELS = ["claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"]


class LLMError(RuntimeError):
    """LLM 호출/파싱 실패 — UI 는 메시지를 인라인 표시."""


def anthropic_available() -> bool:
    try:
        import anthropic  # noqa: F401

        return True
    except ImportError:
        return False


class LLMClient(ABC):
    @abstractmethod
    def generate(self, kind: str, intent: str) -> dict:
        """자연어 의도 → kind 의 편집 필드 dict(state.patch 용). 실패 시 LLMError."""


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        try:
            import anthropic
        except ImportError as e:
            raise LLMError("anthropic 미설치 — pip install harness-builder[llm]") from e
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(self, kind: str, intent: str) -> dict:
        model_cls = CONTENT_MODELS[kind]
        parse = getattr(self._client.messages, "parse", None)
        if parse is None:
            raise LLMError("anthropic 버전이 구조화 출력(messages.parse) 미지원 — 업그레이드 필요")
        try:
            resp = parse(
                model=self._model,
                max_tokens=2048,
                system=SYSTEM_PROMPTS[kind],
                messages=[{"role": "user", "content": intent}],
                output_format=model_cls,
            )
        except self._anthropic.AnthropicError as e:
            raise LLMError(f"API 오류: {e}") from e
        except Exception as e:
            raise LLMError(str(e)) from e
        parsed = getattr(resp, "parsed_output", None)
        if parsed is None:
            raise LLMError("구조화 출력 파싱 실패 — 다시 시도하세요")
        return to_patch(kind, parsed.model_dump())
