import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.ecosystem_root = Path(os.getenv("ECOSYSTEM_ROOT",
            str(Path(__file__).parent.parent.parent.parent)))
        self.github_owner = os.getenv("GITHUB_OWNER", "chaghadi")
        self.github_token = os.getenv("GITHUB_TOKEN", "")

settings = _Settings()
