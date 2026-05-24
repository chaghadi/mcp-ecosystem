import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        # Path to Google service account JSON or the JSON contents
        self.service_account_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH", "")
        self.service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        self.base_url = "https://androidpublisher.googleapis.com/androidpublisher/v3"
    def validate(self):
        if not self.service_account_path and not self.service_account_json:
            return "Set GOOGLE_SERVICE_ACCOUNT_PATH (or _JSON). Create one at console.cloud.google.com → IAM → Service Accounts. Grant access in Play Console → Setup → API access."
        return None

settings = _Settings()
