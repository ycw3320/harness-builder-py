"""인앱 LLM 오프라인 테스트 — content 모델·env 변환·컴포넌트 머지·credentials(모킹). 네트워크 0."""

import harness_llm.credentials as cred
from harness_core.ir.factory import create_component
from harness_core.ir.schema import parse_component
from harness_llm.content_models import CONTENT_MODELS, to_patch

_KINDS = ["prose-guideline", "permission-rule", "mcp-server", "hook", "policy-doc", "sub-agent"]


def test_content_models_cover_all_kinds():
    for kind in _KINDS:
        assert kind in CONTENT_MODELS


def test_mcp_env_pairs_to_dict():
    data = {
        "server_name": "gh",
        "command": "npx",
        "args": ["-y"],
        "env": [{"name": "T", "value": "${T}"}],
    }
    assert to_patch("mcp-server", data)["env"] == {"T": "${T}"}


def test_content_model_merges_into_valid_component():
    """LLM content(샘플) → 모델 검증 → 컴포넌트 머지 → 전체 재검증(SSOT 재사용)."""
    m = CONTENT_MODELS["permission-rule"](action="deny", pattern="Bash(rm -rf:*)")
    patch = to_patch("permission-rule", m.model_dump())
    base = create_component("permission-rule", "permissions").model_dump(by_alias=False)
    base.update(patch)
    c = parse_component(base)
    assert c.action == "deny"
    assert c.pattern == "Bash(rm -rf:*)"


def test_credentials_offline_safe(monkeypatch):
    monkeypatch.setattr(cred, "_keyring", lambda: None)
    assert cred.available() is False
    assert cred.get_api_key("anthropic") is None
    assert cred.has_api_key("anthropic") is False
    cred.delete_api_key("anthropic")  # 무해


def test_credentials_roundtrip_mocked(monkeypatch):
    store: dict = {}

    class Fake:
        def set_password(self, s, p, k):
            store[(s, p)] = k

        def get_password(self, s, p):
            return store.get((s, p))

        def delete_password(self, s, p):
            if (s, p) in store:
                del store[(s, p)]
            else:
                raise KeyError

    monkeypatch.setattr(cred, "_keyring", lambda: Fake())
    cred.save_api_key("anthropic", "sk-test")
    assert cred.has_api_key("anthropic")
    assert cred.get_api_key("anthropic") == "sk-test"
    cred.delete_api_key("anthropic")
    assert not cred.has_api_key("anthropic")
