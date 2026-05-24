def test_no_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    from importlib import reload
    import src.config as c; reload(c)
    from src.config import settings
    assert settings.validate() is not None

def test_referral_code_format():
    from src.server import _new_referral_code
    code = _new_referral_code()
    assert len(code) <= 10
    assert code.isalnum()

def test_position_lookup_needs_input():
    import os
    os.environ["DATABASE_URL"] = "postgresql://x:x@localhost/x"
    from importlib import reload
    import src.config as c; reload(c)
    from src.server import get_position
    result = get_position()
    assert result["ok"] is False
