import asyncio
from backend.scrapers.job_scraper import scrape_executive_jobs

async def test():
    print("Testing Lead Engine Scraper (Real Data Only)...")
    results = await asyncio.to_thread(
        scrape_executive_jobs,
        search_term="CFO",
        location="India",
        industry="Automotive",
        results_wanted=5
    )
    
    print(f"\nFound {len(results)} results.")
    for i, res in enumerate(results):
        print(f"\n[{i+1}] {res['job_title']} at {res['company_name']}")
        print(f"    Source: {res['source']} | Location: {res['location']}")
        print(f"    URL: {res['job_url'][:70]}...")
        
    if not results:
        print("No leads found. Scraper is working but returning 0 results (expected if no current matching roles).")

if __name__ == "__main__":
    asyncio.run(test())
