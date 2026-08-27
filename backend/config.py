import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    COOKIE_HEADER = os.getenv("COOKIE_HEADER", "")
    LI_AT = os.getenv("LI_AT", "")
    JSESSIONID = os.getenv("JSESSIONID", "").strip('"')  # Clean quotes if any
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

    @classmethod
    def get_cookies_dict(cls) -> dict:
        """Parse cookies from COOKIE_HEADER or individual variables."""
        cookies = {}
        if cls.COOKIE_HEADER:
            # Clean enclosing quotes if copy-pasted as a string block
            clean_header = cls.COOKIE_HEADER.strip('"\'')
            for pair in clean_header.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    cookies[k.strip()] = v.strip()
        
        # Fallback/merge with explicit individual variables
        if "li_at" not in cookies and cls.LI_AT:
            cookies["li_at"] = cls.LI_AT
        if "JSESSIONID" not in cookies and cls.JSESSIONID:
            cookies["JSESSIONID"] = cls.JSESSIONID.strip('"')
            
        return cookies

    @classmethod
    def is_valid(cls) -> bool:
        """Check if cookies are configured and not placeholders."""
        cookies = cls.get_cookies_dict()
        li_at = cookies.get("li_at", "")
        jsessionid = cookies.get("JSESSIONID", "")
        placeholders = {"your_li_at_cookie_here", "your_jsessionid_here", ""}
        return (
            li_at != "" and li_at not in placeholders
            and jsessionid != "" and jsessionid not in placeholders
        )
