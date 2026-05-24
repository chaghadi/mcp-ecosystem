import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.token = os.getenv("FIGMA_TOKEN", "")
        self.base_url = "https://api.figma.com/v1"
    def validate(self):
        if not self.token or "your-" in self.token:
            return "FIGMA_TOKEN not set. Generate at figma.com → Settings → Personal access tokens"
        return None
    @property
    def headers(self):
        return {"X-Figma-Token": self.token}

settings = _Settings()
