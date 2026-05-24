import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "")
        self.twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
        self.mcp_root = Path(__file__).parent.parent
    def validate(self):
        if not self.database_url:
            return "DATABASE_URL is not set."
        return None

settings = _Settings()
