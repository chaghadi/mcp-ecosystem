import os
from dotenv import load_dotenv
load_dotenv()

class _Settings:
    def __init__(self):
        # Twitter/X
        self.twitter_api_key = os.getenv("TWITTER_API_KEY", "")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET", "")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.twitter_access_secret = os.getenv("TWITTER_ACCESS_SECRET", "")
        self.twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
        # LinkedIn
        self.linkedin_access_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        self.linkedin_author_urn = os.getenv("LINKEDIN_AUTHOR_URN", "")

    def validate_twitter(self):
        if not self.twitter_api_key or "your-" in self.twitter_api_key:
            return "Twitter API credentials not configured. Get them from developer.twitter.com"
        return None

    def validate_linkedin(self):
        if not self.linkedin_access_token or "your-" in self.linkedin_access_token:
            return "LinkedIn access token not configured. Get it from linkedin.com/developers"
        return None

settings = _Settings()
