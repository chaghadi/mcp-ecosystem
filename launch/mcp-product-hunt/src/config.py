import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.access_token = os.getenv("PRODUCT_HUNT_TOKEN", "")
        self.base_url = "https://api.producthunt.com/v2/api/graphql"
    def validate(self):
        if not self.access_token or "your-" in self.access_token:
            return "PRODUCT_HUNT_TOKEN not set. Get one at producthunt.com/v2/oauth/applications"
        return None
    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json", "Content-Type": "application/json"}

settings = _Settings()
