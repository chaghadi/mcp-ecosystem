import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "")
        self.resend_api_key = os.getenv("RESEND_API_KEY", "")
        self.email_from = os.getenv("EMAIL_FROM", "noreply@mmiri28.com")
        self.unsubscribe_base_url = os.getenv("UNSUBSCRIBE_BASE_URL", "https://mmiri28.com/unsubscribe")
        self.mcp_root = Path(__file__).parent.parent
    def validate(self):
        if not self.database_url:
            return "DATABASE_URL is not set."
        return None

settings = _Settings()
