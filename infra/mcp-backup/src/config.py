import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "")
        # R2 credentials for backup storage
        self.r2_account_id = os.getenv("R2_ACCOUNT_ID", "")
        self.r2_access_key = os.getenv("R2_ACCESS_KEY_ID", "")
        self.r2_secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "")
        self.r2_backup_bucket = os.getenv("R2_BACKUP_BUCKET", "mmiri28-backups")
        self.mcp_root = Path(__file__).parent.parent
    def validate(self):
        if not self.database_url:
            return "DATABASE_URL is not set."
        if not self.r2_access_key:
            return "R2_ACCESS_KEY_ID is not set."
        return None

settings = _Settings()
