import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.token = os.getenv("VERCEL_TOKEN", "")
        self.team_id = os.getenv("VERCEL_TEAM_ID", "")
        self.base_url = "https://api.vercel.com"
    def validate(self):
        if not self.token or "your-" in self.token:
            return "VERCEL_TOKEN not set. Get it from vercel.com/account/tokens"
        return None
    @property
    def headers(self):
        h = {"Authorization": f"Bearer {self.token}"}
        if self.team_id:
            h["x-vercel-team-id"] = self.team_id
        return h

settings = _Settings()
