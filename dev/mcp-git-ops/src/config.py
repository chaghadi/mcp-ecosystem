import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.github_owner = os.getenv("GITHUB_OWNER", "chaghadi")
        self.base_url = "https://api.github.com"
    def validate(self):
        if not self.github_token or "your-" in self.github_token:
            return "GITHUB_TOKEN is not set. Create one at github.com/settings/tokens"
        return None
    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"}

settings = _Settings()
