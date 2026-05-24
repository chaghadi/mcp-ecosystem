import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.api_key = os.getenv("COINBASE_COMMERCE_API_KEY", "")
        self.webhook_secret = os.getenv("COINBASE_WEBHOOK_SECRET", "")
        self.base_url = "https://api.commerce.coinbase.com"
    def validate(self):
        if not self.api_key or "your-" in self.api_key:
            return "COINBASE_COMMERCE_API_KEY not configured. Get it from commerce.coinbase.com/dashboard/settings"
        return None
    @property
    def headers(self):
        return {"X-CC-Api-Key": self.api_key, "X-CC-Version": "2018-03-22",
                "Content-Type": "application/json"}

settings = _Settings()
