def test_consistent_variant():
    from src.server import _assign_variant
    v1 = _assign_variant("exp1", "user-abc", ["A", "B", "C"])
    v2 = _assign_variant("exp1", "user-abc", ["A", "B", "C"])
    assert v1 == v2  # Deterministic

def test_different_users_different_variants():
    from src.server import _assign_variant
    variants = ["A", "B"]
    assignments = [_assign_variant("exp1", f"user-{i}", variants) for i in range(100)]
    # Both variants should appear in 100 users
    assert "A" in assignments
    assert "B" in assignments

def test_requires_two_variants(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import create_experiment
    result = create_experiment("test", "app", ["only_one"], "goal")
    assert result["ok"] is False
