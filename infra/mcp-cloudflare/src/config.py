import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        self.base_url = "https://api.cloudflare.com/client/v4"
    def validate(self):
        if not self.api_token or "your-" in self.api_token:
            return "CLOUDFLARE_API_TOKEN not set. Get it from dash.cloudflare.com/profile/api-tokens"
        return None
    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"}

settings = _Settings()
