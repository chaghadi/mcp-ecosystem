import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.token = os.getenv("DO_API_TOKEN", "")
        self.base_url = "https://api.digitalocean.com/v2"
    def validate(self):
        if not self.token or "your-" in self.token:
            return "DO_API_TOKEN not set. Get it from cloud.digitalocean.com/account/api/tokens"
        return None
    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

settings = _Settings()
