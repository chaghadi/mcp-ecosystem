import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "")
        self.default_calendar = os.getenv("GOOGLE_DEFAULT_CALENDAR", "primary")
        self.base_url = "https://www.googleapis.com/calendar/v3"
    def validate(self):
        if not self.refresh_token or "your-" in self.refresh_token:
            return "Google OAuth not configured. See setup guide in README."
        return None

settings = _Settings()
