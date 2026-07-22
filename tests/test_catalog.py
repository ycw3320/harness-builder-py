"""MCP 카탈로그(앱 계층) — build_mcp → export .mcp.json/.env.example 정합 + frozen 무영향."""

import json

from harness_app.catalog import MCP_CATALOG, build_mcp, catalog_entry
from harness_app.state import BuilderState
from harness_core.export.assemble_project import assemble_project
from harness_core.ir.schema import McpServer


def test_catalog_entries_shape():
    keys = {e.key for e in MCP_CATALOG}
    # 적대 검증 통과 10종 시드(postgres·slack 제외)
    assert {"filesystem", "github", "git", "context7", "playwright", "brave-search"} <= keys
    for e in MCP_CATALOG:
        assert e.command in ("npx", "uvx", "docker")
        assert e.args, f"{e.key}: args 비어 있음"
        # 필수 키만 required=True — .env.example 정확성
        for env in e.env:
            assert env.key.isupper() or "_" in env.key


def test_build_mcp_produces_valid_server():
    gh = catalog_entry("github")
    comp = build_mcp(gh, "mcp")
    assert isinstance(comp, McpServer)
    assert comp.server_name == "github" and comp.command == "docker"
    # 필수 비밀키는 ${KEY} 로 프리필(실값 아님)
    assert comp.env == {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"}
    # 키 없는 서버는 env 비어 있음
    fs = build_mcp(catalog_entry("filesystem"), "mcp")
    assert fs.env == {}


def test_export_mcp_json_and_env_example():
    s = BuilderState("demo", preset="minimal")
    s.add_prebuilt(build_mcp(catalog_entry("github"), "mcp"))
    files = {vf.path: vf.content for vf in assemble_project(s.ir, s.scaffold)}
    # .mcp.json 이 stdio 3키 형식으로 생성
    mcp = json.loads(files["demo/.mcp.json"])
    assert "github" in mcp["mcpServers"]
    assert set(mcp["mcpServers"]["github"]) == {"command", "args", "env"}
    assert mcp["mcpServers"]["github"]["command"] == "docker"
    # 비밀키가 .env.example 로 자동 스캐폴드(실값은 사용자가 .env 에)
    assert "GITHUB_PERSONAL_ACCESS_TOKEN=" in files["demo/.env.example"]
    # 설정 파일엔 실제 토큰이 박히지 않음(${VAR} 만)
    assert "${GITHUB_PERSONAL_ACCESS_TOKEN}" in files["demo/.mcp.json"]
