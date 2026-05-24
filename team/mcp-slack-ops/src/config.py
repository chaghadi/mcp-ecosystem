import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        self.base_url = "https://slack.com/api"
    def validate(self):
        if not self.bot_token or "your-" in self.bot_token:
            return "SLACK_BOT_TOKEN not set. Create a Slack app at api.slack.com/apps, install it to your workspace, copy the Bot Token (xoxb-...)"
        return None
    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.bot_token}",
                "Content-Type": "application/json; charset=utf-8"}

settings = _Settings()
