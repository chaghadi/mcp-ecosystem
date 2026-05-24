import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.key_id = os.getenv("APPSTORE_KEY_ID", "")
        self.issuer_id = os.getenv("APPSTORE_ISSUER_ID", "")
        # Path to .p8 private key file
        self.private_key_path = os.getenv("APPSTORE_PRIVATE_KEY_PATH", "")
        # Or the key contents directly
        self.private_key_content = os.getenv("APPSTORE_PRIVATE_KEY", "")
        self.base_url = "https://api.appstoreconnect.apple.com/v1"
    def validate(self):
        if not self.key_id or "your-" in self.key_id:
            return "APPSTORE_KEY_ID not set. Get one from App Store Connect → Users and Access → Keys."
        if not self.issuer_id or "your-" in self.issuer_id:
            return "APPSTORE_ISSUER_ID not set."
        if not self.private_key_path and not self.private_key_content:
            return "APPSTORE_PRIVATE_KEY_PATH or APPSTORE_PRIVATE_KEY not set."
        return None
    def get_private_key(self) -> str:
        if self.private_key_content:
            return self.private_key_content.replace("\\n", "\n")
        with open(self.private_key_path) as f:
            return f.read()

settings = _Settings()
