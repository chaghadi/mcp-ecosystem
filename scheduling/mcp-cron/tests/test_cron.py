def test_invalid_cron_expression(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost/x")
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import register_job
    result = register_job("test", "not a cron", "tool", {})
    assert result["ok"] is False
    assert "Invalid cron" in result["error"]

def test_valid_cron_calculates_next_run():
    from src.server import _next_run
    next_run = _next_run("0 3 * * *")
    assert next_run.hour == 3
    assert next_run.minute == 0
