import re
import logging
from typing import Dict, Any, List, Optional
from linkedin_api import Linkedin
from backend.config import Config

logger = logging.getLogger(__name__)

def extract_username(url: str) -> str:
    """
    Extract the LinkedIn public identifier (username/slug) from a profile URL.
    Supports formats like:
      - https://www.linkedin.com/in/username/
      - https://www.linkedin.com/in/username
      - http://linkedin.com/in/username/
      - https://in.linkedin.com/in/username
    """
    url = url.strip()
    match = re.search(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/([^/?#]+)", url)
    if not match:
        raise ValueError(
            "Invalid LinkedIn profile URL. Must be in the format: "
            "https://www.linkedin.com/in/username"
        )
    # Strip any trailing slashes
    username = match.group(1).rstrip("/")
    return username

def parse_date(date_dict: Optional[Dict[str, Any]]) -> Optional[str]:
    """Parse a date dictionary into a YYYY-MM or YYYY string."""
    if not date_dict:
        return None
    year = date_dict.get("year")
    month = date_dict.get("month")
    if year and month:
        return f"{year}-{month:02d}"
    elif year:
        return f"{year}"
    return None

def parse_experience(experience_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse raw experience elements into a normalized structure."""
    parsed = []
    for item in experience_elements:
        time_period = item.get("timePeriod", {})
        start_dict = time_period.get("startDate") if time_period else None
        end_dict = time_period.get("endDate") if time_period else None

        start_date = parse_date(start_dict)
        end_date = parse_date(end_dict) if end_dict else "Present"

        # Determine company details
        company_name = item.get("companyName")
        company_url = None
        company_logo_url = item.get("companyLogoUrl")

        company_data = item.get("company", {})
        if company_data:
            # Reconstruct company url from miniCompany URN
            mini_company = company_data.get("miniCompany", {}) or {}
            entity_urn = company_data.get("entityUrn") or mini_company.get("entityUrn")
            if entity_urn:
                company_id = entity_urn.split(":")[-1]
                company_url = f"https://www.linkedin.com/company/{company_id}"
            
            # Fallback for company logo if not present
            if not company_logo_url and "logo" in mini_company:
                logo = mini_company["logo"].get("com.linkedin.common.VectorImage")
                if logo:
                    company_logo_url = logo.get("rootUrl")

        parsed.append({
            "company": company_name,
            "company_url": company_url,
            "company_logo_url": company_logo_url,
            "title": item.get("title"),
            "location": item.get("locationName"),
            "start_date": start_date,
            "end_date": end_date,
            "duration": item.get("durationName"),
            "description": item.get("description"),
        })
    return parsed

def parse_education(education_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse raw education elements into a normalized structure."""
    parsed = []
    for item in education_elements:
        time_period = item.get("timePeriod", {})
        start_dict = time_period.get("startDate") if time_period else None
        end_dict = time_period.get("endDate") if time_period else None

        start_date = parse_date(start_dict)
        end_date = parse_date(end_dict)

        school_data = item.get("school", {})
        school_url = None
        school_logo_url = item.get("schoolLogoUrl") or school_data.get("logoUrl")

        if school_data:
            entity_urn = school_data.get("entityUrn")
            if entity_urn:
                school_id = entity_urn.split(":")[-1]
                school_url = f"https://www.linkedin.com/school/{school_id}"

            # Fallback for logo url
            if not school_logo_url and "logo" in school_data:
                logo = school_data["logo"].get("com.linkedin.common.VectorImage")
                if logo:
                    school_logo_url = logo.get("rootUrl")

        parsed.append({
            "school": item.get("schoolName"),
            "school_url": school_url,
            "school_logo_url": school_logo_url,
            "degree": item.get("degreeName"),
            "field_of_study": item.get("fieldOfStudy"),
            "start_date": start_date,
            "end_date": end_date,
            "description": item.get("description"),
        })
    return parsed

def parse_skills(skills_elements: List[Dict[str, Any]]) -> List[str]:
    """Parse raw skills elements into a list of strings."""
    parsed = []
    for item in skills_elements:
        if isinstance(item, str):
            parsed.append(item)
        elif isinstance(item, dict):
            # linkedin-api usually maps to 'name'
            name = item.get("name") or item.get("skillName")
            if name:
                parsed.append(name)
    return parsed

def parse_certifications(certification_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse raw certification elements into a normalized structure."""
    parsed = []
    for item in certification_elements:
        time_period = item.get("timePeriod", {})
        start_dict = time_period.get("startDate") if time_period else None
        end_dict = time_period.get("endDate") if time_period else None

        start_date = parse_date(start_dict)
        end_date = parse_date(end_dict)

        parsed.append({
            "name": item.get("name"),
            "authority": item.get("authority"),
            "license_number": item.get("licenseNumber"),
            "url": item.get("url"),
            "start_date": start_date,
            "end_date": end_date,
        })
    return parsed

def parse_languages(language_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse raw language elements into a normalized structure."""
    parsed = []
    for item in language_elements:
        parsed.append({
            "name": item.get("name"),
            "proficiency": item.get("proficiency"),
        })
    return parsed

class LinkedInScraper:
    """Wrapper scraper using the unofficial LinkedIn Voyager API via session cookies."""

    def __init__(self):
        self._client = None

    def get_client(self) -> Linkedin:
        """Lazy initialization of the LinkedIn client with cookies."""
        if not Config.is_valid():
            raise ValueError(
                "LinkedIn authentication cookies (LI_AT, JSESSIONID) are not configured. "
                "Please configure them in your .env file."
            )
        
        if self._client is None:
            logger.info("Initializing LinkedIn API client with session cookies.")
            self._client = Linkedin(
                cookies={
                    "li_at": Config.LI_AT,
                    "JSESSIONID": Config.JSESSIONID,
                }
            )
        return self._client

    def scrape_profile(self, profile_url: str) -> Dict[str, Any]:
        """
        Extract LinkedIn profile details by URL.
        Returns a formatted structured JSON.
        """
        username = extract_username(profile_url)
        client = self.get_client()

        logger.info(f"Fetching profile View data for user: {username}")
        raw_profile = client.get_profile(public_id=username)
        if not raw_profile:
            raise ValueError(
                f"Failed to retrieve profile data for '{username}'. "
                "Verify the URL or check if your LinkedIn session cookies are valid and active."
            )

        # Reconstruct profile images
        root_img_url = raw_profile.get("displayPictureUrl")
        profile_images = {}
        profile_picture_url = None

        if root_img_url:
            # Reconstruct various sizes from the flat fields prefixed with img_
            # e.g., img_800_800, img_400_400, img_200_200
            for key, val in raw_profile.items():
                if key.startswith("img_"):
                    size = key.replace("img_", "")
                    profile_images[size] = root_img_url + val
            
            # Select the largest available picture as default
            sizes = sorted(
                [int(s.split("_")[0]) for s in profile_images.keys() if "_" in s],
                reverse=True
            )
            if sizes:
                largest_size = f"{sizes[0]}_{sizes[0]}"
                profile_picture_url = profile_images.get(largest_size)
            else:
                profile_picture_url = root_img_url

        # Attempt to retrieve contact info (optional segment, might fail if restricted)
        contact_info = {}
        try:
            logger.info(f"Fetching contact info for user: {username}")
            raw_contact = client.get_profile_contact_info(public_id=username)
            if raw_contact:
                contact_info = {
                    "email": raw_contact.get("email_address"),
                    "websites": raw_contact.get("websites", []),
                    "twitter": raw_contact.get("twitter", []),
                    "phone_numbers": raw_contact.get("phone_numbers", []),
                }
        except Exception as e:
            logger.warning(f"Could not fetch contact info for {username}: {str(e)}")

        # Construct unified normalized profile JSON
        normalized = {
            "profile_id": raw_profile.get("profile_id", username),
            "urn_id": raw_profile.get("urn_id"),
            "first_name": raw_profile.get("firstName"),
            "last_name": raw_profile.get("lastName"),
            "full_name": f"{raw_profile.get('firstName', '')} {raw_profile.get('lastName', '')}".strip(),
            "headline": raw_profile.get("headline"),
            "location": raw_profile.get("locationName") or raw_profile.get("geoLocationName"),
            "summary": raw_profile.get("summary"),
            "profile_picture_url": profile_picture_url,
            "profile_images": profile_images,
            "contact_info": contact_info,
            "experience": parse_experience(raw_profile.get("experience", [])),
            "education": parse_education(raw_profile.get("education", [])),
            "skills": parse_skills(raw_profile.get("skills", [])),
            "certifications": parse_certifications(raw_profile.get("certifications", [])),
            "languages": parse_languages(raw_profile.get("languages", [])),
        }

        return normalized
