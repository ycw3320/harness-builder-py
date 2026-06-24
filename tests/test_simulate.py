from harness_core.ir.presets import safety_first_preset
from harness_core.sim.simulate import glob_to_regexp, simulate


def test_glob_to_regexp():
    r = glob_to_regexp("**/.env*")
    assert r.search(".env")
    assert r.search("config/.env.local")
    assert not r.search("src/index.ts")


def test_env_write_blocked_by_hook():
    r = simulate(safety_first_preset("demo"), {"tool": "Write", "path": ".env", "label": "x"})
    assert r["outcome"] == "blocked-by-hook"
    assert r["blockedBy"] == "guard-hook-secrets"


def test_forcepush_ask():
    r = simulate(safety_first_preset("demo"), {"tool": "Bash", "command": "git push --force origin main", "label": "x"})
    assert r["outcome"] == "ask"
    assert r["blockedBy"] == "perm-ask-forcepush"


def test_build_allowed():
    r = simulate(safety_first_preset("demo"), {"tool": "Bash", "command": "npm run build", "label": "x"})
    assert r["outcome"] == "allowed"


def test_hook_disabled_allows_env():
    ir = safety_first_preset("demo")
    for c in ir.components:
        if c.id == "guard-hook-secrets":
            c.enabled = False
    r = simulate(ir, {"tool": "Write", "path": ".env", "label": "x"})
    assert r["outcome"] == "allowed"
