def test_health_no_docker():
    import subprocess
    from unittest.mock import patch
    with patch("subprocess.run", side_effect=FileNotFoundError("docker")):
        from src.server import health_check
        result = health_check()
        assert result["ok"] is False
