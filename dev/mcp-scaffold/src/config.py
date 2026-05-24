import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.github_owner = os.getenv("GITHUB_OWNER", "chaghadi")
        self.brand = os.getenv("BRAND", "mmiri28 solutions")
    def validate(self):
        if not self.github_token or "your-" in self.github_token:
            return "GITHUB_TOKEN not set."
        return None

settings = _Settings()
