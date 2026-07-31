from harness_core.ir.presets import safety_first_preset
from harness_core.sim.simulate import glob_to_pattern, glob_to_regexp, simulate


def test_glob_to_regexp():
    r = glob_to_regexp("**/.env*")
    assert r.search(".env")
    assert r.search("config/.env.local")
    assert not r.search("src/index.ts")


def test_glob_double_star_spans_multiple_dirs():
    """3-A 회귀: `**` 가 '정확히 한 단계'로 축소되던 결함(sub/dir/.env 가 시뮬만 통과).

    치환 순서 때문에 `(?:.*/)?` 삽입 뒤 `*`→`[^/]*` 가 삽입분까지 오염시켜 `.[^/]*` 이 됐었다.
    """
    env = glob_to_regexp("**/.env*")
    for p in (".env", "sub/.env", "sub/dir/.env", "a/b/c/.env.local"):
        assert env.search(p), p
    for p in ("src/app.js", "environment.ts"):
        assert not env.search(p), p

    git = glob_to_regexp("**/.git/**")
    for p in (".git/config", "sub/.git/config", "x/y/.git/hooks/pre-commit"):
        assert git.search(p), p
    assert not git.search(".gitignore")

    claude = glob_to_regexp(".claude/**")
    assert claude.search(".claude/a/b/c.md")
    assert not claude.search("other/x")


def test_glob_pattern_is_ere_compatible():
    """단일 생성기 계약: 같은 문자열을 grep -E 도 써야 하므로 Python 전용 문법 금지.

    `(?:...)` 는 POSIX ERE 에 없어 스크립트 쪽 매칭이 조용히 실패한다.
    """
    for g in ("**/.env*", "**/.git/**", ".claude/**", "**/*.py", "src/*"):
        pat = glob_to_pattern(g)
        assert "(?:" not in pat, (g, pat)
        assert "(?" not in pat, (g, pat)  # 룩어라운드·플래그 등 확장 문법 전반 차단


def test_env_write_blocked_by_hook():
    r = simulate(safety_first_preset("demo"), {"tool": "Write", "path": ".env", "label": "x"})
    assert r["outcome"] == "blocked-by-hook"
    assert r["blockedBy"] == "guard-hook-secrets"


def test_forcepush_ask():
    r = simulate(
        safety_first_preset("demo"),
        {"tool": "Bash", "command": "git push --force origin main", "label": "x"},
    )
    assert r["outcome"] == "ask"
    assert r["blockedBy"] == "perm-ask-forcepush"


def test_build_allowed():
    r = simulate(
        safety_first_preset("demo"), {"tool": "Bash", "command": "npm run build", "label": "x"}
    )
    assert r["outcome"] == "allowed"


def test_hook_disabled_allows_env():
    ir = safety_first_preset("demo")
    for c in ir.components:
        if c.id == "guard-hook-secrets":
            c.enabled = False
    r = simulate(ir, {"tool": "Write", "path": ".env", "label": "x"})
    assert r["outcome"] == "allowed"
