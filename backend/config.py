import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    LI_AT = os.getenv("LI_AT", "")
    JSESSIONID = os.getenv("JSESSIONID", "").strip('"')  # Clean quotes if any
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

    @classmethod
    def is_valid(cls) -> bool:
        """Check if cookies are configured and not placeholders."""
        placeholders = {"your_li_at_cookie_here", "your_jsessionid_here", ""}
        return (
            cls.LI_AT not in placeholders
            and cls.JSESSIONID not in placeholders
        )
