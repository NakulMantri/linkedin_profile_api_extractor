import re
import logging
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import quote
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

def extract_description(ent: dict) -> Optional[str]:
    """Traverse subcomponents inside a Tetris entityComponent to extract the description text."""
    sub = ent.get("subComponents")
    if not sub:
        return None
    sub_comps = sub.get("components", [])
    for c in sub_comps:
        comp_details = c.get("components", {})
        fixed_list = comp_details.get("fixedListComponent")
        if fixed_list:
            list_comps = fixed_list.get("components", [])
            for lc in list_comps:
                text_comp = lc.get("components", {}).get("textComponent")
                if text_comp:
                    text_dict = text_comp.get("text", {})
                    if text_dict:
                        return text_dict.get("text")
    return None

def extract_profile_picture(profile_dict: dict) -> tuple:
    """Extract full profile picture URL and various sizes safely from displayImage metadata."""
    profile_pic = profile_dict.get("profilePicture")
    if not profile_pic:
        return None, {}
    
    display_image = profile_pic.get("displayImage")
    if not display_image:
        return None, {}
        
    vector_image = display_image.get("vectorImage")
    if not vector_image:
        return None, {}
        
    root_url = vector_image.get("rootUrl")
    artifacts = vector_image.get("artifacts", [])
    
    profile_images = {}
    profile_picture_url = None
    
    if root_url and artifacts:
        # Reconstruct various sizes from the artifacts
        for art in artifacts:
            w = art.get("width")
            h = art.get("height")
            path = art.get("fileIdentifyingUrlPathSegment")
            if w and h and path:
                size_key = f"{w}_{h}"
                profile_images[size_key] = root_url + path
                
        # Select the largest available size as default profile_picture_url
        sizes = sorted(
            [int(s.split("_")[0]) for s in profile_images.keys() if "_" in s],
            reverse=True
        )
        if sizes:
            largest_size = f"{sizes[0]}_{sizes[0]}"
            profile_picture_url = profile_images.get(largest_size)
        else:
            profile_picture_url = root_url
            
    return profile_picture_url, profile_images

def parse_single_tetris(ent: dict, parent_title: Optional[str], section_type: str) -> Any:
    """Parse a single Tetris entityComponent into the target unified schema."""
    title = ent.get("titleV2", {}).get("text", {}).get("text")
    subtitle = ent.get("subtitle", {}).get("text") if ent.get("subtitle") else None
    caption_text = ent.get("caption", {}).get("text") if ent.get("caption") else None
    metadata_text = ent.get("metadata", {}).get("text") if ent.get("metadata") else None
    
    if section_type == "experience":
        company = parent_title or subtitle
        location = metadata_text
        dates = caption_text
        
        start_date, end_date, duration = None, None, None
        if dates:
            parts = dates.split(" · ")
            duration = parts[1] if len(parts) > 1 else None
            date_range = parts[0]
            if " - " in date_range:
                start_date, end_date = date_range.split(" - ", 1)
            else:
                start_date = date_range
                
        return {
            "company": company,
            "title": title,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "duration": duration,
            "description": extract_description(ent),
        }
        
    elif section_type == "education":
        school = parent_title or title
        degree = subtitle
        dates = caption_text
        
        start_date, end_date = None, None
        if dates:
            if " - " in dates:
                start_date, end_date = dates.split(" - ", 1)
            else:
                start_date = dates
                
        return {
            "school": school,
            "degree": degree,
            "start_date": start_date,
            "end_date": end_date,
            "description": extract_description(ent)
        }
        
    elif section_type == "skills":
        return title
        
    elif section_type == "languages":
        return {
            "name": title,
            "proficiency": subtitle
        }
        
    elif section_type == "certifications":
        name = title
        authority = subtitle
        dates = caption_text
        license_number = metadata_text
        
        start_date, end_date = None, None
        if dates:
            clean_dates = dates.replace("Issued ", "").replace("Expires ", "")
            if " · " in clean_dates:
                parts = clean_dates.split(" · ")
                start_date = parts[0]
                end_date = parts[1]
            else:
                start_date = clean_dates
                
        return {
            "name": name,
            "authority": authority,
            "license_number": license_number,
            "start_date": start_date,
            "end_date": end_date,
        }
    return None

def parse_tetris_elements(elements: list, section_type: str) -> list:
    """Iterate and parse elements inside a PagedListComponent, handling groups."""
    parsed = []
    for el in elements:
        comp = el.get("components", {})
        ent = comp.get("entityComponent")
        if not ent:
            # Handle group component (e.g. multiple experiences in the same company)
            group = comp.get("entityGroupComponent")
            if group:
                group_title = group.get("titleV2", {}).get("text", {}).get("text")
                subcomponents = group.get("subcomponents", [])
                for sub in subcomponents:
                    sub_ent = sub.get("components", {}).get("entityComponent")
                    if sub_ent:
                        parsed.append(parse_single_tetris(sub_ent, group_title, section_type))
            continue
        
        parsed.append(parse_single_tetris(ent, None, section_type))
    return parsed

class LinkedInScraper:
    """Scraper targeting modern LinkedIn Voyager and GraphQL components endpoints."""

    def __init__(self):
        self._client = None

    def get_client(self) -> Linkedin:
        """Lazy initialization of the LinkedIn client with cookies."""
        if not Config.is_valid():
            raise ValueError(
                "LinkedIn authentication cookies are not configured. "
                "Please configure them in your .env file."
            )
        
        if self._client is None:
            logger.info("Initializing LinkedIn API client with session cookies.")
            # Load parsed cookies dictionary from config
            cookies_dict = Config.get_cookies_dict()
            
            # Construct a proper RequestsCookieJar
            cookies_jar = requests.cookies.RequestsCookieJar()
            for k, v in cookies_dict.items():
                cookies_jar.set(k, v, domain=".linkedin.com")
            
            # Instantiate client with jar
            self._client = Linkedin(
                username="",
                password="",
                cookies=cookies_jar
            )
            
            # Update headers with modern user agent and csrf
            jsession = cookies_dict.get("JSESSIONID", "").strip('"')
            self._client.client.session.headers.update({
                "csrf-token": jsession,
                "x-restli-protocol-version": "2.0.0",
                "x-li-lang": "en_US",
                "accept": "application/vnd.linkedin.normalized+json+2.1",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
                "accept-language": "en-US,en-IN;q=0.9,en;q=0.8,hi;q=0.7,de;q=0.6"
            })

        return self._client

    def _fetch_graphql_section(self, client: Linkedin, urn_id: str, section_type: str) -> list:
        """Query and parse a profile components section using the modern GraphQL endpoint."""
        query_id = "voyagerIdentityDashProfileComponents.7af5d6f176f11583b382e37e5639e69e"
        profile_urn = f"urn:li:fsd_profile:{urn_id}"
        variables = f"(profileUrn:{quote(profile_urn)},sectionType:{section_type})"
        url = f"https://www.linkedin.com/voyager/api/graphql?variables={variables}&queryId={query_id}&includeWebMetadata=true"
        
        res = client.client.session.get(url)
        if res.status_code != 200:
            logger.warning(f"Failed to fetch section {section_type}. Status: {res.status_code}")
            return []
            
        data = res.json()
        included = data.get("included", [])
        
        for obj in included:
            if obj.get("$type") == "com.linkedin.voyager.dash.identity.profile.tetris.PagedListComponent":
                elements = obj.get("components", {}).get("elements", [])
                return parse_tetris_elements(elements, section_type)
        return []

    def scrape_profile(self, profile_url: str) -> Dict[str, Any]:
        """
        Extract LinkedIn profile details by URL using modern endpoints.
        Returns a formatted structured JSON.
        """
        username = extract_username(profile_url)
        client = self.get_client()

        logger.info(f"Fetching profile card for user: {username}")
        
        # Query modern profile dashboard card
        url = f"https://www.linkedin.com/voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity={username}"
        res = client.client.session.get(url)
        if res.status_code == 302 or res.status_code == 401 or res.status_code == 410:
            raise ValueError(
                "Authentication failed. Please check if your LinkedIn session cookies in .env are correct and active."
            )
        elif res.status_code != 200:
            raise ValueError(
                f"Failed to retrieve profile card. Status: {res.status_code}. "
                "Check connection or session validity."
            )
            
        data = res.json()
        included = data.get("included", [])
        if not included:
            raise ValueError(
                f"No profile details returned for '{username}'. The profile may not exist or is restricted."
            )
            
        # Parse profile details (always the first object of type Profile in included)
        profile_data = None
        for obj in included:
            if obj.get("$type") == "com.linkedin.voyager.dash.identity.profile.Profile":
                profile_data = obj
                break
                
        if not profile_data:
            raise ValueError(f"Profile object not found in response for '{username}'")
            
        # Reconstruct profile URN ID and identifier
        entity_urn = profile_data.get("entityUrn", "")
        urn_id = entity_urn.split(":")[-1] if entity_urn else None
        
        first_name = profile_data.get("firstName")
        last_name = profile_data.get("lastName")
        full_name = f"{first_name or ''} {last_name or ''}".strip()
        headline = profile_data.get("headline")
        summary = profile_data.get("summary")
        
        # Location mapping
        country_code = profile_data.get("location", {}).get("countryCode")
        location = country_code
        
        # Extract profile picture and artifacts
        profile_picture_url, profile_images = extract_profile_picture(profile_data)
        
        # Attempt to retrieve contact info (optional segment, might fail if restricted/out-of-network)
        contact_info = {}
        try:
            logger.info(f"Fetching contact info for user: {username}")
            # Try fetching from voyager contact info endpoint
            res_contact = client.client.session.get(
                f"https://www.linkedin.com/voyager/api/identity/profiles/{username}/profileContactInfo"
            )
            if res_contact.status_code == 200:
                raw_contact = res_contact.json()
                contact_info = {
                    "email": raw_contact.get("emailAddress") or raw_contact.get("email_address"),
                    "websites": raw_contact.get("websites", []),
                    "twitter": raw_contact.get("twitter", []),
                    "phone_numbers": raw_contact.get("phone_numbers", []),
                }
        except Exception as e:
            logger.warning(f"Could not fetch contact info for {username}: {str(e)}")
            
        # Fetch remaining components via modern GraphQL endpoints
        experience = []
        education = []
        skills = []
        certifications = []
        languages = []
        
        if urn_id:
            logger.info(f"Fetching GraphQL sections for URN ID: {urn_id}")
            experience = self._fetch_graphql_section(client, urn_id, "experience")
            education = self._fetch_graphql_section(client, urn_id, "education")
            skills = self._fetch_graphql_section(client, urn_id, "skills")
            certifications = self._fetch_graphql_section(client, urn_id, "certifications")
            languages = self._fetch_graphql_section(client, urn_id, "languages")

        # Construct unified normalized profile JSON
        normalized = {
            "profile_id": username,
            "urn_id": urn_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "headline": headline,
            "location": location,
            "summary": summary,
            "profile_picture_url": profile_picture_url,
            "profile_images": profile_images,
            "contact_info": contact_info,
            "experience": experience,
            "education": education,
            "skills": skills,
            "certifications": certifications,
            "languages": languages,
        }
        return normalized
