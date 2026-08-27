import logging
from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

from backend.config import Config
from backend.scraper import LinkedInScraper

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LinkedIn Profile Extractor API",
    description="A hosted API that accepts a LinkedIn profile URL and returns structured JSON.",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the scraper
scraper = LinkedInScraper()

@app.get("/health", summary="Health check endpoint")
async def health():
    """Verify that the API server is up, and check cookie configuration status."""
    cookies_ok = Config.is_valid()
    return {
        "status": "online",
        "cookies_configured": cookies_ok,
        "message": "LinkedIn Scraper API is healthy" if cookies_ok else "LinkedIn cookies are not configured yet. Set them in .env"
    }

@app.get("/api/v1/profile", summary="Extract profile information")
async def get_profile(
    profile_url: str = Query(..., description="The full LinkedIn profile URL (e.g., https://www.linkedin.com/in/username)")
):
    """
    Accepts a LinkedIn profile URL and returns structured JSON details of the profile.
    Requires backend session cookies to be configured in .env.
    """
    logger.info(f"Received scraping request for URL: {profile_url}")

    if not Config.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LinkedIn authentication cookies are not configured on the server. Please set them in your .env file."
        )

    try:
        data = scraper.scrape_profile(profile_url)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": data
            }
        )
    except ValueError as val_err:
        logger.error(f"Validation error: {str(val_err)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        logger.error(f"Error extracting profile: {str(exc)}", exc_info=True)
        # Check for typical authentication failure signatures in exception message
        exc_msg = str(exc).lower()
        if "auth" in exc_msg or "login" in exc_msg or "cookie" in exc_msg or "unauthorized" in exc_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed. Please check if your LinkedIn session cookies in .env are correct and active."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the request: {str(exc)}"
        )

# Serve the testing UI dashboard
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

if os.path.exists(frontend_dir):
    # Mount files other than index.html (like CSS and JS) to /static
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_ui():
        """Serve the index.html at root."""
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Welcome to LinkedIn Profile API! Frontend UI index.html not found."}
else:
    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return {"message": "Welcome to LinkedIn Profile API! Visit /docs for Swagger API documentation."}
