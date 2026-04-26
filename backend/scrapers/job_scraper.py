"""
Lead Engine — JobSpy Scraper
Uses python-jobspy to search Indeed, LinkedIn, Google Jobs.
Returns ONLY real scraped data. Never returns mock/fake data.
"""
import csv
import logging
from typing import Optional
from jobspy import scrape_jobs

logger = logging.getLogger(__name__)

# Country code mapping for Indeed
COUNTRY_MAP = {
    "india": "India", "usa": "USA", "uk": "UK",
    "canada": "Canada", "australia": "Australia",
    "germany": "Germany", "france": "France",
    "singapore": "Singapore", "uae": "UAE",
}

INDIAN_CITIES = [
    "mumbai", "delhi", "bangalore", "bengaluru", "pune", "hyderabad",
    "chennai", "kolkata", "noida", "gurgaon", "gurugram", "ahmedabad",
    "jaipur", "lucknow", "chandigarh", "kochi", "indore", "bhopal",
]


def detect_country(location: str, default: str = "USA") -> str:
    """Detect the country from location string."""
    loc_lower = location.lower() if location else ""
    for key, value in COUNTRY_MAP.items():
        if key in loc_lower:
            return value
    if any(city in loc_lower for city in INDIAN_CITIES):
        return "India"
    return default


def scrape_executive_jobs(
    search_term: str = "",
    location: str = "",
    industry: str = "",
    hours_old: Optional[int] = None,
    results_wanted: int = 20,
    country: str = "",
) -> list[dict]:
    """
    Scrape job boards for executive/leadership positions using python-jobspy.
    Returns ONLY real scraped data — no mock data ever.
    If nothing is found, returns an empty list.
    """
    sites = ["indeed", "linkedin", "google"]

    # Build query — the user's term + industry context
    query = search_term.strip() if search_term else "Director"
    if industry:
        query = f"{query} {industry}"

    detected_country = country if country else detect_country(location)
    google_query = f"{query} jobs {location}" if location else f"{query} jobs"

    logger.info(
        f"[JobSpy] query='{query}', location='{location}', "
        f"country='{detected_country}', sites={sites}, hours_old={hours_old}"
    )

    all_results = []

    # ── Strategy 1: Full search with location ──────────────────────
    try:
        kwargs = {
            "site_name": sites,
            "search_term": query,
            "google_search_term": google_query,
            "results_wanted": results_wanted,
            "country_indeed": detected_country,
            "verbose": 1,
        }
        if location:
            kwargs["location"] = location
        if hours_old and hours_old > 0:
            kwargs["hours_old"] = hours_old

        jobs_df = scrape_jobs(**kwargs)

        if jobs_df is not None and not jobs_df.empty:
            for _, row in jobs_df.iterrows():
                job = _row_to_dict(row)
                if job:
                    all_results.append(job)
            logger.info(f"[JobSpy] Strategy 1: Found {len(all_results)} jobs")

    except Exception as e:
        logger.error(f"[JobSpy] Strategy 1 error: {e}", exc_info=True)

    # ── Strategy 2: Broader search without location ────────────────
    if len(all_results) < 5 and location:
        logger.info("[JobSpy] Strategy 2: Broadening search (no location filter)...")
        try:
            kwargs2 = {
                "site_name": sites,
                "search_term": query,
                "google_search_term": f"{query} jobs",
                "results_wanted": results_wanted,
                "country_indeed": detected_country,
                "verbose": 1,
            }
            jobs_df2 = scrape_jobs(**kwargs2)

            if jobs_df2 is not None and not jobs_df2.empty:
                existing_urls = {r["job_url"] for r in all_results}
                for _, row in jobs_df2.iterrows():
                    job = _row_to_dict(row)
                    if job and job["job_url"] not in existing_urls:
                        all_results.append(job)
                        existing_urls.add(job["job_url"])

        except Exception as e:
            logger.error(f"[JobSpy] Strategy 2 error: {e}", exc_info=True)

    # ── Strategy 3: Simplest possible search ───────────────────────
    if len(all_results) < 3:
        base_term = search_term.strip() if search_term else "Director"
        logger.info(f"[JobSpy] Strategy 3: Simplest search — just '{base_term}'...")
        try:
            kwargs3 = {
                "site_name": ["indeed"],
                "search_term": base_term,
                "results_wanted": 15,
                "country_indeed": detected_country,
                "verbose": 1,
            }
            jobs_df3 = scrape_jobs(**kwargs3)

            if jobs_df3 is not None and not jobs_df3.empty:
                existing_urls = {r["job_url"] for r in all_results}
                for _, row in jobs_df3.iterrows():
                    job = _row_to_dict(row)
                    if job and job["job_url"] not in existing_urls:
                        all_results.append(job)
                        existing_urls.add(job["job_url"])

        except Exception as e:
            logger.error(f"[JobSpy] Strategy 3 error: {e}", exc_info=True)

    logger.info(f"[JobSpy] TOTAL: {len(all_results)} real jobs found")
    return all_results


def _row_to_dict(row) -> Optional[dict]:
    """Convert a pandas DataFrame row to a lead dict. Returns None if missing title/URL."""
    title = _safe_str(row.get("title"))
    job_url = _safe_str(row.get("job_url"))

    if not title or not job_url:
        return None

    return {
        "job_title": title,
        "company_name": _safe_str(row.get("company")),
        "company_url": _safe_str(row.get("company_url")),
        "job_url": job_url,
        "location": _build_location(row),
        "source": str(row.get("site", "unknown")).lower(),
        "job_type": _safe_str(row.get("job_type")),
        "salary_min": _safe_float(row.get("min_amount")),
        "salary_max": _safe_float(row.get("max_amount")),
        "description": _safe_str(row.get("description"))[:2000],
        "date_posted": _safe_str(row.get("date_posted")),
        "company_industry": _safe_str(row.get("company_industry")),
        "company_employees": _safe_str(row.get("company_employees_label")),
        "score": 0,
        "outreach_tip": "",
    }


def _build_location(row) -> str:
    parts = []
    for field in ["city", "state", "country"]:
        val = row.get(field)
        if val and str(val) not in ("nan", "None", "") and str(val).strip():
            parts.append(str(val).strip())
    return ", ".join(parts)


def _safe_str(val) -> str:
    if val is None:
        return ""
    s = str(val)
    if s in ("nan", "None", "NaT", "NaN"):
        return ""
    return s.strip()


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:  # NaN check
            return None
        return f
    except (ValueError, TypeError):
        return None
